#!/usr/bin/env python3
"""ONE live vendor arm through the exact DAG `run` task, with the vendor launch
and every descendant under a macOS write-deny sandbox on the operator HOME.

real_home_canary.py proved the bashy side with a zero-model agent; this runs a
real vendor (one request) and fails closed on anything it cannot prove:

  * Quota: `bashy model quota --json` is read before (and after) the request;
    the vendor's 5h/week windows must be measured, ok and under --max-5h /
    --max-week, or nothing is launched.
  * Guard: a sandbox-exec profile denies file-write* into every operator home
    (arm_home.protected_homes) and into a decoy dir, SIGKILLing the writer,
    and denies exec of /usr/bin/security (the Keychain CLI: an arm must not
    write the operator's login). `bashy dag run` gets it as BENCH_GUARD, so
    DAG.md runs every isolated arm command under it. Negative controls, before
    AND after the arm, under the same profile file: a decoy write and a write
    to a fresh path in the real HOME must both be killed and leave nothing.
  * Containment: every vendor process seen in the runner's process tree must
    report sandboxed (libsystem sandbox_check(pid)); none seen, or one
    unsandboxed, fails.
  * Real HOME: fingerprints of the vendor config and bashy stores (as the
    canary), the operator's Claude projects listing and the Keychain item's
    metadata (never its secret) must be unchanged, except for writes the
    canary's attribution rules explain as the live host's own.
  * Sandbox denials by the tree's pids into a real home (unified log) fail.
  * The run must show task delivery ("instruction delivered"), no trust
    prompt, a graded results row (not void, not a grader error), and usage
    attributable to this arm: an assistant message with token usage in the
    arm's own vendor transcript whose cwd is the arm workspace.

Raw evidence (session/screen logs, arm evidence, results row, quota before/
after, denials, report.json) goes to --evidence. Exit 0 only when scored and
clean; 1 = ran but failed a check (reported unscored where applicable);
2 = refused before any vendor request.

Usage:
  guarded_live_arm.py --agent claude-opus5.5 --task t6-pdf-fact --skill off \\
      --evidence DIR [--bashy PATH] [--budget 110]
"""
from __future__ import annotations

import argparse
import ctypes
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arm_home
import real_home_canary as canary

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KILLED = canary.KILLED
TRUST_RE = re.compile(r"trust this folder|Do you trust the files|Yes, I trust", re.I)
KEYCHAIN_SERVICE = arm_home.KEYCHAIN_SERVICE


def guard_profile(homes: list[str], decoy: str) -> str:
    deny = " ".join(f'(subpath "{p}")' for p in [*homes, decoy])
    return ("(version 1)\n(allow default)\n"
            f"(deny file-write* {deny} (with send-signal SIGKILL))\n"
            '(deny process-exec (literal "/usr/bin/security"))\n')


def negative_controls(sb: str, decoy: str, home: str) -> dict:
    """Both writes must be killed by the profile and leave nothing behind."""
    out = {}
    for name, target in (("decoy", os.path.join(decoy, "probe")),
                         ("real_home", os.path.join(home, f".bench-guard-probe-{uuid.uuid4().hex[:8]}"))):
        r = subprocess.run(["sandbox-exec", "-f", sb, "/bin/sh", "-c", f"echo x > '{target}'"],
                           capture_output=True, timeout=30)
        out[name] = {"rc": r.returncode, "killed": r.returncode in KILLED,
                     "absent": not os.path.lexists(target)}
        if not out[name]["absent"] and name == "real_home":
            os.unlink(target)  # our own probe: a broken guard must not leave it behind
    out["ok"] = all(v["killed"] and v["absent"] for v in out.values() if isinstance(v, dict))
    return out


def _quota_rows(raw: str, label: str) -> dict | None:
    try:
        items = json.loads(raw)["items"]
    except (ValueError, KeyError, TypeError):
        return None
    return {i["window"]: i for i in items if i.get("label") == label and i.get("window")}


def quota(bashy: str, label: str) -> tuple[dict, str, dict]:
    """(rows by window, raw JSON, how they were read). A `--refresh` read is
    tried first; if it fails, times out, or leaves a row stale, that is
    recorded as refresh_error and the cached rows are the fallback, which
    quota_ok still accepts only when measured and NOT stale."""
    meta: dict = {}
    try:
        r = subprocess.run([bashy, "model", "quota", "--refresh", "--json", "--provider", label],
                           capture_output=True, text=True, timeout=60)
        rows = _quota_rows(r.stdout, label)
        if r.returncode == 0 and rows and not any(v.get("stale") for v in rows.values()):
            meta["source"] = "refresh"
            return rows, r.stdout, meta
        meta["refresh_error"] = (f"rc={r.returncode} rows={sorted(rows or {})} "
                                 f"stale={sorted(w for w, v in (rows or {}).items() if v.get('stale'))} "
                                 f"stderr={r.stderr.strip()[:200]!r}")
    except subprocess.TimeoutExpired:
        meta["refresh_error"] = "timeout after 60s"
    r = subprocess.run([bashy, "model", "quota", "--json"], capture_output=True, text=True, timeout=60)
    meta["source"] = "cached-fallback"
    rows = _quota_rows(r.stdout, label)
    meta["fallback_nonstale"] = bool(rows) and not any(v.get("stale") for v in rows.values())
    return rows or {}, r.stdout, meta


def balance(bashy: str, provider: str) -> tuple[dict, str]:
    r = subprocess.run([bashy, "model", "quota", "--provider", provider, "--json"],
                       capture_output=True, text=True, timeout=60)
    try:
        rows = json.loads(r.stdout)["items"]
    except (ValueError, KeyError):
        return {}, r.stdout
    valid = [row for row in rows if row.get("label") == provider]
    return (valid[0] if len(valid) == 1 else {}), r.stdout


def balance_ok(row: dict, remaining_usd: float) -> str | None:
    if (row.get("status") != "ok" or row.get("stale") is not False
            or row.get("classification") != "measured" or row.get("balance_unit") != "USD"
            or not isinstance(row.get("balance"), (int, float)) or isinstance(row.get("balance"), bool)):
        return "no fresh measured USD balance"
    if row["balance"] < remaining_usd:
        return f"USD balance {row['balance']} below remaining ceiling {remaining_usd}"
    return None


def ycode_native_budget(bashy: str) -> float | None:
    """Read the authored YOLO route's pre-request dollar ceiling."""
    r = subprocess.run([bashy, "ycode", "--yolo", "config", "show"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode:
        return None
    try:
        value = json.loads(r.stdout)["spec"]["routes"]["main"]["budget"]["maxCostUSD"]
    except (ValueError, KeyError, TypeError):
        return None
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def quota_ok(rows: dict, max_5h: int, max_week: int) -> str | None:
    for window, cap in (("5h", max_5h), ("week", max_week)):
        row = rows.get(window)
        if not row:
            return f"no measured {window} quota row"
        if row.get("status") != "ok" or row.get("stale") or not isinstance(row.get("used_percent"), (int, float)):
            return f"{window} quota not ok/measured: {row.get('status')} stale={row.get('stale')}"
        if row["used_percent"] >= cap:
            return f"{window} quota {row['used_percent']}% >= cap {cap}%"
    return None


SKILL_MD = ".claude/skills/bashy/SKILL.md"  # skill_arm.PROJECT_SKILL_ROOTS["claude"]


def _sha(path: str) -> str | None:
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest() if os.path.isfile(path) else None


def skill_preflight(bashy: str, sb: str, root: str, tool: str, arm: str) -> dict:
    """Zero-model rehearsal of the DAG's skill export under the same guard and a
    tool-less isolated env: the on arm must produce the SKILL.md the vendor
    reads, the off arm must not. Returns its sha so the real arm can be matched."""
    scratch = os.path.join(root, "skill-pre")
    ws, pre = os.path.join(scratch, "ws"), os.path.join(scratch, "pre")
    os.makedirs(ws)
    subprocess.run(["/usr/bin/git", "-C", ws, "init", "-q", "-b", "main"], check=True)
    open(os.path.join(ws, "README"), "w").write("skill preflight\n")
    subprocess.run(["/usr/bin/git", "-C", ws, "add", "-A"], check=True)
    subprocess.run(["/usr/bin/git", "-C", ws, "-c", "user.name=bench", "-c", "user.email=bench@example.invalid",
                    "commit", "-qm", "fixture"], check=True)
    prep = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "arm_home.py"), "prepare",
                           "--arm-dir", pre, "--tool", "none"], capture_output=True, text=True, timeout=120)
    out: dict = {"arm": arm, "prepare_rc": prep.returncode}
    if prep.returncode:
        out["ok"], out["error"] = False, prep.stderr.strip()[:300]
        return out
    env = dict(os.environ, PATH=os.path.dirname(bashy) + os.pathsep + os.environ.get("PATH", ""))
    env.update(l.split("=", 1) for l in prep.stdout.splitlines() if "=" in l)
    r = subprocess.run(["sandbox-exec", "-f", sb, sys.executable, os.path.join(REPO, "scripts", "skill_arm.py"),
                        "--workspace", ws, "--tool", tool, "--arm", arm],
                       env=env, capture_output=True, text=True, timeout=120)
    sha = _sha(os.path.join(ws, SKILL_MD))
    out.update(rc=r.returncode, killed=r.returncode in KILLED, skill_md=sha is not None, skill_sha256=sha,
               stderr=r.stderr.strip()[:300])
    out["ok"] = r.returncode == 0 and (sha is not None) == (arm == "on")
    shutil.rmtree(scratch, ignore_errors=True)
    return out


def zero_model_canary(bashy: str, ev: str) -> dict:
    """real_home_canary.py in-process (benchbot-dry, no vendor), before the request."""
    rep = canary.run(bashy, None)
    with open(os.path.join(ev, "canary.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    return {"verdict": rep.get("verdict"), "failures": rep.get("failures", []),
            "sandbox_denials": rep.get("sandbox_denials", []), "known_leaks": rep.get("known_leaks", {})}


def keychain_meta() -> list[str]:
    """Attributes (never secrets) of every Claude Keychain item."""
    r = subprocess.run(["/usr/bin/security", "dump-keychain"], capture_output=True, text=True, timeout=60)
    out, cur = [], []
    for line in r.stdout.splitlines():
        if line.startswith("keychain:"):
            if any("Claude Code" in l for l in cur):
                out.append(" ".join(l.strip() for l in cur if re.search(r'"(svce|acct|mdat|cdat)"', l)))
            cur = []
        cur.append(line)
    if any("Claude Code" in l for l in cur):
        out.append(" ".join(l.strip() for l in cur if re.search(r'"(svce|acct|mdat|cdat)"', l)))
    return sorted(out)


def projects_listing(homes: list[str]) -> dict[str, list[str]]:
    out = {}
    for h in homes:
        d = os.path.join(h, ".claude", "projects")
        out[d] = sorted(os.listdir(d)) if os.path.isdir(d) else []
    return out


_sandbox_check = None


def sandboxed(pid: int) -> int:
    global _sandbox_check
    if _sandbox_check is None:
        _sandbox_check = ctypes.CDLL("/usr/lib/libSystem.dylib").sandbox_check
        _sandbox_check.restype = ctypes.c_int
    return _sandbox_check(pid, None, 0)


def proc_env(pid: int, keys: tuple[str, ...]) -> dict:
    """Only the named (path) variables of a live process's environment."""
    r = subprocess.run(["/bin/ps", "-E", "-ww", "-o", "command=", "-p", str(pid)], capture_output=True, text=True)
    out = {k: None for k in keys}
    for k in keys:
        m = re.search(rf"(?:^|\s){k}=(\S+)", r.stdout)
        if m:
            out[k] = m.group(1)
    return out


class VendorWatch(canary.Tree):
    """Capture the runner tree so wrapper ancestors and guarded descendants can be separated."""

    def __init__(self):
        self.vendor: dict[int, dict] = {}
        self.processes: dict[int, dict] = {}
        self.comms: set[str] = set()
        super().__init__()

    def _poll(self):
        while not self.stop.wait(0.25):
            r = subprocess.run(["/bin/ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True)
            rows = []
            for l in r.stdout.splitlines():
                parts = l.split(None, 2)
                if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                    rows.append((int(parts[0]), int(parts[1]), parts[2]))
            grew = True
            while grew:
                grew = False
                for pid, ppid, _ in rows:
                    if ppid in self.pids and pid not in self.pids:
                        self.pids.add(pid)
                        grew = True
            for pid, ppid, command in rows:
                if pid in self.pids and pid not in self.processes:
                    try:
                        state = sandboxed(pid)
                    except (OSError, ProcessLookupError):
                        continue  # exited between ps and sandbox_check
                    self.processes[pid] = {"pid": pid, "ppid": ppid,
                                           "comm": command.split()[0], "command": command,
                                           "sandboxed": state,
                                           **(proc_env(pid, ("HOME", "CLAUDE_CONFIG_DIR"))
                                              if os.path.basename(command.split()[0]) in self.comms else {})}


def classify_vendor_processes(processes: dict[int, dict], runner_pid: int,
                              vendor_comms: set[str]) -> tuple[list[dict], list[dict], list[dict]]:
    """Wrapper ancestors precede the first guarded node. Every process below
    a guarded node must remain guarded, including children with other names."""
    guarded: set[int] = set()
    pending = set(processes) - {runner_pid}
    while pending:
        ready = {pid for pid in pending if processes[pid]["ppid"] not in pending}
        if not ready:
            raise ValueError("cycle in observed process ancestry")
        for pid in ready:
            row = processes[pid]
            if row["sandboxed"] == 1 or row["ppid"] in guarded:
                guarded.add(pid)
        pending -= ready
    def escaped_vendor(row: dict) -> bool:
        command = row.get("command", "")
        words = command.split()
        name = os.path.basename(row["comm"])
        return (name in vendor_comms and
                (name != "bashy" or (len(words) > 1 and words[1] in {"chat", "ycode"})))

    wrappers = [row for pid, row in processes.items()
                if pid != runner_pid and pid not in guarded and not escaped_vendor(row)]
    # Bashy DAG wrappers can spawn preflight helpers beside the guarded arm.
    # A vendor CLI or bashy chat launched in that branch remains a failure.
    descendants = [row for pid, row in processes.items()
                   if pid != runner_pid and (pid in guarded or escaped_vendor(row))]
    vendors = [row for row in descendants if os.path.basename(row["comm"]) in vendor_comms]
    return wrappers, descendants, vendors



def tree_denials(log_text: str, pids: set[int], homes: list[str]) -> tuple[list[str], list[str]]:
    """(file-write denials into a real home, every other denial) by the tree."""
    writes, other = [], []
    for line in log_text.splitlines():
        m = re.search(r"Sandbox: ([^(]+)\((\d+)\) deny\(\d+\) (\S+) ?(.*)", line)
        if not m or int(m.group(2)) not in pids:
            continue
        op, target = m.group(3), m.group(4).strip()
        if op.startswith("file-write") and any(target == h or target.startswith(h + "/") for h in homes):
            writes.append(line.strip())
        else:
            other.append(line.strip())
    return writes, other


def split_runner(paths: list[str], since_ns: int, runner_pid: int) -> tuple[list[str], list[dict]]:
    """The parent `bashy dag run` is NOT sandboxed (it keeps its own real-HOME
    state, e.g. the room timeline lock). A bashy store whose every recorded
    lock holder is that runner pid is reported as a runner write, not an arm
    write; anything else stays against the arm."""
    arm, runner = [], []
    for p in paths:
        recs = []
        for h in canary.holders(p, since_ns):
            try:
                with open(h) as fh:  # read only
                    recs.append(json.load(fh))
            except (OSError, ValueError):
                recs.append(None)
        if recs and all(isinstance(r, dict) and r.get("pid") == runner_pid for r in recs):
            runner.append({"path": p, "holders": [f"{r.get('name')}:{r['pid']}" for r in recs]})
        else:
            arm.append(p)
    return arm, runner


def usage_records(arm_evidence: str, ws_real: str, model: str | None) -> list[dict]:
    """Assistant messages with token usage in the arm's Claude transcripts."""
    out = []
    for path in glob.glob(os.path.join(arm_evidence, ".claude", "projects", "*", "*.jsonl")):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                msg = rec.get("message") if isinstance(rec, dict) else None
                if rec.get("type") != "assistant" or not isinstance(msg, dict) or not msg.get("usage"):
                    continue
                cwd = os.path.realpath(rec.get("cwd") or "")
                out.append({"file": os.path.relpath(path, arm_evidence), "cwd": cwd,
                            "cwd_is_ws": cwd == ws_real, "model": msg.get("model"),
                            "model_ok": model is None or msg.get("model") == model,
                            "session": rec.get("sessionId"), "request": rec.get("requestId"),
                            "usage": {k: v for k, v in msg["usage"].items() if isinstance(v, (int, float))}})
    return out


def ycode_receipt(arm_evidence: str, model: str | None) -> tuple[list[dict], int]:
    """Read ycode's isolated event log and final committed message payload.

    The append-only log counts provider requests, including failed and
    uncommitted ones. The final session payload supplies exact provider token
    usage. A mixed-session arm fails closed rather than attributing host work.
    """
    root = os.path.join(arm_evidence, ".bashy", "ycode", "harness")
    path = os.path.join(root, "sessions", "events.jsonl")
    with open(path, encoding="utf-8") as fh:
        events = [json.loads(line) for line in fh if line.strip()]
    sessions = {e.get("session_id") for e in events if e.get("session_id")}
    if len(sessions) != 1:
        raise ValueError(f"expected one isolated ycode session, found {len(sessions)}")
    requests = [e for e in events if e.get("type") == "llm.requested"]
    commits = [e for e in events if e.get("type") == "session.turn-committed"]
    if not commits:
        return [], len(requests)
    ref = commits[-1].get("data", {}).get("messages_ref", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", ref):
        raise ValueError("invalid ycode messages_ref")
    payload = os.path.join(root, "payloads", ref.removeprefix("sha256:"))
    with open(payload, encoding="utf-8") as fh:
        messages = json.load(fh)
    out = []
    for msg in messages:
        if msg.get("role") != "assistant" or not isinstance(msg.get("usage"), dict):
            continue
        usage = msg["usage"]
        if not all(isinstance(usage.get(k), int) and not isinstance(usage[k], bool) and usage[k] >= 0
                   for k in ("input_tokens", "output_tokens")):
            raise ValueError("ycode assistant usage lacks exact token counts")
        # Ycode's committed assistant messages omit a model id. The isolated
        # fleet binding and llm.requested model_ref establish the route.
        refs = {e.get("data", {}).get("model_ref") for e in requests}
        out.append({"session": next(iter(sessions)), "model": model,
                    "model_source": "fleet binding; ycode route primary",
                    "model_ok": refs == {"primary"},
                    "usage": {k: v for k, v in usage.items() if isinstance(v, int) and not isinstance(v, bool)}})
    return out, len(requests)


def run(args) -> int:
    ev = os.path.abspath(args.evidence)
    os.makedirs(ev, exist_ok=True)
    report: dict = {"agent": args.agent, "pack": args.pack, "task": args.task, "skill": args.skill,
                    "bashy": args.bashy, "started": datetime.datetime.now().astimezone().isoformat(),
                    "verdict": "REFUSED", "failures": []}

    def save(code: int) -> int:
        report["finished"] = datetime.datetime.now().astimezone().isoformat()
        with open(os.path.join(ev, "report.json"), "w") as fh:
            json.dump(report, fh, indent=1)
        print(json.dumps({k: report.get(k) for k in ("verdict", "score", "failures")}, indent=1))
        return code

    if sys.platform != "darwin" or not shutil.which("sandbox-exec"):
        report["failures"].append("no sandbox-exec write-deny guard on this host")
        return save(2)
    homes = arm_home.protected_homes()
    report["protected_homes"] = homes
    tool = args.tool or subprocess.run([args.bashy, "agent", "show", args.agent, "--field", "tool"],
                                       capture_output=True, text=True).stdout.strip()
    model = args.model
    report["tool"], report["model"] = tool, model

    if tool == "ycode":
        bound = subprocess.run([args.bashy, "agent", "show", args.agent, "--field", "model"],
                               capture_output=True, text=True, timeout=30)
        report["fleet_model"] = bound.stdout.strip()
        if bound.returncode or not model or report["fleet_model"] != model:
            report["failures"].append("fleet model binding does not match requested Kimi model")
        report["native_route_budget_usd"] = ycode_native_budget(args.bashy)
        if report["native_route_budget_usd"] is None or report["native_route_budget_usd"] > args.spend_ceiling:
            report["failures"].append("ycode native route budget is absent or exceeds approved ceiling")
        bal, raw = balance(args.bashy, args.quota_label or "kimi")
        with open(os.path.join(ev, "quota.before.json"), "w", encoding="utf-8") as fh:
            fh.write(raw)
        report["balance_before_usd"] = bal.get("balance")
        why = balance_ok(bal, args.spend_ceiling)
        if why:
            report["failures"].append(f"balance gate: {why}")
        if args.spend_ceiling > 3 or args.budget > 100 or args.quiet != 20:
            report["failures"].append("ycode arm exceeds approved native budget or timing")
        if report["failures"]:
            return save(2)
    else:
        rows, raw, report["quota_before_read"] = quota(args.bashy, args.quota_label or tool)
        open(os.path.join(ev, "quota.before.json"), "w").write(raw)
        report["quota_before"] = {w: r.get("used_percent") for w, r in rows.items()}
        why = quota_ok(rows, args.max_5h, args.max_week)
        if why:
            report["failures"].append(f"quota gate: {why}")
            return save(2)

    root = os.path.realpath(tempfile.mkdtemp(prefix="s10g.", dir="/tmp"))
    arm_home.assert_outside(root, homes)
    decoy = os.path.join(root, "decoy")
    os.makedirs(decoy)
    sb = os.path.join(root, "guard.sb")
    with open(sb, "w") as fh:
        fh.write(guard_profile(homes, decoy))
    shutil.copyfile(sb, os.path.join(ev, "guard.sb"))
    try:
        report["negative_control_before"] = nc = negative_controls(sb, decoy, homes[0])
        if not nc["ok"]:
            report["failures"].append(f"guard not live before the arm: {nc}")
            return save(2)
        if not args.skip_canary:
            report["canary_before"] = cb = zero_model_canary(args.bashy, ev)
            if cb["verdict"] != "PASS":
                report["failures"].append(f"zero-model real-HOME canary failed before the request: {cb['failures']}")
                return save(2)
        report["skill_preflight"] = sp = skill_preflight(args.bashy, sb, root, tool, args.skill)
        if not sp["ok"]:
            report["failures"].append(f"skill {args.skill} export preflight failed: {sp}")
            return save(2)

        runs = os.path.join(root, "runs")
        since = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        since_ns = time.time_ns()
        fp_before = canary.fingerprint(homes)
        kc_before, pj_before = keychain_meta(), projects_listing(homes)

        env = dict(os.environ, PATH=os.path.dirname(args.bashy) + os.pathsep + os.environ.get("PATH", ""),
                   BENCH_GUARD=sb, BENCH_ARM_ROOT=root, TMPDIR=root, PYTHONDONTWRITEBYTECODE="1",
                   BENCH_CLAUDE_KEYCHAIN="1" if tool == "claude" else "")
        argv = [args.bashy, "dag", "run", f"AGENT={args.agent}", f"PACK={args.pack}", f"TASK={args.task}",
                f"RUNS={runs}", "K=1", "ATTEMPTS=1", f"SKILL={args.skill}", f"BUDGET={args.budget}",
                f"QUIET={args.quiet}", f"THINK={args.quiet * 3}", f"MIN_POST_STEER={args.quiet}"]
        report["dag_argv"] = argv
        watch = VendorWatch()
        watch.comms = set(args.vendor_comm)
        t0 = time.time()
        with open(os.path.join(ev, "dag.log"), "w") as log:
            proc = subprocess.Popen(argv, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
            watch.add_root(proc.pid)
            try:
                rc = proc.wait(timeout=180 if tool == "ycode" else args.budget + 75)
            except subprocess.TimeoutExpired:
                proc.kill()
                rc = proc.wait()
                report["failures"].append("dag run exceeded its wall bound and was killed")
        report["dag_rc"], report["wall_s"] = rc, round(time.time() - t0, 1)
        time.sleep(1)
        watch.stop.set()
        for pid in sorted(watch.pids - {proc.pid}):  # nothing of the arm may outlive it
            try:
                os.kill(pid, 0)
                report.setdefault("survivors", []).append(pid)
                os.kill(pid, 9)
            except OSError:
                pass

        report["negative_control_after"] = nc = negative_controls(sb, decoy, homes[0])
        if not nc["ok"]:
            report["failures"].append(f"guard not live after the arm: {nc}")
        fp_after = canary.fingerprint(homes)
        changed = canary.attribute(canary.diff(fp_before, fp_after), since_ns, watch.pids,
                                   marker=root, claude_pids=canary.live_claude(watch.pids))
        changed["canary"], report["runner_real_home_writes"] = split_runner(changed["canary"], since_ns, proc.pid)
        report["real_home_changed"], report["host_concurrent_writes"] = changed["canary"], changed["host"]
        if changed["canary"]:
            report["failures"].append(f"real HOME paths changed: {changed['canary']}")
        kc_after = keychain_meta()
        report["keychain_unchanged"] = kc_before == kc_after
        if kc_before != kc_after:
            report["failures"].append(f"Claude Keychain items changed: {sorted(set(kc_after) ^ set(kc_before))}")
        slug = root.replace("/", "-")
        new = {d: sorted(set(v) - set(pj_before.get(d, []))) for d, v in projects_listing(homes).items()}
        hits = {d: [n for n in v if slug in n or "s10g" in n] for d, v in new.items()}
        if any(hits.values()):
            report["failures"].append(f"arm transcript in the real Claude projects dir: {hits}")

        time.sleep(2)
        lg = subprocess.run(["log", "show", "--style", "compact", "--start", since, "--predicate",
                             'subsystem == "com.apple.sandbox.reporting"'],
                            capture_output=True, text=True, timeout=180)
        writes, other = tree_denials(lg.stdout, watch.pids, homes)
        report["sandbox_denials"], report["sandbox_other_denials"] = writes, other[:50]
        if writes:
            report["failures"].append(f"write into a real home attempted: {writes[:3]}")

        wrappers, descendants, vendors = classify_vendor_processes(watch.processes, proc.pid, watch.comms)
        report["wrapper_ancestors"] = wrappers
        report["guarded_descendants"] = descendants
        report["vendor_processes"] = vendors
        if not vendors:
            report["failures"].append(f"no {sorted(watch.comms)} process seen under the runner (not launched?)")
        if not all(v["sandboxed"] == 1 for v in descendants):
            report["failures"].append("process below guarded arm escaped sandbox")
        iso = [v for v in vendors if not all(v.get(k) and os.path.realpath(v[k]).startswith(root + "/")
                                               for k in ("HOME", "CLAUDE_CONFIG_DIR"))]
        if iso:
            report["failures"].append(f"vendor process without an isolated HOME/CLAUDE_CONFIG_DIR: {iso}")

        # The DAG record: $RUNS/$AGENT/$PACK-$TASK/1 (+ .session.log/.screen.log/.arm).
        rec = os.path.join(runs, args.agent, f"{args.pack}-{args.task}", "1")
        for suffix in (".session.log", ".screen.log"):
            if os.path.isfile(rec + suffix):
                shutil.copyfile(rec + suffix, os.path.join(ev, "run" + suffix))
        for extra in glob.glob(rec + ".arm") + glob.glob(rec + ".launch*.arm"):
            shutil.copytree(extra, os.path.join(ev, os.path.basename(extra).replace("1.", "run.", 1)),
                            symlinks=True, dirs_exist_ok=True)
        if os.path.isdir(rec):
            shutil.copytree(rec, os.path.join(ev, "workspace"), symlinks=True, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(".git"))
            gl = subprocess.run(["/usr/bin/git", "-C", rec, "log", "--format=%h %s", "-n", "20"],
                                capture_output=True, text=True)
            open(os.path.join(ev, "workspace.gitlog"), "w").write(gl.stdout)
        res = os.path.join(runs, "results.jsonl")
        row = None
        if os.path.isfile(res):
            shutil.copyfile(res, os.path.join(ev, "results.jsonl"))
            lines = [l for l in open(res).read().splitlines() if l.strip()]
            row = json.loads(lines[-1]) if lines else None
        report["result"] = row

        # The skill the vendor actually saw: the graded workspace copy.
        got = _sha(os.path.join(ev, "workspace", SKILL_MD))
        report["workspace_skill"] = {"skill_md": got is not None, "skill_sha256": got,
                                     "matches_preflight": got == sp.get("skill_sha256")}
        if os.path.isdir(os.path.join(ev, "workspace")) and ((got is not None) != (args.skill == "on")
                                                              or got != sp.get("skill_sha256")):
            report["failures"].append(f"arm workspace skill does not match SKILL={args.skill}: {report['workspace_skill']}")
        session = open(rec + ".session.log", errors="replace").read() if os.path.isfile(rec + ".session.log") else ""
        screen = open(rec + ".screen.log", errors="replace").read() if os.path.isfile(rec + ".screen.log") else ""
        report["task_delivered"] = "instruction delivered" in session
        if not report["task_delivered"]:
            report["failures"].append("no task delivery ('instruction delivered') in the session log")
        if TRUST_RE.search(session + screen):
            report["failures"].append("trust prompt on the screen")
        if not row:
            report["failures"].append("no results row (unscored)")
        elif row.get("void") or "grader error" in str(row.get("why", "")) or "result_ok" not in row:
            report["failures"].append(f"no score evidence (unscored): {row.get('why')}")

        # The DAG makes the workspace with mktemp under TMPDIR (= root).
        arm_ev = os.path.join(ev, "run.arm")
        if tool == "ycode" and os.path.isdir(arm_ev):
            try:
                usage, request_count = ycode_receipt(arm_ev, model)
            except (OSError, ValueError, TypeError) as error:
                usage, request_count = [], 0
                report["failures"].append(f"invalid ycode usage receipt: {error}")
            report["arm_workspace"] = "isolated ycode session"
        else:
            cwds = {u["cwd"] for u in usage_records(arm_ev, "", None)} if os.path.isdir(arm_ev) else set()
            cand = sorted(d for d in cwds if d.startswith(root + "/bench-ws."))
            ws_real = cand[0] if len(cand) == 1 else ""
            report["arm_workspace"] = ws_real or sorted(cwds)
            usage = usage_records(arm_ev, ws_real, model) if os.path.isdir(arm_ev) else []
            request_count = len({u["request"] for u in usage if u["request"]})
        report["usage"] = usage
        report["usage_total"] = {k: sum(u["usage"].get(k, 0) for u in usage)
                                 for k in ("input_tokens", "output_tokens",
                                           "cache_creation_input_tokens", "cache_read_input_tokens")}
        if not any(u["model_ok"] and (tool == "ycode" or (u["cwd_is_ws"] and u["cwd"].startswith(root + "/"))) for u in usage):
            report["failures"].append("no attributable usage (arm transcript with token usage in the arm workspace)")
        report["requests"] = request_count
        if tool == "ycode" and request_count < 1:
            report["failures"].append("no ycode provider request recorded")
        # Not scoring evidence (a screen is not a usage record), but kept so an
        # arm whose transcript never reached disk is still diagnosable.
        plain = re.sub(r"\x1b\[[0-9;?>]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(\x07|\x1b\\)", "", screen)
        report["screen_usage_hints"] = {
            "statusline": sorted(set(re.findall(r"\| ?5h ?\d+%", plain))),
            "tokens": sorted(set(re.findall(r"[↓↑] ?\d+ ?tokens", plain)))}

        if tool == "ycode":
            bal, raw = balance(args.bashy, args.quota_label or "kimi")
            open(os.path.join(ev, "quota.after.json"), "w").write(raw)
            report["balance_after_usd"] = bal.get("balance")
            if balance_ok(bal, 0):
                report["failures"].append("no fresh measured after balance")
            if isinstance(report.get("balance_before_usd"), (int, float)) and isinstance(bal.get("balance"), (int, float)):
                report["balance_delta_usd"] = round(report["balance_before_usd"] - bal["balance"], 8)
        else:
            rows, raw, report["quota_after_read"] = quota(args.bashy, args.quota_label or tool)
            open(os.path.join(ev, "quota.after.json"), "w").write(raw)
            report["quota_after"] = {w: r.get("used_percent") for w, r in rows.items()}
            if quota_ok(rows, 101, 101):
                report["failures"].append(f"quota after not measured/nonstale: {quota_ok(rows, 101, 101)}")

        scored = bool(row) and "result_ok" in row and not row.get("void")
        if scored:
            report["score"] = {k: row.get(k) for k in ("points", "fail", "result_ok", "discovery",
                                                        "format_use", "why", "ended", "secs")}
        report["verdict"] = "PASS" if not report["failures"] else ("FAIL" if scored else "UNSCORED")
        return save(0 if not report["failures"] else 1)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--agent", required=True)
    ap.add_argument("--pack", default="skill-uptake")
    ap.add_argument("--task", required=True)
    ap.add_argument("--skill", default="off")
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--bashy", default=shutil.which("bashy"))
    ap.add_argument("--tool", help="the agent's tool (default: `bashy agent show AGENT --field tool`)")
    ap.add_argument("--model", help="expected transcript model id, e.g. claude-opus-5-5")
    ap.add_argument("--vendor-comm", action="append", default=None,
                    help="process name(s) of the vendor CLI that must be seen sandboxed (default: the tool)")
    ap.add_argument("--quota-label")
    ap.add_argument("--budget", type=int, default=110)
    ap.add_argument("--quiet", type=int, default=20)
    ap.add_argument("--max-5h", type=int, default=80)
    ap.add_argument("--max-week", type=int, default=90)
    ap.add_argument("--skip-canary", action="store_true", help="tests only: skip the zero-model canary")
    ap.add_argument("--spend-ceiling", type=float, default=3.0)
    args = ap.parse_args(argv)
    args.bashy = os.path.abspath(args.bashy)
    args.vendor_comm = args.vendor_comm or [args.tool or "claude"]
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

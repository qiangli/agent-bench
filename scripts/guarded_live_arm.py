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


def quota(bashy: str, label: str) -> tuple[dict, str]:
    r = subprocess.run([bashy, "model", "quota", "--json"], capture_output=True, text=True, timeout=60)
    raw = r.stdout
    try:
        items = json.loads(raw)["items"]
    except (ValueError, KeyError):
        return {}, raw
    return {i["window"]: i for i in items if i.get("label") == label and i.get("window")}, raw


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


class VendorWatch(canary.Tree):
    """The runner's process tree, plus a sandbox_check of every vendor pid."""

    def __init__(self):
        self.vendor: dict[int, dict] = {}
        self.comms: set[str] = set()
        super().__init__()

    def _poll(self):
        while not self.stop.wait(0.25):
            r = subprocess.run(["/bin/ps", "-axo", "pid=,ppid=,comm="], capture_output=True, text=True)
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
            for pid, ppid, comm in rows:
                if pid in self.pids and os.path.basename(comm) in self.comms and pid not in self.vendor:
                    self.vendor[pid] = {"pid": pid, "ppid": ppid, "comm": comm, "sandboxed": sandboxed(pid)}


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

    rows, raw = quota(args.bashy, args.quota_label or tool)
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
                rc = proc.wait(timeout=args.budget + 75)
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

        report["vendor_processes"] = list(watch.vendor.values())
        if not watch.vendor:
            report["failures"].append(f"no {sorted(watch.comms)} process seen under the runner (not launched?)")
        elif not all(v["sandboxed"] == 1 for v in watch.vendor.values()):
            report["failures"].append(f"vendor process outside the guard: {report['vendor_processes']}")

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
        cwds = {u["cwd"] for u in usage_records(arm_ev, "", None)} if os.path.isdir(arm_ev) else set()
        cand = sorted(d for d in cwds if d.startswith(root + "/bench-ws."))
        ws_real = cand[0] if len(cand) == 1 else ""
        report["arm_workspace"] = ws_real or sorted(cwds)
        usage = usage_records(arm_ev, ws_real, model) if os.path.isdir(arm_ev) else []
        report["usage"] = usage
        report["usage_total"] = {k: sum(u["usage"].get(k, 0) for u in usage)
                                 for k in ("input_tokens", "output_tokens",
                                           "cache_creation_input_tokens", "cache_read_input_tokens")}
        if not any(u["cwd_is_ws"] and u["model_ok"] and u["cwd"].startswith(root + "/") for u in usage):
            report["failures"].append("no attributable usage (arm transcript with token usage in the arm workspace)")
        report["requests"] = len({u["request"] for u in usage if u["request"]})
        # Not scoring evidence (a screen is not a usage record), but kept so an
        # arm whose transcript never reached disk is still diagnosable.
        plain = re.sub(r"\x1b\[[0-9;?>]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(\x07|\x1b\\)", "", screen)
        report["screen_usage_hints"] = {
            "statusline": sorted(set(re.findall(r"\| ?5h ?\d+%", plain))),
            "tokens": sorted(set(re.findall(r"[↓↑] ?\d+ ?tokens", plain)))}

        rows, raw = quota(args.bashy, args.quota_label or tool)
        open(os.path.join(ev, "quota.after.json"), "w").write(raw)
        report["quota_after"] = {w: r.get("used_percent") for w, r in rows.items()}

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
    args = ap.parse_args(argv)
    args.bashy = os.path.abspath(args.bashy)
    args.vendor_comm = args.vendor_comm or [args.tool or "claude"]
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

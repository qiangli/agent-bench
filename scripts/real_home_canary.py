#!/usr/bin/env python3
"""Zero-model canary: does the REAL bashy binary, run under an arm env built
from a poisoned inherited environment, leave the operator's real HOME alone?

The stub-only DAG test (test_dag_arm_wiring) proves the runner hands the arm
env to every command; it cannot prove that the bashy binary itself honours it.
This canary runs the candidate `bashy` (first on PATH, or --bashy) for real:

  * The inherited env is poisoned: CLAUDE_CONFIG_DIR, BASHY_HOME,
    BASHY_MB_DIR, BASHY_SPRINT_DIR, CODEX_HOME, XDG_*, GEMINI_CLI_HOME and
    OPENCODE_CONFIG_DIR all point into the real HOME; `arm_home.py prepare`
    builds the arm env on top of it, exactly as DAG.md does.
  * Write-deny guard: every arm command runs under macOS sandbox-exec with
    `(deny file-write* (subpath REAL_HOME) (with send-signal SIGKILL))`, so a
    write into a real home cannot happen and the offending process dies loudly
    (SIGKILL). A decoy run first proves the guard is live. Denials are also
    read back from the unified log (com.apple.sandbox.reporting), which catches
    a killed detached child whose exit status nobody waits for.
  * Commands: `bashy -c`, `chat sessions`, `todo list`, `inspect context`, and
    the arm launch path itself: `bashy chat --agent benchbot-dry -i` (benchbot
    calls no model), then `chat sessions`, `chat steer`, `chat steer --enter`,
    until the session's --timeout ends it.
  * Fingerprints (size, mtime, sha256) of the real ~/.claude.json, Claude
    settings/credentials and the real ~/.bashy stores those commands write
    are taken before and after, and must be unchanged. The live host (weave,
    other agents) keeps writing the shared bashy locks meanwhile, so a change
    is excused only when every bashy lock holder recorded for it is a pid
    outside the canary's own process tree (polled from ps), and a Claude file
    change only when an operator Claude process outside the tree is live and
    the file never mentions the canary's temp root; anything else fails.
  * Positive control: the arm HOME must hold the bashy state (room timeline,
    exec audit) that the same commands write, so session state still works.
  * Known leaks (commands NOT on the arm path) are probed last and reported,
    not failed: `bashy inbox` chmods the real ~/.bashy/inbox even with HOME and
    BASHY_HOME redirected (the launch sets BASHY_CHAT_INBOX=off).

No vendor CLI is launched. Usage:
  real_home_canary.py [--bashy PATH] [--evidence DIR] [--json]
Exit 0 PASS, 1 FAIL, 2 cannot run (no sandbox-exec / no bashy).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arm_home

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK = os.path.join(REPO, "packs", "steer", "t1-pivot")

# Real-home files the arm commands would write if isolation failed: Claude's
# config, and the real counterparts of the bashy stores the positive control
# finds in the arm HOME. Directories are fingerprinted one level deep.
CLAUDE_FILES = (".claude.json", ".claude/settings.json", ".claude/.credentials.json")
BASHY_STORES = (".bashy/sessions", ".bashy/sessions/logs", ".bashy/todo", ".bashy/mb",
                ".bashy/sprint", ".bashy/skills/probecache.json", ".bashy/coord/claims.lock",
                ".bashy/room/member-claims.lock", ".bashy/room/.timeline.lock")
# Arm-HOME paths that prove bashy session state works under isolation.
ARM_STATE = (".bashy/room/timeline.jsonl", ".bashy/exec")

POISON_KEYS = {
    "CLAUDE_CONFIG_DIR": ".claude", "BASHY_HOME": ".bashy", "BASHY_MB_DIR": ".bashy/mb",
    "BASHY_SPRINT_DIR": ".bashy/sprint", "CODEX_HOME": ".codex", "XDG_CONFIG_HOME": ".config",
    "XDG_DATA_HOME": ".local/share", "XDG_STATE_HOME": ".local/state",
    "GEMINI_CLI_HOME": "", "OPENCODE_CONFIG_DIR": ".config/opencode",
}
# Processes of the canary's own tree, for reading denials back from the log.
KILLED = (137, -9)  # SIGKILL via a shell, or as Popen reports it
TREE_PROCS = ("bashy", "python3", "Python", "git", "sh", "bash", "env", "benchbot")


def poisoned_env(base: dict[str, str], real_home: str) -> dict[str, str]:
    env = dict(base)
    for key, rel in POISON_KEYS.items():
        env[key] = os.path.join(real_home, rel) if rel else real_home
    return env


def _digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:  # read only
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(homes: list[str], rels=CLAUDE_FILES + BASHY_STORES) -> dict[str, list]:
    """path -> [kind, size, mtime_ns, mode, sha256|entries]; absent paths too."""
    out = {}
    for home in homes:
        for rel in rels:
            p = os.path.join(home, rel)
            if not os.path.lexists(p):
                out[p] = ["absent"]
                continue
            st = os.lstat(p)
            if os.path.isdir(p) and not os.path.islink(p):
                entries = sorted(os.listdir(p))
                out[p] = ["dir", st.st_mtime_ns, st.st_mode,
                          hashlib.sha256("\0".join(entries).encode()).hexdigest()]
            else:
                out[p] = ["file", st.st_size, st.st_mtime_ns, st.st_mode,
                          _digest(p) if os.path.isfile(p) else os.readlink(p)]
    return out


def diff(before: dict, after: dict) -> list[str]:
    return sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))


def profile(homes: list[str]) -> str:
    deny = " ".join(f'(subpath "{h}")' for h in homes)
    return f"(version 1)\n(allow default)\n(deny file-write* {deny} (with send-signal SIGKILL))\n"


def denials(log_text: str, homes: list[str]) -> list[str]:
    """Sandbox file-write denials into a protected home by the canary's tree."""
    hits = []
    for line in log_text.splitlines():
        if "deny(1) file-write" not in line or "Sandbox: " not in line:
            continue
        proc = line.split("Sandbox: ", 1)[1].split("(", 1)[0]
        if proc in TREE_PROCS and any(f" {h}/" in line or line.endswith(f" {h}") for h in homes):
            hits.append(line.strip())
    return hits


def read_denials(since: str, homes: list[str]) -> list[str]:
    time.sleep(2)  # sandboxd reports asynchronously
    r = subprocess.run(["log", "show", "--style", "compact", "--start", since, "--predicate",
                        'subsystem == "com.apple.sandbox.reporting"'],
                       capture_output=True, text=True, timeout=120)
    return denials(r.stdout, homes)


class Tree:
    """Every pid descended from the canary's sandboxed commands (polled from
    ps), so a real-HOME change can be attributed to the canary or to the host."""

    def __init__(self):
        self.roots: set[int] = set()
        self.pids: set[int] = set()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._poll, daemon=True)
        self.thread.start()

    def add_root(self, pid: int):
        self.roots.add(pid)
        self.pids.add(pid)

    def _poll(self):
        while not self.stop.wait(0.25):
            r = subprocess.run(["/bin/ps", "-axo", "pid=,ppid="], capture_output=True, text=True)
            pairs = [tuple(map(int, l.split())) for l in r.stdout.splitlines() if len(l.split()) == 2]
            grew = True
            while grew:
                grew = False
                for pid, ppid in pairs:
                    if ppid in self.pids and pid not in self.pids:
                        self.pids.add(pid)
                        grew = True


def holders(path: str, since_ns: int) -> list[str]:
    """bashy lock files that record who last wrote path: the lock itself, or
    the locks inside a changed directory touched since the canary started."""
    if path.endswith(".lock"):
        return [path]
    if os.path.isdir(path):
        return [os.path.join(path, n) for n in sorted(os.listdir(path))
                if n.endswith(".lock") and os.stat(os.path.join(path, n)).st_mtime_ns >= since_ns]
    return []


def live_claude(tree_pids: set[int]) -> list[int]:
    """Claude Code processes running outside the canary tree (the operator's
    own sessions, which rewrite ~/.claude.json on their own schedule)."""
    r = subprocess.run(["/bin/ps", "-axo", "pid=,comm="], capture_output=True, text=True)
    return [int(pid) for pid, _, comm in (l.strip().partition(" ") for l in r.stdout.splitlines())
            if os.path.basename(comm.strip()) == "claude" and int(pid) not in tree_pids]


def attribute(changed: list[str], since_ns: int, tree_pids: set[int], marker: str = "",
              claude_pids: list[int] = ()) -> dict[str, list]:
    """Split real-HOME changes into host writes and canary writes. Fail-closed:
    a change counts against the canary unless it is explained.

    * A bashy store is explained when every lock holder recorded for it is a
      pid outside the canary tree.
    * A Claude file is explained only when an out-of-tree Claude process is
      live AND the file does not mention the canary's temp root (a trust entry
      or project record for the canary workspace would)."""
    out = {"canary": [], "host": []}
    for p in changed:
        if os.path.basename(p) in {os.path.basename(f) for f in CLAUDE_FILES}:
            try:
                with open(p, "rb") as fh:  # read only
                    mentions = bool(marker) and marker.encode() in fh.read()
            except OSError:
                mentions = True
            if claude_pids and not mentions:
                out["host"].append({"path": p, "holders": [f"claude:{pid}" for pid in claude_pids]})
            else:
                out["canary"].append(p)
            continue
        recs = []
        for h in holders(p, since_ns):
            try:
                with open(h) as fh:  # read only
                    recs.append(json.load(fh))
            except (OSError, ValueError):
                recs.append(None)
        if recs and all(isinstance(r, dict) and isinstance(r.get("pid"), int)
                        and r["pid"] not in tree_pids for r in recs):
            out["host"].append({"path": p, "holders": [f"{r.get('name')}:{r['pid']}" for r in recs]})
        else:
            out["canary"].append(p)
    return out


class Canary:
    def __init__(self, bashy: str, homes: list[str], root: str):
        self.bashy, self.homes, self.root = bashy, homes, root
        self.sb = os.path.join(root, "deny-real-home.sb")
        with open(self.sb, "w") as fh:
            fh.write(profile(homes))
        self.steps: list[dict] = []
        self.failures: list[str] = []
        self.tree = Tree()

    def popen(self, argv, env, **kw):
        proc = subprocess.Popen(["sandbox-exec", "-f", self.sb, *argv], env=env, **kw)
        self.tree.add_root(proc.pid)
        return proc

    def guarded(self, argv, env, timeout=120, **kw):
        proc = self.popen(argv, env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kw)
        out, err = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)

    def step(self, name, argv, env, ok=lambda r: r.returncode == 0, **kw):
        r = self.guarded(argv, env, **kw)
        passed = r.returncode not in KILLED and ok(r)
        self.steps.append({"step": name, "rc": r.returncode, "ok": passed,
                           "out": (r.stdout + r.stderr)[-300:]})
        if not passed:
            self.failures.append(f"{name}: rc={r.returncode} {(r.stdout + r.stderr)[-200:]!r}")
        return r

    def guard_is_live(self) -> bool:
        decoy = os.path.realpath(tempfile.mkdtemp(prefix="canary-decoy.", dir=self.root))
        sb = os.path.join(self.root, "decoy.sb")
        with open(sb, "w") as fh:
            fh.write(profile([decoy]))
        r = subprocess.run(["sandbox-exec", "-f", sb, "/bin/sh", "-c", f"echo x > {decoy}/probe"],
                           capture_output=True, timeout=30)
        return r.returncode in KILLED and not os.path.exists(os.path.join(decoy, "probe"))


def run(bashy: str, evidence_dir: str | None = None) -> dict:
    homes = arm_home.protected_homes()
    report: dict = {"bashy": bashy, "protected_homes": homes, "verdict": "FAIL"}
    # Short root: bashy's per-session control socket lives in the arm HOME.
    root = tempfile.mkdtemp(prefix="canary.", dir="/tmp")
    arm_home.assert_outside(root, homes)
    try:
        c = Canary(bashy, homes, root)
        if not c.guard_is_live():
            report["failures"] = ["write-deny guard is not live (decoy write was not killed)"]
            return report
        report["guard"] = "sandbox-exec deny file-write* + SIGKILL (decoy verified)"

        base = poisoned_env(dict(os.environ), homes[0])
        base["PATH"] = os.path.dirname(bashy) + os.pathsep + base.get("PATH", "")
        arm = os.path.join(root, "arm")
        # Built from the poisoned env, as DAG.md builds armenv from the runner's.
        prep = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "arm_home.py"),
                               "prepare", "--arm-dir", arm, "--tool", "benchbot"],
                              env=base, capture_output=True, text=True, timeout=300)
        if prep.returncode:
            report["failures"] = [f"arm_home prepare failed: {prep.stderr.strip()}"]
            return report
        armenv = dict(line.split("=", 1) for line in prep.stdout.splitlines() if "=" in line)
        env = arm_home.arm_environ(base, armenv, homes)
        ah = armenv["HOME"]
        report["arm_home"] = ah
        report["poisoned"] = {k: base[k] for k in POISON_KEYS}
        report["arm_env"] = {k: env.get(k) for k in POISON_KEYS}

        ws = os.path.join(root, "ws")
        shutil.copytree(os.path.join(TASK, "fixture"), ws)
        for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                     ["-c", "user.name=bench", "-c", "user.email=bench@example.invalid",
                      "commit", "-qm", "fixture"]):
            subprocess.run(["git", *args], cwd=ws, env=env, check=True, capture_output=True)

        since = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        since_ns = time.time_ns()
        before = fingerprint(homes)

        c.step("bashy -c", [bashy, "-c", "echo canary-ok"], env,
               ok=lambda r: "canary-ok" in r.stdout, cwd=ws)
        c.step("chat sessions", [bashy, "chat", "sessions"], env, cwd=ws)
        c.step("todo list", [bashy, "todo", "list"], env, cwd=ws)
        c.step("inspect context", [bashy, "inspect", "context", "--json"], env, cwd=ws)

        launch_env = dict(env, BENCH_REF=os.path.join(TASK, "reference"),
                          BASHY_CHAT_INBOX="off", BASHY_ALLOW_UNSAFE_AGENT_LAUNCH="1")
        log = os.path.join(root, "session.log")
        with open(log, "w") as fh:
            proc = c.popen(
                [bashy, "chat", "--agent", "benchbot-dry", "-i", "--yolo",
                 "-m", "Read TASK.md and do the task.", "--cwd", ws,
                 "--task", "canary", "--timeout", "40s"],
                launch_env, stdout=fh, stderr=subprocess.STDOUT, cwd=ws)
        sid = None
        for _ in range(30):
            time.sleep(1)
            text = Path(log).read_text()
            if "(id " in text:
                sid = text.split("(id ", 1)[1].split(")", 1)[0]
                break
        if not sid:
            c.failures.append(f"launch printed no session id: {Path(log).read_text()[-300:]!r}")
        else:
            time.sleep(3)
            c.step("chat sessions (live)", [bashy, "chat", "sessions"], env,
                   ok=lambda r: r.returncode == 0 and sid in r.stdout, cwd=ws)
            c.step("chat steer", [bashy, "chat", "steer", sid, "canary steer"], env, cwd=ws)
            c.step("chat steer --enter", [bashy, "chat", "steer", sid, "--enter"], env, cwd=ws)
        rc = proc.wait(timeout=120)
        text = Path(log).read_text()
        c.steps.append({"step": "chat launch", "rc": rc, "out": text[-300:]})
        if rc in KILLED or "instruction delivered" not in text:
            c.failures.append(f"chat launch: rc={rc} {text[-200:]!r}")
        if sid:
            steer_seen = subprocess.run(["git", "log", "--format=%s"], cwd=ws, env=env,
                                        capture_output=True, text=True).stdout
            report["benchbot_commits"] = steer_seen.split("\n")[:5]
            if "benchbot: steer received" not in steer_seen:
                c.failures.append("benchbot never recorded the steer (steer path not exercised)")

        after = fingerprint(homes)
        time.sleep(1)
        c.tree.stop.set()
        changed = attribute(diff(before, after), since_ns, c.tree.pids,
                            marker=root, claude_pids=live_claude(c.tree.pids))
        report["real_home_changed"] = changed["canary"]
        report["host_concurrent_writes"] = changed["host"]
        report["canary_pids_seen"] = len(c.tree.pids)
        if changed["canary"]:
            c.failures.append(f"real HOME paths changed: {changed['canary']}")
        report["sandbox_denials"] = read_denials(since, homes)
        if report["sandbox_denials"]:
            c.failures.append(f"write into a real home was attempted: {report['sandbox_denials'][:3]}")
        missing = [p for p in ARM_STATE if not os.path.exists(os.path.join(ah, p))]
        if missing:
            c.failures.append(f"bashy state missing from the arm HOME: {missing}")
        report["arm_state"] = [p for p in ARM_STATE if p not in missing]

        # Known leak, NOT on the arm path: probed last so it cannot mask the above.
        r = c.guarded([bashy, "inbox"], env, cwd=ws)
        report["known_leaks"] = {"bashy inbox": "killed: writes real ~/.bashy/inbox" if r.returncode in KILLED
                                 else f"clean (rc={r.returncode})"}

        if evidence_dir:
            arm_home.evidence(arm, evidence_dir, homes)
            shutil.copyfile(log, os.path.join(evidence_dir, "canary.session.log"))
        report["steps"], report["failures"] = c.steps, c.failures
        report["verdict"] = "PASS" if not c.failures else "FAIL"
        return report
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bashy", default=shutil.which("bashy"))
    ap.add_argument("--evidence", help="copy the arm's raw evidence here (arm-specific RUNS path)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if sys.platform != "darwin" or not shutil.which("sandbox-exec"):
        print("canary: no write-deny guard (sandbox-exec) on this host", file=sys.stderr)
        return 2
    if not args.bashy or not os.access(args.bashy, os.X_OK):
        print("canary: no bashy binary (put the candidate first on PATH or pass --bashy)", file=sys.stderr)
        return 2
    report = run(os.path.abspath(args.bashy), args.evidence)
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        for s in report.get("steps", []):
            print(f"  {'ok ' if s.get('ok', True) else 'BAD'} {s['step']} rc={s['rc']}")
        for k, v in report.get("known_leaks", {}).items():
            print(f"  known leak (off the arm path): {k}: {v}")
        for f in report.get("failures", []):
            print(f"  FAIL {f}")
        print(f"real-home canary: {report['verdict']} ({report['bashy']})")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Zero-quota proof that Claude reads the skill-uptake on arm's export.

For each arm (off, on) this builds a workspace and an arm HOME exactly as the
DAG `run` task does (arm_home.py prepare, skill_arm.py under the arm env),
then runs the arm's Claude ONCE, non-interactively, against a local fake
Anthropic endpoint (ANTHROPIC_BASE_URL on 127.0.0.1, a dummy API key, no
Keychain seed). The fake endpoint records the /v1/messages request body and
answers 400, so no request ever reaches the provider and no quota is spent.
Claude, the export and every arm command run under the same write-deny
sandbox profile as a live arm when --guard is given.

The probe passes when the captured request's skill listing ("The following
skills are available for use with the Skill tool:") names bashy in the on arm
and not in the off arm. Whether bashy's description survived Claude's skill
listing budget is reported too (measured 2026-10-18, Claude 2.1.283: it does
not; the listing is over budget and bashy is listed by name only). Only
booleans and sizes go to the report; the request body itself is not kept (it
carries the operator's environment description).

A second check, `persistence`, reproduces S10's missing usage record with
zero quota: the arm's Claude TUI is started in a PTY against the same fake
endpoint (the dummy key pre-approved in the ARM's .claude.json, the workspace
trust preseeded there), with CLAUDE_CODE_CHILD_SESSION=1 inherited from the
runner, once with the S10 arm env and once with the current one. It types
the task prompt and counts the arm's transcripts: the old env must show
"Transcript saving is off" and keep none; the current env must keep one.

Usage: claude_skill_probe.py --evidence DIR [--bashy PATH] [--guard PROFILE.sb]
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import pty
import re
import shutil
import subprocess
import sys
import select
import signal
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arm_home

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "packs", "skill-uptake", "t6-pdf-fact", "fixture")
MARKER = "Drive bashy, the agentic shell"  # the exported SKILL.md description
LISTING = re.compile(r"skills are available for use with the Skill tool:\n\n((?:- [^\n]*\n?)+)")


def listing(body: str) -> list[str]:
    """The skill listing lines Claude put in a /v1/messages request."""
    try:
        req = json.loads(body)
    except ValueError:
        return []
    texts = []
    for part in [*(req.get("system") or []), *(req.get("messages") or [])]:
        content = part.get("content", part.get("text", "")) if isinstance(part, dict) else ""
        for x in content if isinstance(content, list) else [{"text": content}]:
            texts.append(str(x.get("text", "")) if isinstance(x, dict) else "")
    m = LISTING.search("\n".join(texts))
    return m.group(1).splitlines() if m else []


def fake_endpoint() -> tuple[http.server.HTTPServer, list[bytes]]:
    seen: list[bytes] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = self.rfile.read(int(self.headers.get("content-length") or 0))
            if "/messages" in self.path and "count_tokens" not in self.path:
                seen.append(body)
            out = json.dumps({"type": "error", "error": {"type": "invalid_request_error",
                                                         "message": "bench probe: no model"}}).encode()
            self.send_response(400)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        do_GET = do_POST  # noqa: N815

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


def probe(arm: str, bashy: str, claude: str, guard: list[str], root: str) -> dict:
    ws = tempfile.mkdtemp(prefix=f"ws-{arm}.", dir=root)
    shutil.copytree(FIXTURE, ws, dirs_exist_ok=True)
    git = ["git", "-C", ws, "-c", "user.name=bench", "-c", "user.email=bench@example.invalid"]
    subprocess.run(["git", "-C", ws, "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", ws, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "fixture"], check=True)
    armdir = tempfile.mkdtemp(prefix=f"arm-{arm}.", dir=root)
    env = arm_home.prepare(armdir, "claude")
    env.update(arm_home.clear_inherited(dict(os.environ), env))
    full = arm_home.arm_environ(dict(os.environ), env)
    full["PATH"] = os.path.dirname(bashy) + os.pathsep + full.get("PATH", "")
    sel = subprocess.run([*guard, sys.executable, os.path.join(REPO, "scripts", "skill_arm.py"),
                          "--workspace", ws, "--tool", "claude", "--arm", arm],
                         env=full, capture_output=True, text=True)
    out = {"arm": arm, "skill_arm_rc": sel.returncode,
           "workspace_skill": os.path.isfile(os.path.join(ws, ".claude/skills/bashy/SKILL.md"))}
    if sel.returncode:
        out["error"] = sel.stderr.strip()[-300:]
        return out
    srv, seen = fake_endpoint()
    try:
        full.update({"ANTHROPIC_BASE_URL": f"http://127.0.0.1:{srv.server_port}",
                     "ANTHROPIC_API_KEY": "sk-ant-bench-probe-not-a-key",
                     "CLAUDE_CODE_MAX_RETRIES": "0", "DISABLE_TELEMETRY": "1",
                     "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"})
        run = subprocess.run([*guard, claude, "-p", "Read TASK.md and do the task.",
                              "--dangerously-skip-permissions", "--max-turns", "1"],
                             cwd=ws, env=full, stdin=subprocess.DEVNULL, capture_output=True,
                             text=True, timeout=120)
    finally:
        srv.shutdown()
    body = seen[0].decode("utf-8", "replace") if seen else ""
    lines = listing(body)
    mine = [l for l in lines if re.match(r"- bashy(:|$)", l)]
    out.update({"claude_rc": run.returncode, "requests_captured": len(seen),
                "listing_skills": len(lines),
                "skill_listed": bool(mine), "description_listed": any(MARKER in l for l in mine),
                "transcripts": sorted(os.path.relpath(p, env["HOME"])
                                      for p in _jsonl(os.path.join(env["CLAUDE_CONFIG_DIR"], "projects")))})
    return out


DUMMY_KEY = "sk-ant-bench-probe-not-a-key"
WARN = "Transcript saving is off"


def persistence(claude: str, guard: list[str], root: str, current: bool) -> dict:
    """One PTY session with an inherited child-session marker; see the module doc."""
    ws = tempfile.mkdtemp(prefix="ws-tui.", dir=root)
    subprocess.run(["git", "-C", ws, "init", "-q"], check=True)
    env = arm_home.prepare(tempfile.mkdtemp(prefix="arm-tui.", dir=root), "claude")
    base = dict(os.environ, CLAUDE_CODE_CHILD_SESSION="1")
    if current:
        env.update(arm_home.clear_inherited(base, env))
        full = arm_home.arm_environ(base, env)
    else:  # the S10 arm env: no marker clearing, no persistence override
        env.pop("CLAUDE_CODE_FORCE_SESSION_PERSISTENCE")
        full = dict(base, **env)
    subprocess.run([sys.executable, os.path.join(REPO, "scripts", "trust_preseed.py"), "--workspace", ws,
                    "--home", env["CLAUDE_CONFIG_DIR"]], capture_output=True, check=True)
    cfg = os.path.join(env["CLAUDE_CONFIG_DIR"], ".claude.json")
    with open(cfg) as fh:
        data = json.load(fh)
    data["customApiKeyResponses"] = {"approved": [DUMMY_KEY[-20:]], "rejected": []}
    with open(cfg, "w") as fh:
        json.dump(data, fh)
    srv, seen = fake_endpoint()
    full.update({"ANTHROPIC_BASE_URL": f"http://127.0.0.1:{srv.server_port}", "ANTHROPIC_API_KEY": DUMMY_KEY,
                 "TERM": "xterm-256color", "COLUMNS": "200", "LINES": "50"})
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(ws)
        os.execvpe((guard or [claude])[0], [*guard, claude, "--dangerously-skip-permissions"], full)
    buf, start, sent = b"", time.time(), False
    try:
        while time.time() - start < 40:
            if not sent and time.time() - start > 12:
                os.write(fd, b"Read TASK.md")
                time.sleep(1)
                os.write(fd, b"\r")
                sent = True
            if select.select([fd], [], [], 0.5)[0]:
                try:
                    buf += os.read(fd, 65536)
                except OSError:
                    break
    finally:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        srv.shutdown()
    screen = re.sub(r"\s+", " ", re.sub(rb"\x1b\[[0-9;?>]*[ -/]*[@-~]", b" ", buf).decode("utf-8", "replace"))
    return {"arm_env": "current" if current else "s10",
            "CLAUDE_CODE_CHILD_SESSION": full.get("CLAUDE_CODE_CHILD_SESSION"),
            "CLAUDE_CODE_FORCE_SESSION_PERSISTENCE": full.get("CLAUDE_CODE_FORCE_SESSION_PERSISTENCE", "<unset>"),
            "tui_up": "Claude Code" in screen, "warning_shown": WARN in screen,
            "requests_captured": len(seen),
            "transcripts": len(_jsonl(os.path.join(env["CLAUDE_CONFIG_DIR"], "projects")))}


def _jsonl(root: str) -> list[str]:
    hits = []
    for d, _, files in os.walk(root):
        hits += [os.path.join(d, f) for f in files if f.endswith(".jsonl")]
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--bashy", default=shutil.which("bashy") or "bashy")
    ap.add_argument("--claude", help="vendor binary (default: bashy's pinned claude tool binary)")
    ap.add_argument("--guard")
    a = ap.parse_args(argv)
    claude = a.claude or os.path.expanduser(subprocess.run(
        [a.bashy, "tool", "show", "claude", "--field", "cli.binary"],
        capture_output=True, text=True).stdout.strip().replace("$HOME", "~"))
    guard = ["sandbox-exec", "-f", a.guard] if a.guard else []
    root = tempfile.mkdtemp(prefix="s11probe.", dir="/tmp")
    arm_home.assert_outside(root)
    try:
        arms = [probe(arm, os.path.abspath(a.bashy), claude, guard, root) for arm in ("off", "on")]
        tui = [persistence(claude, guard, root, current) for current in (False, True)]
    finally:
        shutil.rmtree(root, ignore_errors=True)
    off, on = arms
    ok = (on.get("skill_listed") is True and off.get("skill_listed") is False
          and on.get("listing_skills", 0) >= 1 and off.get("listing_skills", 0) >= 1)
    old, new = tui
    persisted = (old["tui_up"] and old["warning_shown"] and old["transcripts"] == 0
                 and new["tui_up"] and not new["warning_shown"] and new["transcripts"] >= 1)
    ok = ok and persisted
    version = subprocess.run([claude, "--version"], capture_output=True, text=True).stdout.strip()
    report = {"verdict": "PASS" if ok else "FAIL", "guarded": bool(guard), "claude": version, "arms": arms,
              "persistence": {"verdict": "PASS" if persisted else "FAIL", "sessions": tui}}
    os.makedirs(a.evidence, exist_ok=True)
    with open(os.path.join(a.evidence, "skill-probe.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print(json.dumps(report, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

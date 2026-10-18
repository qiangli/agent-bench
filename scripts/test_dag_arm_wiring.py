"""Runner-level dry run of the arm wiring in DAG.md's `run` block. No vendor
launch: `bashy` is a stub on PATH that records the argv and environment of
every call.

The block from the arm's tool lookup through the launch (`pid=$!`) is cut out
of DAG.md verbatim and run under bash with a poisoned inherited
CLAUDE_CONFIG_DIR=$REAL_HOME/.claude and a stand-in operator home
(BENCH_OPERATOR_HOME) as the seed source. It must pass the arm's isolated
CLAUDE_CONFIG_DIR to trust_preseed and run the launch with the arm env; the
real HOME's Claude config must be untouched. A static check holds every
`bashy chat` (launch, steer, session listing) in the block to the arm env.
"""
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import arm_home

REPO = Path(__file__).resolve().parent.parent
REAL_HOMES = arm_home.protected_homes()

STUB = r"""#!/bin/bash
python3 - "$@" <<'PY' >> "$BENCH_STUB_LOG"
import json, os, sys
print(json.dumps({"argv": sys.argv[1:], "env": {k: os.environ.get(k) for k in
    ("HOME", "CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME", "CODEX_HOME", "GEMINI_CLI_HOME",
     "OPENCODE_CONFIG_DIR", "OPENCODE_CONFIG", "BASHY_HOME", "BASHY_MB_DIR",
     "BASHY_SPRINT_DIR")}}))
PY
case "$*" in
  "agent show "*"--field tool") echo claude ;;
  "tool show claude --field cli.binary") echo claude ;;
  "tool show claude --field cli.launch.trust_preseed") echo .claude.json ;;
  chat\ --agent*) echo "launched (id stub-1)" ;;
esac
"""


def run_block():
    text = (REPO / "DAG.md").read_text()
    body = text.split("### run", 1)[1].split("~~~python as grade", 1)[0]
    start = body.index("  tool=$(bashy agent show")
    end = body.index("  pid=$!", start) + len("  pid=$!")
    return body, body[start:end]


def real_claude_state():
    out = {}
    for home in REAL_HOMES:
        for rel in (".claude.json", ".claude/settings.json", ".claude/.credentials.json"):
            p = os.path.join(home, rel)
            if os.path.isfile(p):
                st = os.stat(p)
                out[p] = (st.st_mtime_ns, st.st_size, stat.S_IMODE(st.st_mode))
    return out


class DagArmWiringTest(unittest.TestCase):
    def test_every_bashy_chat_runs_with_arm_env(self):
        body, _ = run_block()
        joined = re.sub(r"\\\n\s*", " ", body)  # one logical line per command
        calls = [l for l in joined.splitlines() if re.search(r"\bbashy chat\b", l)
                 and not l.lstrip().startswith("#")]
        self.assertGreaterEqual(len(calls), 4)  # sessions, launch, steer, enter
        for line in calls:
            self.assertRegex(line, r'env "\$\{armenv\[@\]\}"[^|;]*bashy chat', line)
        self.assertIn('trust_preseed.py --workspace "$ws" --home "$acd"', body)
        self.assertNotIn('--home "$ah"', body)

    def test_dry_run_preseeds_and_launches_in_arm_config_dir(self):
        _, block = run_block()
        before = real_claude_state()
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(os.path.realpath(tmp))
            op = root / "operator"
            (op / ".claude").mkdir(parents=True)
            (op / ".claude.json").write_text(json.dumps({"projects": {}}))
            (op / ".claude" / "settings.json").write_text("{}")
            (op / ".config" / "bashy").mkdir(parents=True)
            stubdir = root / "bin"
            stubdir.mkdir()
            (stubdir / "bashy").write_text(STUB)
            os.chmod(stubdir / "bashy", 0o755)
            ws = root / "ws"
            ws.mkdir()
            log = root / "stub.jsonl"
            script = "\n".join([
                "set -u", 'armdone() { [ -n "${arm:-}" ] && rm -rf "$arm"; arm=; }',
                "for i in 1; do", block, "wait $pid", 'echo "ARM=$arm"', "done"])
            env = dict(os.environ, PATH=f"{stubdir}:{os.environ['PATH']}",
                       BENCH_STUB_LOG=str(log), BENCH_OPERATOR_HOME=str(op),
                       CLAUDE_CONFIG_DIR=os.path.join(REAL_HOMES[0], ".claude"),
                       BASHY_HOME=os.path.join(REAL_HOMES[0], ".bashy"),
                       BASHY_MB_DIR=os.path.join(REAL_HOMES[0], ".bashy/mb"),
                       BASHY_SPRINT_DIR=os.path.join(REAL_HOMES[0], ".bashy/sprint"),
                       AGENT="stub-claude", TASK="t1-pivot", PACK="steer",
                       pack=str(REPO / "packs/steer/t1-pivot"), ws=str(ws),
                       rec=str(root / "rec"), ARM_ROOT=str(root), BUDGET="10")
            r = subprocess.run(["bash", "-c", script], cwd=REPO, env=env,
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            arm = re.search(r"^ARM=(.+)$", r.stdout, re.M).group(1)
            home = os.path.realpath(os.path.join(arm, arm_home.HOME_NAME))
            ccd = os.path.join(home, ".claude")
            calls = [json.loads(l) for l in log.read_text().splitlines()]
            launch = [c for c in calls if c["argv"][:2] == ["chat", "--agent"]]
            self.assertEqual(len(launch), 1)
            for c in (c for c in calls if c["argv"][:1] == ["chat"]):
                for key, value in c["env"].items():
                    if key in ("BASHY_MB_DIR", "BASHY_SPRINT_DIR"):
                        self.assertEqual(value, "", key)  # inherited real store cleared
                        continue
                    self.assertTrue(os.path.realpath(value).startswith(home + os.sep)
                                    or os.path.realpath(value) == home, (key, value))
            self.assertEqual(os.path.realpath(launch[0]["env"]["BASHY_HOME"]),
                             os.path.join(home, ".bashy"))
            self.assertEqual(os.path.realpath(launch[0]["env"]["CLAUDE_CONFIG_DIR"]), ccd)
            # The trust entry is where Claude reads it: $CLAUDE_CONFIG_DIR/.claude.json.
            data = json.loads(Path(ccd, ".claude.json").read_text())
            self.assertTrue(data["projects"][os.path.realpath(ws)]["hasTrustDialogAccepted"])
        self.assertEqual(real_claude_state(), before)

    def test_dry_run_refuses_poisoned_arm_root(self):
        # The runner's own pre-flight: an arm root inside the operator HOME stops every arm.
        r = subprocess.run([sys.executable, "scripts/arm_home.py", "check", "--path",
                            os.path.join(REAL_HOMES[0], ".claude")], cwd=REPO,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()

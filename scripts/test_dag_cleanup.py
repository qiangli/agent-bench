"""Exercise the run block with real temporary directories and a local chat stub."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[1]
STUB = """#!/usr/bin/env python3
import json, os, signal, subprocess, sys
from pathlib import Path

args = sys.argv[1:]
if args[:2] == ["agent", "show"]:
    print("stub")
elif args[:2] == ["chat", "--agent"]:
    ws = args[args.index("--cwd") + 1]
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    children = [subprocess.Popen(["sleep", "90"], cwd=path, start_new_session=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for path in (ws, os.environ["HOME"])]
    if os.environ["FAIL_EVIDENCE"] == "yes":
        # A file at the archive destination forces the real evidence copy to fail.
        (Path(os.environ["RUNS"]) / "stub/steer-t1-pivot/1.arm").touch()
    ready = Path(os.environ["READY"])
    ready.with_suffix(".tmp").write_text(json.dumps([p.pid for p in children]))
    ready.with_suffix(".tmp").rename(ready)
    print("launched (id stub-1)", flush=True)
    signal.pause()
"""


class DagCleanupTest(unittest.TestCase):
    def exercise(self, interrupt, fail_evidence=False):
        body = (REPO / "DAG.md").read_text().split("### run\n", 1)[1]
        shell, grade = body.split("```bsh\n", 1)[1].split("~~~python as grade\n", 1)
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp)
            ready = root / "ready"
            stub = root / "bashy"
            stub.write_text(STUB)
            stub.chmod(0o755)
            # Supply the two embedded Python functions normally bound by the DAG.
            (root / "grade.py").write_text(grade.split("~~~", 1)[0] +
                "\nimport sys\nsys.exit(globals()[sys.argv[1]](*sys.argv[2:]))\n")
            bridge = '\n'.join(f'grade.{fn}() {{ python3 "$GRADE" {fn} "$@"; }}'
                               for fn in ("record", "find"))
            (root / "operator").mkdir()
            env = dict(PATH=f"{root}:{os.environ['PATH']}", HOME=str(root / "operator"),
                       BENCH_OPERATOR_HOME=str(root / "operator"), TMPDIR=tmp,
                       BENCH_ARM_ROOT=tmp, AGENT="stub", PACK="steer", TASK="t1-pivot",
                       RUNS=str(root / "results"), K="1", BUDGET="1",
                       READY=str(ready), FAIL_EVIDENCE="yes" if fail_evidence else "no",
                       GRADE=str(root / "grade.py"))
            proc = subprocess.Popen(["bash", "-c", bridge + "\n" + shell], cwd=REPO,
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True)
            try:
                deadline = time.monotonic() + 15
                while not ready.exists() and proc.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.05)
                if interrupt and ready.exists():
                    proc.terminate()
                log, _ = proc.communicate(timeout=45)
                self.assertTrue(ready.exists(), log)
                self.assertEqual(proc.returncode, 143 if interrupt else 0, log)
                for pid in json.loads(ready.read_text()):
                    with self.assertRaises(ProcessLookupError, msg=log):
                        os.kill(pid, 0)
                rec = root / "results/stub/steer-t1-pivot/1"
                leftovers = list(root.glob("bench-*"))
                if fail_evidence:
                    self.assertEqual(len(leftovers), 1, log)
                    arm = leftovers[0]
                    self.assertTrue(arm.name.startswith("bench-arm."))
                    self.assertTrue((arm / "arm.json").exists(), log)
                    self.assertIn("ARM EVIDENCE COPY FAILED: kept " + str(arm), log)
                    self.assertIn("LEFT BEHIND " + str(arm), log)
                else:
                    self.assertEqual(leftovers, [], log)
                    self.assertTrue(rec.with_suffix(".arm").joinpath("arm.json").exists(), log)
                    self.assertNotIn("LEFT BEHIND", log)
                if not interrupt:
                    self.assertTrue((rec / "TASK.md").exists(), log)
                    row = json.loads((root / "results/results.jsonl").read_text())
                    self.assertEqual(row["ended"], "budget", log)
            finally:
                proc.kill()
                proc.communicate()
                if ready.exists():
                    for pid in json.loads(ready.read_text()):
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    def test_completed(self):
        self.exercise(False)

    def test_failed_copy_keeps_only_arm(self):
        self.exercise(False, fail_evidence=True)

    def test_interrupted(self):
        self.exercise(True)

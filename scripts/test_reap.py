"""Local process cleanup, including detached sessions and path boundaries."""
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

REAPER = Path(__file__).with_name("reap.py")


class ReapTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "bench-ws.abc"
        self.root.mkdir()
        self.sibling = self.root.with_name("bench-ws.abcd")
        self.sibling.mkdir()

    def start(self, cwd, setup="", args=(), **kwargs):
        code = "import signal,time;" + setup + "print('ready',flush=True);time.sleep(120)"
        proc = subprocess.Popen([sys.executable, "-c", code, *args], cwd=cwd,
                                start_new_session=True, stdout=subprocess.PIPE, **kwargs)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.wait, 5)
        self.addCleanup(proc.kill)
        self.assertEqual(proc.stdout.readline(), b"ready\n")
        return proc

    def reap(self):
        r = subprocess.run([sys.executable, REAPER, self.root], capture_output=True,
                           text=True, timeout=40)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_detached_paths(self):
        a = self.start(self.root.resolve())
        with (self.root / "open file").open("w") as f:
            b = self.start(self.sibling, pass_fds=(f.fileno(),))
        c = self.start(self.sibling, args=[str(self.root / "arg only")])
        d = self.start(self.sibling, args=[str(self.sibling), str(self.root) + " copy"])
        log = self.reap()
        for proc in (a, b, c):
            self.assertEqual(proc.wait(1), -signal.SIGTERM)
            self.assertIn(f"stopped {proc.pid} ", log)
        self.assertIsNone(d.poll())

    def test_escalates_to_kill(self):
        proc = self.start(self.root, "signal.signal(signal.SIGTERM,signal.SIG_IGN);")
        self.reap()
        self.assertEqual(proc.wait(1), -signal.SIGKILL)

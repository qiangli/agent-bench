"""Tests for scripts/real_home_canary.py. No vendor launch.

The pure helpers (attribution, log parsing, sandbox profile, poisoned env)
always run. The real-binary canary runs only when BENCH_CANARY_BASHY names the
candidate bashy (e.g. /tmp/s446-candidate-bin/bashy) on a macOS host with
sandbox-exec; it launches the zero-model benchbot-dry agent only.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import arm_home
import real_home_canary as canary

BASHY = os.environ.get("BENCH_CANARY_BASHY", "")
LIVE = bool(BASHY) and sys.platform == "darwin" and shutil.which("sandbox-exec")


class Helpers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def lock(self, path, pid, name="room-emit"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump({"name": name, "pid": pid}, fh)
        return path

    def test_poisoned_env_points_every_key_into_real_home(self):
        env = canary.poisoned_env({}, "/real")
        for key in canary.POISON_KEYS:
            self.assertTrue(env[key] == "/real" or env[key].startswith("/real/"), key)
        self.assertIn("CLAUDE_CONFIG_DIR", env)
        self.assertIn("BASHY_HOME", env)
        for key in ("BASHY_ACTIVITY_DIR", "BASHY_FLEET_DIR"):
            self.assertEqual(env[key], os.path.join("/real", ".bashy", key[6:-4].lower()))

    def test_arm_overlay_clears_every_poisoned_bashy_dir(self):
        """The poisoned per-store BASHY_*_DIR keys must not survive the overlay
        built the way the canary (and DAG.md) builds it."""
        real = os.path.join(self.tmp, "real")
        os.makedirs(real)
        base = canary.poisoned_env({"HOME": real}, real)
        armenv = arm_home.prepare(os.path.join(self.tmp, "arm"), "benchbot",
                                  source_home=real, protected=[real])
        cleared = arm_home.clear_inherited(base, armenv)
        for key in ("BASHY_MB_DIR", "BASHY_SPRINT_DIR", "BASHY_ACTIVITY_DIR", "BASHY_FLEET_DIR"):
            self.assertEqual(cleared.get(key), "", key)
        env = arm_home.arm_environ(base, armenv, [real])
        for key in ("BASHY_MB_DIR", "BASHY_SPRINT_DIR", "BASHY_ACTIVITY_DIR", "BASHY_FLEET_DIR"):
            self.assertEqual(env.get(key), "", key)

    def test_profile_denies_writes_to_every_home_with_kill(self):
        sb = canary.profile(["/a", "/b c"])
        self.assertIn('(subpath "/a")', sb)
        self.assertIn('(subpath "/b c")', sb)
        self.assertIn("(deny file-write*", sb)
        self.assertIn("SIGKILL", sb)

    def test_denials_keep_only_tree_writes_into_real_home(self):
        log = "\n".join([
            "x E sandboxd[1:2] [com.apple.sandbox.reporting:violation] Sandbox: bashy(9) deny(1) file-write-mode /real/.bashy/inbox",
            "x E sandboxd[1:2] [com.apple.sandbox.reporting:violation] Sandbox: Safari(9) deny(1) file-write-create /real/x",
            "x E sandboxd[1:2] [com.apple.sandbox.reporting:violation] Sandbox: bashy(9) deny(1) file-write-create /tmp/x",
            "x E sandboxd[1:2] [com.apple.sandbox.reporting:violation] Sandbox: python3(9) deny(1) file-read-data /real/y",
        ])
        hits = canary.denials(log, ["/real"])
        self.assertEqual(len(hits), 1)
        self.assertIn("/real/.bashy/inbox", hits[0])

    def test_fingerprint_diff_sees_content_and_absence(self):
        home = os.path.join(self.tmp, "h")
        os.makedirs(os.path.join(home, ".claude"))
        Path(home, ".claude.json").write_text("{}")
        before = canary.fingerprint([home])
        self.assertEqual(before[os.path.join(home, ".bashy/todo")], ["absent"])
        self.assertEqual(canary.diff(before, canary.fingerprint([home])), [])
        Path(home, ".claude.json").write_text('{"x": 1}')
        os.makedirs(os.path.join(home, ".bashy/todo"))
        changed = canary.diff(before, canary.fingerprint([home]))
        self.assertEqual(changed, sorted([os.path.join(home, ".claude.json"),
                                          os.path.join(home, ".bashy/todo")]))

    def test_lock_held_outside_tree_is_host(self):
        p = self.lock(os.path.join(self.tmp, "room/.timeline.lock"), 4242)
        out = canary.attribute([p], 0, {1, 2})
        self.assertEqual(out["canary"], [])
        self.assertEqual(out["host"][0]["holders"], ["room-emit:4242"])

    def test_lock_held_by_canary_tree_fails(self):
        p = self.lock(os.path.join(self.tmp, "room/.timeline.lock"), 7)
        self.assertEqual(canary.attribute([p], 0, {7})["canary"], [p])

    def test_unexplained_change_fails_closed(self):
        d = os.path.join(self.tmp, "sessions")
        os.makedirs(d)
        f = os.path.join(self.tmp, "probecache.json")
        Path(f).write_text("{}")
        bad = self.lock(os.path.join(self.tmp, "x.lock"), 1)
        Path(bad).write_text("not json")
        out = canary.attribute([d, f, bad], 0, set())
        self.assertEqual(sorted(out["canary"]), sorted([d, f, bad]))

    def test_dir_change_needs_every_fresh_lock_outside_tree(self):
        d = os.path.join(self.tmp, "sprint")
        self.lock(os.path.join(d, "queue.lock"), 99, "weave-queue")
        self.assertEqual(canary.attribute([d], 0, {1})["host"][0]["path"], d)
        self.lock(os.path.join(d, "other.lock"), 5)
        self.assertEqual(canary.attribute([d], 0, {5})["canary"], [d])
        # Locks not touched since the canary started do not explain anything.
        self.assertEqual(canary.attribute([d], time.time_ns() + 10**12, set())["canary"], [d])

    def test_claude_file_needs_live_operator_claude_and_no_canary_mention(self):
        p = os.path.join(self.tmp, ".claude.json")
        Path(p).write_text('{"projects": {}}')
        self.assertEqual(canary.attribute([p], 0, set(), "/tmp/canary.x", [])["canary"], [p])
        self.assertEqual(canary.attribute([p], 0, set(), "/tmp/canary.x", [55])["host"][0]["holders"],
                         ["claude:55"])
        Path(p).write_text('{"projects": {"/tmp/canary.x/ws": {}}}')
        self.assertEqual(canary.attribute([p], 0, set(), "/tmp/canary.x", [55])["canary"], [p])

    def test_main_refuses_without_bashy(self):
        if sys.platform != "darwin" or not shutil.which("sandbox-exec"):
            self.skipTest("no sandbox-exec")
        self.assertEqual(canary.main(["--bashy", os.path.join(self.tmp, "missing")]), 2)


@unittest.skipUnless(LIVE, "set BENCH_CANARY_BASHY=<candidate bashy> on macOS to run the real-binary canary")
class RealBinary(unittest.TestCase):
    def test_guard_kills_bashy_under_unredirected_poison(self):
        """Negative control: the very commands the canary passes with the arm
        overlay (`bashy -c`, `todo list`) write into the real HOME's bashy store
        under the bare poisoned env, and the guard kills them. Nothing is
        written (the write is denied before it happens)."""
        homes = arm_home.protected_homes()
        root = tempfile.mkdtemp(prefix="canary-neg.", dir="/tmp")
        self.addCleanup(shutil.rmtree, root, True)
        sb = os.path.join(root, "p.sb")
        Path(sb).write_text(canary.profile(homes))
        env = canary.poisoned_env(dict(os.environ), homes[0])
        for argv in ([BASHY, "-c", "echo canary"], [BASHY, "todo", "list"]):
            r = subprocess.run(["sandbox-exec", "-f", sb, *argv], env=env, cwd=root,
                               capture_output=True, timeout=120)
            self.assertIn(r.returncode, canary.KILLED, (argv, r.stderr[-300:]))

    def test_candidate_binary_leaves_real_home_unchanged(self):
        report = canary.run(os.path.abspath(BASHY))
        self.assertEqual(report["verdict"], "PASS", json.dumps(report, indent=1)[-3000:])
        self.assertEqual(report["real_home_changed"], [])
        self.assertEqual(report["sandbox_denials"], [])
        for key in ("CLAUDE_CONFIG_DIR", "BASHY_HOME", "CODEX_HOME", "XDG_CONFIG_HOME"):
            self.assertTrue(report["arm_env"][key].startswith(os.path.dirname(report["arm_home"])), key)
        for key in ("BASHY_MB_DIR", "BASHY_SPRINT_DIR", "BASHY_ACTIVITY_DIR", "BASHY_FLEET_DIR"):
            self.assertEqual(report["arm_env"][key], "")
        self.assertIn("benchbot: steer received", report["benchbot_commits"])


if __name__ == "__main__":
    unittest.main()

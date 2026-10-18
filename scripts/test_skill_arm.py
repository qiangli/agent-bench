"""Selector tests for scripts/skill_arm.py in a temp workspace under a temp arm
HOME. Calls `bashy skill export` (local, no model, no vendor launch); skipped
when bashy is not on PATH.

The arm HOME is seeded exactly as the runner seeds it: a read-only copy of
the operator's bashy config (tool definitions decide what an export writes;
an empty HOME falls back to built-ins and changes the result), under a write
guard over the operator HOME.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import arm_home
import skill_arm
from write_guard import forbid_writes

HAVE_BASHY = shutil.which("bashy") is not None


class SkillArmTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        with forbid_writes(arm_home.protected_homes()) as hits:
            self.env = arm_home.prepare(str(root / "arm"), "agy")
        self.assertEqual(hits, [])
        self.ws = root / "ws"
        self.ws.mkdir()
        (self.ws / "TASK.md").write_text("task\n")
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git(*skill_arm.BENCH_GIT, "commit", "-qm", "fixture")
        patcher = mock.patch.dict(os.environ, self.env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.ws), *args], check=True, text=True,
                              capture_output=True).stdout

    def commits(self):
        return self.git("log", "--format=%s").split()

    def test_off_exports_nothing(self):
        self.assertEqual(skill_arm.select(str(self.ws), "agy", "off"), [])
        self.assertEqual(self.commits(), ["fixture"])

    def test_script_sets_env_marker_and_exports_nothing(self):
        self.assertEqual(skill_arm.select(str(self.ws), "agy", "script"), ["BASHY_HELP_FORMAT=script"])
        self.assertEqual(self.commits(), ["fixture"])
        self.assertFalse((self.ws / ".agents").exists())

    def test_unknown_arm_fails_loudly(self):
        with self.assertRaises(skill_arm.ArmError):
            skill_arm.select(str(self.ws), "agy", "prose")
        self.assertEqual(skill_arm.main(["--workspace", str(self.ws), "--tool", "agy", "--arm", ""]), 1)

    @unittest.skipUnless(HAVE_BASHY, "bashy not on PATH")
    def test_on_exports_prose_skill_under_arm_home(self):
        self.assertEqual(skill_arm.select(str(self.ws), "agy", "on"), [])
        self.assertEqual(self.commits(), ["skill", "fixture"])
        self.assertTrue((self.ws / ".agents" / "skills" / "bashy").is_dir())
        # bashy kept its own state in the arm HOME, not the operator's.
        self.assertTrue((Path(self.env["HOME"]) / ".bashy").is_dir())

    @unittest.skipUnless(HAVE_BASHY, "bashy not on PATH")
    def test_yaml_exports_single_record(self):
        self.assertEqual(skill_arm.select(str(self.ws), "agy", "yaml"), [])
        self.assertEqual(self.commits(), ["skill-yaml", "fixture"])
        self.assertTrue(list((self.ws / ".agents" / "skills").rglob("bashy.yaml")))

    @unittest.skipUnless(HAVE_BASHY, "bashy not on PATH")
    def test_tool_without_integration_fails_not_mislabelled(self):
        with self.assertRaises(skill_arm.ArmError) as ctx:
            skill_arm.select(str(self.ws), "codex", "on")
        # Either bashy refuses (rc=1, "declares no integration") or it exits 0
        # having written nothing; both must fail rather than label skill-on.
        self.assertRegex(str(ctx.exception), "declares no integration|wrote nothing")
        self.assertEqual(self.commits(), ["fixture"])


if __name__ == "__main__":
    unittest.main()

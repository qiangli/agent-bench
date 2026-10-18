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

    def test_script_delivers_recipe_without_prose_export(self):
        self.assertEqual(skill_arm.select(str(self.ws), "agy", "script", task="t6-pdf-fact"), ["BASHY_HELP_FORMAT=script"])
        self.assertEqual(self.commits(), ["skill-script", "fixture"])
        self.assertFalse((self.ws / ".agents").exists())
        self.assertIn("bashy lens -t md invoice.pdf", (self.ws / "AGENTS.md").read_text())
        self.assertNotIn("2026-11-14", (self.ws / "AGENTS.md").read_text())

    def test_script_refuses_unknown_task_and_existing_instructions(self):
        with self.assertRaisesRegex(skill_arm.ArmError, "no script recipe"):
            skill_arm.select(str(self.ws), "agy", "script", task="t7-json-yaml")
        (self.ws / "AGENTS.md").write_text("keep me\n")
        with self.assertRaisesRegex(skill_arm.ArmError, "overwrite"):
            skill_arm.select(str(self.ws), "agy", "script", task="t6-pdf-fact")
        self.assertEqual((self.ws / "AGENTS.md").read_text(), "keep me\n")

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
    def test_ycode_on_exports_prose_and_instructions(self):
        self.assertEqual(skill_arm.select(str(self.ws), "ycode", "on"), [])
        self.assertTrue((self.ws / ".agents" / "skills" / "bashy" / "SKILL.md").is_file())
        self.assertIn("bashy:skill:bashy:begin", (self.ws / "AGENTS.md").read_text())

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

    @unittest.skipUnless(HAVE_BASHY, "bashy not on PATH")
    def test_claude_on_exports_project_skill_claude_reads(self):
        # bashy's claude tool has no integration block; the on arm still lands
        # the skill where Claude reads project skills, inside the workspace only.
        self.assertEqual(skill_arm.select(str(self.ws), "claude", "on"), [])
        self.assertEqual(self.commits(), ["skill", "fixture"])
        skill = self.ws / ".claude" / "skills" / "bashy" / "SKILL.md"
        self.assertTrue(skill.is_file())
        self.assertTrue(skill.read_text().startswith("---\nname: bashy\n"))
        self.assertIn(".claude/skills/bashy/SKILL.md", self.git("ls-files"))


if __name__ == "__main__":
    unittest.main()

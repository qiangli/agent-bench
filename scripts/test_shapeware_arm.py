"""Unit tests for scripts/shapeware_arm.py. No network, no live agents."""
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import shapeware_arm


class ShapewareArmTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.arm_dir = self.root / "arm"
        self.arm_dir.mkdir()
        self.fake_bins = {}
        for arm in ("A", "B", "C"):
            p = self.root / f"bashy-{arm}"
            p.write_text("#!/bin/sh\necho fake-" + arm + "\n", encoding="utf-8")
            p.chmod(0o755)
            self.fake_bins[arm] = str(p)

    def tearDown(self):
        self.tmp.cleanup()

    def test_select_each_arm_with_explicit_binary(self):
        for arm in ("A", "B", "C"):
            with self.subTest(arm=arm):
                lines = shapeware_arm.select(
                    str(self.arm_dir),
                    arm,
                    bashy_bin=self.fake_bins[arm],
                    env={"PATH": "/usr/bin:/bin"},
                )
                kv = dict(line.split("=", 1) for line in lines)
                self.assertEqual(kv["BENCH_ARM"], arm)
                self.assertEqual(kv["BENCH_BASHY_BIN"], os.path.realpath(self.fake_bins[arm]))
                arm_bin = os.path.join(os.path.realpath(str(self.arm_dir)), "arm-bin")
                self.assertTrue(kv["PATH"].startswith(arm_bin + os.pathsep))
                self.assertEqual(
                    os.path.realpath(os.path.join(arm_bin, "bashy")),
                    os.path.realpath(self.fake_bins[arm]),
                )

    def test_select_uses_per_arm_env_var(self):
        env = {"PATH": "/usr/bin:/bin", "BASHY_BIN_B": self.fake_bins["B"]}
        lines = shapeware_arm.select(str(self.arm_dir), "B", env=env)
        kv = dict(line.split("=", 1) for line in lines)
        self.assertEqual(kv["BENCH_ARM"], "B")
        self.assertEqual(kv["BENCH_BASHY_BIN"], os.path.realpath(self.fake_bins["B"]))

    def test_rejects_unknown_arm(self):
        with self.assertRaisesRegex(shapeware_arm.ArmError, "unknown shapeware arm"):
            shapeware_arm.select(str(self.arm_dir), "D", bashy_bin=self.fake_bins["A"])

    def test_rejects_missing_or_non_executable_binary(self):
        with self.assertRaisesRegex(shapeware_arm.ArmError, "no bashy binary supplied"):
            shapeware_arm.select(str(self.arm_dir), "A", env={"PATH": "/usr/bin"})
        missing = str(self.root / "does-not-exist")
        with self.assertRaisesRegex(shapeware_arm.ArmError, "does not exist"):
            shapeware_arm.select(str(self.arm_dir), "A", bashy_bin=missing)
        nonexec = self.root / "not-exec"
        nonexec.write_text("#!/bin/sh\n", encoding="utf-8")
        nonexec.chmod(stat.S_IRUSR | stat.S_IWUSR)
        with self.assertRaisesRegex(shapeware_arm.ArmError, "not executable"):
            shapeware_arm.select(str(self.arm_dir), "A", bashy_bin=str(nonexec))

    def test_main_nonzero_on_error(self):
        rc = shapeware_arm.main(["--arm-dir", str(self.arm_dir), "--arm", "Z"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()

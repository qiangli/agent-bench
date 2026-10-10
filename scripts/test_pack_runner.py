"""Regression checks for pack task discovery. Run with unittest, no network."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import pack_runner


class TaskDiscoveryTest(unittest.TestCase):
    def test_existing_pack_layouts(self):
        expected_counts = {
            "floor": 4,
            "l1": 20,
            "l2": 20,
            "steer": 10,
            "review": 20,
            "manager": 10,
            "judge": 1,
            "l5": 6,
            "skill-uptake": 5,
        }
        for pack, count in expected_counts.items():
            with self.subTest(pack=pack):
                self.assertEqual(len(pack_runner.task_dirs(pack)), count)

        steer = pack_runner.task_dirs("steer")
        self.assertTrue(all(not (task / "task.yaml").exists() for task in steer))
        self.assertTrue(all((task / "grader" / "grade.py").is_file() for task in steer))
        self.assertEqual(pack_runner.task_dirs("judge"), [pack_runner.PACKS / "judge"])

    def test_empty_pack_is_an_error_for_validate_and_verdict(self):
        with tempfile.TemporaryDirectory() as temp:
            packs = Path(temp)
            (packs / "empty").mkdir()
            output = io.StringIO()
            with mock.patch.object(pack_runner, "PACKS", packs), contextlib.redirect_stdout(output):
                self.assertEqual(pack_runner.validate("empty"), 2)
                self.assertEqual(pack_runner.verdict(packs / "rows.jsonl", "empty", "agent", 3), 2)
            self.assertEqual(output.getvalue().splitlines(), [
                "ERROR empty: no task directories found",
                "ERROR empty: no task directories found",
            ])


if __name__ == "__main__":
    unittest.main()

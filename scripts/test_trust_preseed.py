"""Unit tests for scripts/trust_preseed.py. Run with unittest, no network.

Every test points the helper at a temporary HOME, so the real user config
is never touched; test_real_home_refused proves the real HOME is refused
before anything is opened.
"""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import trust_preseed
from arm_home import protected_homes
from write_guard import forbid_writes


class TrustPreseedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.ws = Path(self.tmp.name) / "ws"
        self.ws.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def config(self):
        return json.loads((self.home / ".claude.json").read_text(encoding="utf-8"))

    def test_absent_file_creates_minimal_entry(self):
        ws = trust_preseed.preseed(str(self.ws), str(self.home))
        self.assertEqual(ws, os.path.realpath(str(self.ws)))
        data = self.config()
        self.assertTrue(data["projects"][ws]["hasTrustDialogAccepted"])
        mode = stat.S_IMODE(os.stat(self.home / ".claude.json").st_mode)
        self.assertEqual(mode, 0o600)

    def test_existing_config_preserved(self):
        cfg = {
            "theme": "dark",
            "projects": {
                "/other/dir": {"hasTrustDialogAccepted": True, "extra": 1},
                os.path.realpath(str(self.ws)): {"mru": ["a"]},
            },
        }
        (self.home / ".claude.json").write_text(json.dumps(cfg), encoding="utf-8")
        ws = trust_preseed.preseed(str(self.ws), str(self.home))
        data = self.config()
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["projects"]["/other/dir"], {"hasTrustDialogAccepted": True, "extra": 1})
        # The workspace entry keeps its own fields and gains the trust flag.
        self.assertEqual(data["projects"][ws], {"mru": ["a"], "hasTrustDialogAccepted": True})

    def test_invalid_file_backed_up_not_lost(self):
        bad = self.home / ".claude.json"
        bad.write_text("{not json", encoding="utf-8")
        ws = trust_preseed.preseed(str(self.ws), str(self.home))
        backups = list(self.home.glob(".claude.json.bench-bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "{not json")
        self.assertTrue(self.config()["projects"][ws]["hasTrustDialogAccepted"])

    def test_permission_bits_preserved(self):
        cfg = self.home / ".claude.json"
        cfg.write_text("{}", encoding="utf-8")
        os.chmod(cfg, 0o640)
        trust_preseed.preseed(str(self.ws), str(self.home))
        self.assertEqual(stat.S_IMODE(os.stat(cfg).st_mode), 0o640)

    def test_missing_workspace_is_an_error(self):
        with self.assertRaises(ValueError):
            trust_preseed.preseed(str(self.ws / "nope"), str(self.home))
        self.assertFalse((self.home / ".claude.json").exists())

    def test_home_is_required(self):
        with self.assertRaises(SystemExit):
            trust_preseed.main(["--workspace", str(self.ws)])
        with self.assertRaises(ValueError):
            trust_preseed.preseed(str(self.ws), "")

    def test_operator_home_refused(self):
        # The temp "home" stands in for an operator HOME: nothing is written.
        with self.assertRaises(trust_preseed.UnsafeTarget):
            trust_preseed.preseed(str(self.ws), str(self.home), protected=[str(self.home)])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_symlinked_config_into_operator_home_refused(self):
        operator = Path(self.tmp.name) / "operator"
        operator.mkdir()
        (operator / ".claude.json").write_text("{}", encoding="utf-8")
        (self.home / ".claude.json").symlink_to(operator / ".claude.json")
        with self.assertRaises(trust_preseed.UnsafeTarget):
            trust_preseed.preseed(str(self.ws), str(self.home), protected=[str(operator)])
        self.assertEqual((operator / ".claude.json").read_text(encoding="utf-8"), "{}")

    def test_real_home_refused(self):
        real = protected_homes()
        with forbid_writes(real) as hits:
            for home in real:
                rc = trust_preseed.main(["--workspace", str(self.ws), "--home", home])
                self.assertEqual(rc, 1)
        self.assertEqual(hits, [])

    def test_idempotent_second_run(self):
        trust_preseed.preseed(str(self.ws), str(self.home))
        first = self.config()
        trust_preseed.preseed(str(self.ws), str(self.home))
        self.assertEqual(self.config(), first)


class AgyTrustPreseedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.ws = Path(self.tmp.name) / "ws"
        self.ws.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def settings_path(self) -> Path:
        return self.home / ".gemini" / "antigravity-cli" / "settings.json"

    def settings(self) -> dict:
        return json.loads(self.settings_path().read_text(encoding="utf-8"))

    def test_absent_file_creates_minimal_0600_settings(self):
        alias = Path(self.tmp.name) / "ws-link"
        alias.symlink_to(self.ws)
        rc = trust_preseed.main(["--tool", "agy", "--workspace", str(alias), "--home", str(self.home)])
        self.assertEqual(rc, 0)
        self.assertEqual(self.settings(), {"trustedWorkspaces": [os.path.realpath(str(self.ws))]})
        self.assertEqual(stat.S_IMODE(os.stat(self.settings_path()).st_mode), 0o600)

    def test_existing_settings_preserved_and_idempotent(self):
        path = self.settings_path()
        path.parent.mkdir(parents=True)
        cfg = {"colorScheme": "dark", "trustedWorkspaces": ["/other/ws"]}
        path.write_text(json.dumps(cfg), encoding="utf-8")
        os.chmod(path, 0o640)
        ws = trust_preseed.preseed(str(self.ws), str(self.home), tool="agy")
        trust_preseed.preseed(str(self.ws), str(self.home), tool="agy")
        self.assertEqual(self.settings(), {
            "colorScheme": "dark",
            "trustedWorkspaces": ["/other/ws", ws],
        })
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o640)

    def test_invalid_file_backed_up_not_lost(self):
        path = self.settings_path()
        path.parent.mkdir(parents=True)
        path.write_text("{corrupt", encoding="utf-8")
        ws = trust_preseed.preseed(str(self.ws), str(self.home), tool="agy")
        backups = list(path.parent.glob("settings.json.bench-bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "{corrupt")
        self.assertEqual(self.settings(), {"trustedWorkspaces": [ws]})

    def test_operator_home_and_symlinks_into_it_refused(self):
        operator = Path(self.tmp.name) / "operator"
        (operator / ".gemini" / "antigravity-cli").mkdir(parents=True)
        op_settings = operator / ".gemini" / "antigravity-cli" / "settings.json"
        op_settings.write_text("{}", encoding="utf-8")
        protected = protected_homes() + [str(operator)]
        with forbid_writes(protected) as hits:
            with self.assertRaises(trust_preseed.UnsafeTarget):
                trust_preseed.preseed(str(self.ws), str(operator), protected=protected, tool="agy")
            for real in protected_homes():
                self.assertEqual(trust_preseed.main(
                    ["--tool", "agy", "--workspace", str(self.ws), "--home", real]), 1)
        self.assertEqual(hits, [])
        # Symlinked .gemini directory into operator HOME refused.
        (self.home / ".gemini").symlink_to(operator / ".gemini")
        with forbid_writes(protected) as hits:
            with self.assertRaises(trust_preseed.UnsafeTarget):
                trust_preseed.preseed(str(self.ws), str(self.home), protected=protected, tool="agy")
        self.assertEqual(hits, [])
        (self.home / ".gemini").unlink()
        # Symlinked settings.json into operator HOME refused.
        (self.home / ".gemini" / "antigravity-cli").mkdir(parents=True)
        self.settings_path().symlink_to(op_settings)
        with forbid_writes(protected) as hits:
            with self.assertRaises(trust_preseed.UnsafeTarget):
                trust_preseed.preseed(str(self.ws), str(self.home), protected=protected, tool="agy")
        self.assertEqual(hits, [])
        self.assertEqual(op_settings.read_text(encoding="utf-8"), "{}")


if __name__ == "__main__":
    unittest.main()

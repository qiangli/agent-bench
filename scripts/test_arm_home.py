"""Unit tests for scripts/arm_home.py (per-arm HOME isolation). No network,
no vendor launch.

Every test runs under write_guard.forbid_writes over the REAL operator HOME
(passwd home and $HOME) plus the fake operator home it seeds from: any write
that resolves there is blocked and fails the test.
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import arm_home
import trust_preseed
from write_guard import forbid_writes

REAL_HOMES = arm_home.protected_homes()


class ArmHomeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        # A fake operator home with real-looking vendor config.
        self.op = root / "operator"
        (self.op / ".claude").mkdir(parents=True)
        (self.op / ".claude.json").write_text(json.dumps({"projects": {"/x": {"hasTrustDialogAccepted": True}}}))
        os.chmod(self.op / ".claude.json", 0o600)
        (self.op / ".claude" / "settings.json").write_text('{"theme": "dark"}')
        (self.op / ".claude" / "history.jsonl").write_text("private history\n")
        (self.op / ".config" / "bashy" / "agents").mkdir(parents=True)
        (self.op / ".config" / "bashy" / "agents" / "a.yaml").write_text("name: a\n")
        (self.op / ".config" / "bashy" / "skills" / "big").mkdir(parents=True)
        (self.op / ".config" / "bashy" / "skills" / "big" / "SKILL.md").write_text("x")
        (self.op / ".config" / "bashy" / "linked.yaml").symlink_to(self.op / ".claude" / "settings.json")
        self.arm = root / "arm"
        self.ws = root / "ws"
        self.ws.mkdir()
        self.protected = REAL_HOMES + [str(self.op)]
        self.snapshot = self._snap()

    def tearDown(self):
        # The operator files are byte-identical after every test.
        self.assertEqual(self._snap(), self.snapshot)
        self.tmp.cleanup()

    def _snap(self):
        out = {}
        for p in sorted(self.op.rglob("*")):
            if p.is_file() and not p.is_symlink():
                out[str(p)] = (p.read_bytes(), stat.S_IMODE(p.stat().st_mode))
        return out

    def prepare(self, tool="claude", **kw):
        return arm_home.prepare(str(self.arm), tool, source_home=str(self.op),
                                protected=self.protected, **kw)

    def test_real_config_never_opened_for_writing(self):
        # The full arm lifecycle — seed, trust preseed, evidence — under a guard
        # over the real operator HOME and the seed source.
        rec = Path(self.tmp.name) / "runs" / "rec.arm"
        with forbid_writes(self.protected) as hits:
            env = self.prepare(binary="$HOME/.bashy/tools/claude/1/claude")
            trust_preseed.preseed(str(self.ws), env["HOME"], protected=self.protected)
            arm_home.evidence(str(self.arm), str(rec), protected=self.protected)
        self.assertEqual(hits, [])

    def test_guard_catches_a_real_config_write(self):
        # The guard itself must go red, or the test above proves nothing.
        with forbid_writes(self.protected) as hits:
            with self.assertRaises(PermissionError):
                open(self.op / ".claude.json", "w")
            with self.assertRaises(PermissionError):
                trust_preseed.preseed(str(self.ws), str(self.op), protected=[])
        self.assertEqual(len(hits), 2)

    def test_poisoned_claude_config_dir_is_redirected(self):
        # Operator exported CLAUDE_CONFIG_DIR (and friends) into the real HOME.
        for real in REAL_HOMES + [str(self.op)]:
            poisoned = {"CLAUDE_CONFIG_DIR": os.path.join(real, ".claude"),
                        "CODEX_HOME": os.path.join(real, ".codex"),
                        "GEMINI_CLI_HOME": real,
                        "OPENCODE_CONFIG_DIR": os.path.join(real, ".config/opencode"),
                        "OPENCODE_CONFIG": os.path.join(real, ".config/opencode/x.json"),
                        "HOME": real, "XDG_CONFIG_HOME": os.path.join(real, ".config"),
                        "GOCACHE": os.path.join(real, ".bashy/weave/agent-data/go-build-cache"),
                        "BASHY_HOME": os.path.join(real, ".bashy"),
                        "BASHY_MB_DIR": os.path.join(real, ".bashy/mb"),
                        "BASHY_SPRINT_DIR": os.path.join(real, ".bashy/sprint"),
                        "BASHY_ROOT": real,
                        "BASHY_TOOL_BINARY_CLAUDE": "/usr/bin/true",
                        "PATH": "/usr/bin"}
            with forbid_writes(self.protected) as hits:
                env = self.prepare(tool="claude")
                merged = arm_home.arm_environ(poisoned, env, protected=self.protected)
                home = os.path.realpath(self.arm / arm_home.HOME_NAME)
                for key in arm_home.GUARDED_KEYS:
                    self.assertTrue(merged[key] == home or merged[key].startswith(home + os.sep), key)
                self.assertEqual(merged["CLAUDE_CONFIG_DIR"], os.path.join(home, ".claude"))
                self.assertEqual(merged["BASHY_HOME"], os.path.join(home, ".bashy"))
                self.assertEqual(merged["GOCACHE"], os.path.join(home, ".cache", "go-build"))
                for key in ("BASHY_MB_DIR", "BASHY_SPRINT_DIR", "BASHY_ROOT"):
                    self.assertEqual(merged[key], "", key)  # cleared: bashy defaults under BASHY_HOME
                self.assertEqual(merged["BASHY_TOOL_BINARY_CLAUDE"], "/usr/bin/true")  # not a location
                # Claude reads $CLAUDE_CONFIG_DIR/.claude.json: seeded and preseedable there.
                cfg = Path(merged["CLAUDE_CONFIG_DIR"]) / ".claude.json"
                self.assertTrue(cfg.is_file())
                trust_preseed.preseed(str(self.ws), merged["CLAUDE_CONFIG_DIR"], protected=self.protected)
                self.assertIn(os.path.realpath(self.ws), json.loads(cfg.read_text())["projects"])
            self.assertEqual(hits, [])
            import shutil
            shutil.rmtree(self.arm)

    def test_go_cache_write_stays_in_isolated_home(self):
        with forbid_writes(self.protected) as hits:
            env = self.prepare(tool="ycode")
            merged = arm_home.arm_environ({"GOCACHE": os.path.join(str(self.op), "go-cache")},
                                           env, protected=self.protected)
            cache = Path(merged["GOCACHE"])
            cache.mkdir(parents=True)
            (cache / "probe").write_text("x")
        self.assertEqual(hits, [])
        self.assertEqual((cache / "probe").read_text(), "x")
        self.assertFalse((self.op / "go-cache").exists())

    def test_parent_agent_session_markers_cleared(self):
        # S10: an inherited CLAUDE_CODE_CHILD_SESSION turned off the arm's
        # transcript (no attributable usage); the messaging token is the parent's.
        parent = {"CLAUDE_CODE_CHILD_SESSION": "1", "CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "p",
                  "CLAUDE_CODE_ENTRYPOINT": "sdk-cli", "CLAUDE_CODE_MESSAGING_TOKEN": "secret",
                  "CLAUDE_CODE_MESSAGING_SOCKET": "/tmp/s", "CLAUDE_PID": "1", "CODEX_THREAD_ID": "t",
                  "CLAUDE_CODE_USE_BEDROCK": "1", "PATH": "/usr/bin"}
        env = self.prepare(tool="claude")
        merged = arm_home.arm_environ(parent, env, protected=self.protected)
        for key in parent:
            if key not in ("CLAUDE_CODE_USE_BEDROCK", "PATH"):
                self.assertEqual(merged[key], "", key)
        self.assertEqual(merged["CLAUDE_CODE_USE_BEDROCK"], "1")  # operator config, not a marker
        self.assertEqual(merged["CLAUDE_CODE_FORCE_SESSION_PERSISTENCE"], "1")
        # The CLI prints the clearing lines too, so `env "${armenv[@]}"` drops them.
        with mock.patch.dict(os.environ, parent):
            self.assertEqual(arm_home.clear_inherited(dict(os.environ), env)["CLAUDE_CODE_CHILD_SESSION"], "")

    def test_unredirected_poisoned_key_fails_closed(self):
        for real in REAL_HOMES + [str(self.op)]:
            env = self.prepare()
            env.pop("CLAUDE_CONFIG_DIR")  # a regression that drops the redirect
            with self.assertRaises(arm_home.UnsafeTarget):
                arm_home.arm_environ({"CLAUDE_CONFIG_DIR": os.path.join(real, ".claude")}, env,
                                     protected=self.protected)
            import shutil
            shutil.rmtree(self.arm)

    def test_unredirected_bashy_home_fails_closed(self):
        for real in REAL_HOMES + [str(self.op)]:
            env = self.prepare()
            env.pop("BASHY_HOME")  # a regression that drops the redirect
            with self.assertRaises(arm_home.UnsafeTarget):
                arm_home.arm_environ({"BASHY_HOME": os.path.join(real, ".bashy")}, env,
                                     protected=self.protected)
            # A stateful override the arm env sets itself into a real home also fails.
            env = dict(env, BASHY_HOME=os.path.join(self.arm, "x"),
                       BASHY_MB_DIR=os.path.join(real, ".bashy/mb"))
            with self.assertRaises(arm_home.UnsafeTarget):
                arm_home.arm_environ({}, env, protected=self.protected)
            import shutil
            shutil.rmtree(self.arm)

    def test_prepare_cli_emits_clears_for_inherited_bashy_stores(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            arm = os.path.join(os.path.realpath(tmp), "arm")
            real = REAL_HOMES[0]
            r = subprocess.run(
                [sys.executable, str(Path(__file__).parent / "arm_home.py"), "prepare",
                 "--arm-dir", arm, "--tool", "claude"],
                env=dict(os.environ, BENCH_OPERATOR_HOME=str(self.op),
                         BASHY_HOME=os.path.join(real, ".bashy"),
                         BASHY_MB_DIR=os.path.join(real, ".bashy/mb"),
                         BASHY_SPRINT_DIR=os.path.join(real, ".bashy/sprint"),
                         BASHY_OTEL_SPOOL=os.path.join(real, ".agents/otel/spool/spans.jsonl")),
                capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = r.stdout.splitlines()
            home = os.path.join(os.path.realpath(arm), arm_home.HOME_NAME)
            self.assertIn(f"BASHY_HOME={home}/.bashy", lines)
            self.assertIn("BASHY_MB_DIR=", lines)
            self.assertIn("BASHY_SPRINT_DIR=", lines)
            self.assertIn("BASHY_OTEL_SPOOL=", lines)  # telemetry spool, not a *_DIR

    def test_env_points_only_at_arm_home(self):
        env = self.prepare(tool="codex", binary="$HOME/.bashy/tools/codex/1/codex")
        home = os.path.realpath(self.arm / arm_home.HOME_NAME)
        self.assertEqual(env["HOME"], home)
        for key in arm_home.GUARDED_KEYS[1:]:
            self.assertTrue(env[key] == home or env[key].startswith(home + os.sep), key)
        # The binary is executed in place (read-only), resolved against the source home.
        self.assertEqual(env["BASHY_TOOL_BINARY_CODEX"], f"{self.op}/.bashy/tools/codex/1/codex")
        self.assertEqual(stat.S_IMODE(os.stat(self.arm).st_mode), 0o700)

    def test_seed_is_minimal_copy_without_links(self):
        env = self.prepare()
        home = Path(env["HOME"])
        self.assertEqual(json.loads((home / ".claude.json").read_text())["projects"]["/x"],
                         {"hasTrustDialogAccepted": True})
        self.assertTrue((home / ".claude" / "settings.json").is_file())
        self.assertTrue((home / ".config" / "bashy" / "agents" / "a.yaml").is_file())
        self.assertFalse((home / ".claude" / "history.jsonl").exists())
        self.assertFalse((home / ".config" / "bashy" / "skills").exists())
        linked = home / ".config" / "bashy" / "linked.yaml"
        self.assertFalse(linked.is_symlink())
        self.assertEqual(linked.read_text(), '{"theme": "dark"}')
        for p in home.rglob("*"):
            self.assertFalse(p.is_symlink(), p)
        # A write to the arm copy never reaches the operator file.
        (home / ".claude.json").write_text("{}")
        manifest = json.loads((self.arm / "arm.json").read_text())
        self.assertIn(".claude.json", manifest["seeded"])

    def test_arm_dir_in_operator_home_fails_closed(self):
        with forbid_writes(self.protected) as hits:
            with self.assertRaises(arm_home.UnsafeTarget):
                arm_home.prepare(str(self.op / "arm"), "claude", source_home=str(self.op),
                                 protected=self.protected)
        self.assertEqual(hits, [])
        self.assertFalse((self.op / "arm").exists())

    def test_arm_dir_symlinked_into_operator_home_fails_closed(self):
        (self.op / "target").mkdir()
        link = Path(self.tmp.name) / "sneaky"
        link.symlink_to(self.op / "target")
        with self.assertRaises(arm_home.UnsafeTarget):
            arm_home.prepare(str(link), "claude", source_home=str(self.op), protected=self.protected)
        self.assertEqual(list((self.op / "target").iterdir()), [])
        os.rmdir(self.op / "target")

    def test_nonempty_arm_dir_refused(self):
        self.arm.mkdir()
        (self.arm / "stale").write_text("x")
        with self.assertRaises(arm_home.UnsafeTarget):
            self.prepare()

    def test_check_cli_refuses_real_home(self):
        for home in REAL_HOMES:
            self.assertEqual(arm_home.main(["check", "--path", os.path.join(home, ".claude.json")]), 1)
        self.assertEqual(arm_home.main(["check", "--path", str(self.ws)]), 0)

    def test_evidence_keeps_sessions_not_credentials(self):
        env = self.prepare()
        home = Path(env["HOME"])
        (home / ".bashy" / "sessions" / "logs").mkdir(parents=True)
        (home / ".bashy" / "sessions" / "logs" / "abc.log").write_text("screen")
        (home / ".claude" / "projects" / "p").mkdir(parents=True)
        (home / ".claude" / "projects" / "p" / "s.jsonl").write_text("{}")
        rec = Path(self.tmp.name) / "runs" / "agent" / "pack-task" / "1.arm"
        kept = arm_home.evidence(str(self.arm), str(rec), protected=self.protected)
        self.assertEqual(kept, [".bashy/sessions", ".claude/projects"])  # no room/exec in this fake arm
        self.assertEqual((rec / ".bashy/sessions/logs/abc.log").read_text(), "screen")
        self.assertTrue((rec / "arm.json").is_file())
        self.assertFalse((rec / ".claude.json").exists())
        self.assertFalse((rec / ".config").exists())
        # The manifest names what the arm held (credentials included) but never copies content.
        (home / ".bashy" / "quota").mkdir(parents=True)
        (home / ".bashy" / "quota" / "claude.json").write_text("{}")
        (home / ".claude" / ".credentials.json").write_text("SECRET")
        rec2 = Path(self.tmp.name) / "runs" / "2.arm"
        self.assertIn(".bashy/quota", arm_home.evidence(str(self.arm), str(rec2), protected=self.protected))
        listing = (rec2 / "arm-files.txt").read_text()
        self.assertIn("6\t.claude/.credentials.json", listing)
        self.assertFalse((rec2 / ".claude" / ".credentials.json").exists())
        self.assertNotIn("SECRET", "".join(p.read_text(errors="replace") for p in rec2.rglob("*") if p.is_file()))


if __name__ == "__main__":
    unittest.main()

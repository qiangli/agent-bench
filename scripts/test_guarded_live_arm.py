"""Zero-model tests for the guarded live arm: Keychain credential seeding
(stub reader, never the real Keychain), DAG.md's BENCH_GUARD wiring, and the
wrapper's denial / usage / runner-write attribution."""
import json
import os
import re
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import arm_home
import guarded_live_arm as g

REPO = Path(__file__).resolve().parent.parent


def login(expires_in_s, now=1_000_000.0):
    return json.dumps({"claudeAiOauth": {"accessToken": "a", "refreshToken": "r",
                                         "refreshTokenExpiresAt": 1, "expiresAt": (now + expires_in_s) * 1000,
                                         "subscriptionType": "max"}})


class KeychainSeedTest(unittest.TestCase):
    def test_seed_drops_refresh_token_and_is_private(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            ccd = os.path.join(os.path.realpath(tmp), ".claude")
            label = arm_home.seed_claude_keychain(ccd, arm_home.protected_homes(), now=1_000_000.0,
                                                  read=lambda s: login(3600))
            self.assertIn("no refresh token", label)
            p = os.path.join(ccd, ".credentials.json")
            data = json.load(open(p))["claudeAiOauth"]
            self.assertEqual(data["accessToken"], "a")
            self.assertNotIn("refreshToken", data)
            self.assertNotIn("refreshTokenExpiresAt", data)
            self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)

    def test_near_expiry_refuses(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            ccd = os.path.join(os.path.realpath(tmp), ".claude")
            with self.assertRaises(arm_home.UnsafeTarget):
                arm_home.seed_claude_keychain(ccd, arm_home.protected_homes(), now=1_000_000.0,
                                              read=lambda s: login(60))
            self.assertFalse(os.path.exists(os.path.join(ccd, ".credentials.json")))

    def test_refuses_operator_home_target(self):
        home = arm_home.protected_homes()[0]
        with self.assertRaises(arm_home.UnsafeTarget):
            arm_home.seed_claude_keychain(os.path.join(home, ".claude"), arm_home.protected_homes(),
                                          now=1_000_000.0, read=lambda s: login(3600))

    def test_garbage_refuses(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            with self.assertRaises(arm_home.UnsafeTarget):
                arm_home.seed_claude_keychain(os.path.join(tmp, ".claude"), arm_home.protected_homes(),
                                              read=lambda s: "not json")


class DagGuardWiringTest(unittest.TestCase):
    def test_every_isolated_command_is_guarded(self):
        text = (REPO / "DAG.md").read_text()
        body = text.split("### run", 1)[1].split("~~~python as grade", 1)[0]
        joined = re.sub(r"\\\n\s*", " ", body)
        self.assertIn('guard=(); [ -n "${BENCH_GUARD:-}" ] && guard=(sandbox-exec -f "$BENCH_GUARD")', body)
        for m in re.finditer(r'env "\$\{(armenv|preenv)\[@\]\}"', joined):
            line_start = joined.rfind("\n", 0, m.start()) + 1
            if joined[line_start:m.start()].lstrip().startswith("#"):
                continue
            self.assertTrue(joined[:m.start()].endswith('"${guard[@]}" '), joined[line_start:m.end()])
        self.assertIn('"${guard[@]}" python3 scripts/trust_preseed.py', body)
        self.assertIn('for attempt in $(seq 1 "$ATTEMPTS")', body)
        self.assertIn('[ "$attempt" = "$ATTEMPTS" ] && exit 1', body)


class WrapperParsingTest(unittest.TestCase):
    def test_tree_denials(self):
        home = "/Users/op"
        log = "\n".join([
            "2026-10-18 Df kernel[0:1] Sandbox: claude(101) deny(1) file-write-create /Users/op/.claude.json",
            "2026-10-18 Df kernel[0:1] Sandbox: claude(101) deny(1) process-exec /usr/bin/security",
            "2026-10-18 Df kernel[0:1] Sandbox: other(999) deny(1) file-write-create /Users/op/x",
            "2026-10-18 Df kernel[0:1] Sandbox: claude(101) deny(1) file-write-create /Users/opx/y",
        ])
        writes, other = g.tree_denials(log, {101}, [home])
        self.assertEqual(len(writes), 1)
        self.assertIn(".claude.json", writes[0])
        self.assertEqual(len(other), 2)  # the exec denial, and /Users/opx is not /Users/op

    def test_usage_records_attribute_by_cwd(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            d = Path(tmp, ".claude", "projects", "p")
            d.mkdir(parents=True)
            rows = [{"type": "user", "cwd": "/w"},
                    {"type": "assistant", "cwd": "/w", "requestId": "q1", "sessionId": "s",
                     "message": {"model": "m", "usage": {"input_tokens": 3, "output_tokens": 4, "x": "y"}}},
                    {"type": "assistant", "cwd": "/elsewhere", "requestId": "q2",
                     "message": {"model": "m", "usage": {"input_tokens": 1}}}]
            (d / "s.jsonl").write_text("\n".join(map(json.dumps, rows)) + "\nnot json\n")
            recs = g.usage_records(tmp, os.path.realpath("/w"), "m")
            self.assertEqual(len(recs), 2)
            self.assertEqual([r["cwd_is_ws"] for r in recs], [True, False])
            self.assertEqual(recs[0]["usage"], {"input_tokens": 3, "output_tokens": 4})

    def test_split_runner(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            a = os.path.join(tmp, "a.lock")
            b = os.path.join(tmp, "b.lock")
            Path(a).write_text(json.dumps({"name": "room-emit", "pid": 7}))
            Path(b).write_text(json.dumps({"name": "x", "pid": 8}))
            arm, runner = g.split_runner([a, b, os.path.join(tmp, "plain")], 0, 7)
            self.assertEqual([r["path"] for r in runner], [a])
            self.assertEqual(sorted(arm), sorted([b, os.path.join(tmp, "plain")]))

    def test_quota_gate(self):
        ok = {"5h": {"status": "ok", "used_percent": 3}, "week": {"status": "ok", "used_percent": 39}}
        self.assertIsNone(g.quota_ok(ok, 80, 90))
        self.assertIn("cap", g.quota_ok(dict(ok, week={"status": "ok", "used_percent": 95}), 80, 90))
        self.assertIn("no measured 5h", g.quota_ok({"week": ok["week"]}, 80, 90))
        self.assertIn("not ok", g.quota_ok(dict(ok, **{"5h": {"status": "ok", "used_percent": 3, "stale": True}}), 80, 90))

    def test_profile_denies_homes_decoy_and_keychain_cli(self):
        p = g.guard_profile(["/Users/op"], "/private/tmp/d")
        self.assertIn('(deny file-write* (subpath "/Users/op") (subpath "/private/tmp/d") (with send-signal SIGKILL))', p)
        self.assertIn('(deny process-exec (literal "/usr/bin/security"))', p)


if __name__ == "__main__":
    unittest.main()

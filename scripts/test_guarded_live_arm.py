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
from types import SimpleNamespace
from unittest import mock

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
    def test_wrapper_ancestors_are_separate_and_vendor_escape_fails(self):
        rows = {
            10: {"pid": 10, "ppid": 1, "comm": "bashy", "sandboxed": 0},
            11: {"pid": 11, "ppid": 10, "comm": "bashy", "sandboxed": 0},
            12: {"pid": 12, "ppid": 11, "comm": "bashy", "command": "bashy chat --agent ycode-kimi-k2.6", "sandboxed": 1},
            13: {"pid": 13, "ppid": 12, "comm": "bashy", "command": "bashy ycode -m kimi-k2.6", "sandboxed": 1},
            14: {"pid": 14, "ppid": 13, "comm": "go", "sandboxed": 0},
            15: {"pid": 15, "ppid": 11, "comm": "bashy", "command": "bashy chat run", "sandboxed": 0},
            16: {"pid": 16, "ppid": 11, "comm": "bashy", "command": "bashy agent show", "sandboxed": 0},
        }
        wrappers, descendants, vendors = g.classify_vendor_processes(rows, 10, {"bashy"})
        self.assertEqual({r["pid"] for r in wrappers}, {11, 16})
        self.assertEqual({r["pid"] for r in descendants}, {12, 13, 14, 15})
        self.assertEqual({r["pid"] for r in vendors}, {12, 13, 15})
        self.assertFalse(all(r["sandboxed"] == 1 for r in descendants))

    def test_guarded_helpers_do_not_need_vendor_environment(self):
        rows = {
            1: {"pid": 1, "ppid": 0, "comm": "bashy", "sandboxed": 0},
            2: {"pid": 2, "ppid": 1, "comm": "bashy", "command": "bashy chat --agent ycode-kimi-k2.6", "sandboxed": 1,
                "HOME": "/tmp/arm", "CLAUDE_CONFIG_DIR": "/tmp/arm/.claude", "GOCACHE": "/tmp/arm/.cache/go-build"},
            3: {"pid": 3, "ppid": 2, "comm": "bashy", "command": "bashy kb context --json", "sandboxed": 1},
            4: {"pid": 4, "ppid": 2, "comm": "bashy", "command": "bashy dag -f dag.md package", "sandboxed": 1},
        }
        _, descendants, vendors = g.classify_vendor_processes(rows, 1, {"bashy"})
        self.assertEqual({r["pid"] for r in descendants}, {2, 3, 4})
        self.assertEqual([r["pid"] for r in vendors], [2])

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

    def test_kimi_balance_gate(self):
        row = {"status": "ok", "stale": False, "classification": "measured",
               "balance_unit": "USD", "balance": 19.04183}
        self.assertIsNone(g.balance_ok(row, 0.50))
        self.assertIn("below", g.balance_ok(dict(row, balance=0.20), 0.50))
        self.assertIn("no fresh", g.balance_ok(dict(row, stale=True), 0.50))

    def test_ycode_native_route_budget(self):
        body = json.dumps({"spec": {"routes": {"main": {"budget": {"maxCostUSD": 3}}}}})
        with mock.patch.object(g.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=body)):
            self.assertEqual(g.ycode_native_budget("/bin/bashy"), 3.0)
        with mock.patch.object(g.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="{}")):
            self.assertIsNone(g.ycode_native_budget("/bin/bashy"))

    def test_ycode_receipt_counts_requests_and_exact_tokens(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp, ".bashy", "ycode", "harness")
            (root / "sessions").mkdir(parents=True)
            (root / "payloads").mkdir()
            ref = "sha256:" + "a" * 64
            messages = [{"role": "user", "content": []},
                        {"role": "assistant",
                         "usage": {"input_tokens": 12, "output_tokens": 4}}]
            (root / "payloads" / ("a" * 64)).write_text(json.dumps(messages))
            events = [{"session_id": "s1", "type": "llm.requested", "data": {"model_ref": "primary"}},
                      {"session_id": "s1", "type": "session.turn-committed",
                       "data": {"messages_ref": ref}}]
            (root / "sessions" / "events.jsonl").write_text("\n".join(map(json.dumps, events)))
            usage, requests = g.ycode_receipt(tmp, "kimi-k2.6")
            self.assertEqual(requests, 1)
            self.assertEqual(usage[0]["usage"], {"input_tokens": 12, "output_tokens": 4})
            self.assertTrue(usage[0]["model_ok"])
            events.insert(1, {"session_id": "s1", "type": "llm.requested", "data": {"model_ref": "primary"}})
            (root / "sessions" / "events.jsonl").write_text("\n".join(map(json.dumps, events)))
            self.assertEqual(g.ycode_receipt(tmp, "kimi-k2.6")[1], 2)
            events.append({"session_id": "other", "type": "llm.requested"})
            (root / "sessions" / "events.jsonl").write_text("\n".join(map(json.dumps, events)))
            with self.assertRaisesRegex(ValueError, "one isolated"):
                g.ycode_receipt(tmp, "kimi-k2.6")

    def test_ycode_preflight_refuses_insufficient_balance_before_dispatch(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            args = SimpleNamespace(evidence=tmp, agent="ycode-kimi-k2.6", pack="skill-uptake",
                                   task="t6-pdf-fact", skill="script", bashy="/bin/bashy",
                                   tool="ycode", model="kimi-k2.6", quota_label="kimi",
                                   spend_ceiling=3.0, budget=100, quiet=20)
            row = {"label": "kimi", "status": "ok", "stale": False,
                   "classification": "measured", "balance_unit": "USD", "balance": 1.0}
            with mock.patch.object(g.sys, "platform", "darwin"), \
                 mock.patch.object(g.shutil, "which", return_value="/usr/bin/sandbox-exec"), \
                 mock.patch.object(g.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="kimi-k2.6\n")), \
                 mock.patch.object(g, "ycode_native_budget", return_value=3.0), \
                 mock.patch.object(g, "balance", return_value=(row, json.dumps({"items": [row]}))), \
                 mock.patch.object(g.subprocess, "Popen") as launch:
                self.assertEqual(g.run(args), 2)
                launch.assert_not_called()
            report = json.loads(Path(tmp, "report.json").read_text())
            self.assertEqual(report["verdict"], "REFUSED")
            self.assertIn("below", report["failures"][-1])

    def test_profile_denies_homes_decoy_and_keychain_cli(self):
        p = g.guard_profile(["/Users/op"], "/private/tmp/d")
        self.assertIn('(deny file-write* (subpath "/Users/op") (subpath "/private/tmp/d") (with send-signal SIGKILL))', p)
        self.assertIn('(deny process-exec (literal "/usr/bin/security"))', p)


def fake_bashy(tmp, refresh_rc, refresh_stale, cached_stale):
    def doc(stale):
        return json.dumps({"items": [{"label": "claude", "window": w, "status": "ok", "used_percent": 5,
                                      "stale": stale} for w in ("5h", "week")]})
    p = os.path.join(tmp, "bashy")
    Path(p).write_text("#!/bin/sh\n"
                       f"case \"$*\" in *--refresh*) echo '{doc(refresh_stale)}'; echo boom >&2; exit {refresh_rc};; esac\n"
                       f"echo '{doc(cached_stale)}'\n")
    os.chmod(p, 0o755)
    return p


class QuotaReadTest(unittest.TestCase):
    def test_refresh_ok(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            rows, _, meta = g.quota(fake_bashy(tmp, 0, False, True), "claude")
            self.assertEqual(meta, {"source": "refresh"})
            self.assertIsNone(g.quota_ok(rows, 80, 90))

    def test_refresh_failure_recorded_nonstale_fallback_accepted(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            rows, _, meta = g.quota(fake_bashy(tmp, 1, False, False), "claude")
            self.assertEqual(meta["source"], "cached-fallback")
            self.assertIn("rc=1", meta["refresh_error"])
            self.assertIn("boom", meta["refresh_error"])
            self.assertTrue(meta["fallback_nonstale"])
            self.assertIsNone(g.quota_ok(rows, 80, 90))

    def test_stale_fallback_refused(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            rows, _, meta = g.quota(fake_bashy(tmp, 0, True, True), "claude")
            self.assertIn("stale=['5h', 'week']", meta["refresh_error"])
            self.assertFalse(meta["fallback_nonstale"])
            self.assertIn("not ok", g.quota_ok(rows, 80, 90))


class ProcEnvTest(unittest.TestCase):
    def test_reads_only_named_vars_of_a_live_process(self):
        import subprocess
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            # Not /bin/sleep: ps cannot read a platform binary's environment.
            p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"],
                                 env={"HOME": tmp, "SECRET": "s", "PATH": "/bin"})
            try:
                import time
                time.sleep(0.5)
                env = g.proc_env(p.pid, ("HOME", "CLAUDE_CONFIG_DIR"))
            finally:
                p.kill()
                p.wait()
            self.assertEqual(env, {"HOME": tmp, "CLAUDE_CONFIG_DIR": None})


class PairTest(unittest.TestCase):
    # pair() reads the host process table; feed it a fixed ps listing so the
    # tests do not depend on whatever bench runners are live on this machine.
    PS = "1 /sbin/launchd\n2 /bin/zsh\n"

    def setUp(self):
        import subprocess
        from unittest import mock
        import guarded_pair as gp
        real = subprocess.run

        def run(argv, *a, **kw):
            if argv[:1] == ["/bin/ps"]:
                return subprocess.CompletedProcess(argv, 0, stdout=self.PS, stderr="")
            return real(argv, *a, **kw)
        patcher = mock.patch.object(gp.subprocess, "run", side_effect=run)
        patcher.start()
        self.addCleanup(patcher.stop)

    def args(self, tmp):
        import types
        return types.SimpleNamespace(agent="a", pack="skill-uptake", task="t6-pdf-fact", model="m", budget=100,
                                     quiet=20, bashy="/x/bashy", evidence=tmp, order=["off", "on"],
                                     tool=None, vendor_comm=[])

    def fake(self, rcs, calls):
        def run(argv):
            arm = argv[argv.index("--skill") + 1]
            ev = argv[argv.index("--evidence") + 1]
            calls.append(argv)
            os.makedirs(ev, exist_ok=True)
            rc = rcs[arm]
            Path(ev, "report.json").write_text(json.dumps({"verdict": "PASS" if rc == 0 else "UNSCORED",
                                                           "failures": [] if rc == 0 else ["no attributable usage"]}))
            return rc
        return run

    def test_first_arm_failure_stops_before_second_request(self):
        import guarded_pair as gp
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            calls = []
            out = gp.pair(self.args(tmp), self.fake({"off": 1, "on": 0}, calls))
            self.assertEqual(len(calls), 1)
            self.assertEqual(out["verdict"], "UNSCORED")
            self.assertEqual(out["arms"][1]["requests"], 0)
            self.assertIn("not run", out["arms"][1]["why"])

    def test_same_task_model_budget_both_arms(self):
        import guarded_pair as gp
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            calls = []
            out = gp.pair(self.args(tmp), self.fake({"off": 0, "on": 0}, calls))
            self.assertEqual(out["verdict"], "PAIRED")
            strip = [[v for i, v in enumerate(c) if i == 0 or c[i - 1] not in ("--skill", "--evidence")] for c in calls]
            self.assertEqual(strip[0], strip[1])
            self.assertTrue(out["grader_sha256"])

    def test_script_pair_passes_ycode_guard_options(self):
        import guarded_pair as gp
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            args = self.args(tmp)
            args.order = ["script", "on"]
            args.tool = "ycode"
            args.vendor_comm = ["bashy"]
            calls = []
            out = gp.pair(args, self.fake({"script": 0, "on": 0}, calls))
            self.assertEqual(out["verdict"], "PAIRED")
            self.assertEqual([c[c.index("--skill") + 1] for c in calls], ["script", "on"])
            self.assertTrue(all(c[-4:] == ["--tool", "ycode", "--vendor-comm", "bashy"] for c in calls))

    def test_concurrent_runner_detected(self):
        import guarded_pair as gp
        ps = "10 python3 scripts/guarded_live_arm.py --agent x\n11 /bin/zsh\n12 bashy dag run AGENT=y\n13 vim\n"
        self.assertEqual(len(gp.concurrent_runs(ps, {13})), 2)
        self.assertEqual(gp.concurrent_runs(ps, {10, 12}), [])

    def test_ancestry_excluded_but_sibling_runner_detected(self):
        from unittest import mock
        import guarded_pair as gp
        self.PS = "10 1\n11 10\n12 11\n13 10\n"
        with mock.patch.object(gp.os, "getpid", return_value=12):
            own = gp.own_pids()
        self.assertEqual(own, {12, 11, 10, 1})
        ps = ("10 /bin/zsh python3 scripts/guarded_pair.py --agent self\n"
              "11 bashy python3 scripts/guarded_pair.py --agent self\n"
              "13 python3 scripts/guarded_live_arm.py --agent other\n")
        self.assertEqual(gp.concurrent_runs(ps, own),
                         ["13 python3 scripts/guarded_live_arm.py --agent other"])

    def test_live_runner_blocks_pair_before_any_request(self):
        import guarded_pair as gp
        self.PS = "99999 python3 scripts/guarded_live_arm.py --agent other\n"
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            calls = []
            out = gp.pair(self.args(tmp), self.fake({"off": 0, "on": 0}, calls))
            self.assertEqual(calls, [])
            self.assertEqual(out["verdict"], "UNSCORED")
            self.assertEqual(len(out["concurrent_runs"]), 1)


if __name__ == "__main__":
    unittest.main()

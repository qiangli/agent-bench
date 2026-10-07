import importlib.util, json, os, shutil, tempfile, unittest
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location("experiment", Path(__file__).with_name("bashsharp_l2_experiment.py")); experiment = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(experiment)
SHELL_SPEC = importlib.util.spec_from_file_location("action_shell", Path(__file__).with_name("bashsharp_l2_action_shell.py")); action_shell = importlib.util.module_from_spec(SHELL_SPEC); SHELL_SPEC.loader.exec_module(action_shell)

class ExperimentTest(unittest.TestCase):
    def test_terminal_bench_failure_taxonomy(self):
        cases = {"bash: nope: command not found": "command_not_found", "No such file or directory": "file_not_found", "ModuleNotFoundError: No module named x": "module_not_found", "bash: syntax error near": "shell_syntax", "SyntaxError: invalid syntax": "script_syntax", "timeout": "other"}
        for text, want in cases.items():
            with self.subTest(text=text): self.assertEqual(experiment.classify(text), want)
    def test_prepare_requires_k_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "candidate"; candidate.write_text("x")
            args = type("Args", (), {"candidate": str(candidate), "output": str(Path(tmp) / "out"), "model": "m", "agent": "a", "seed": "1", "k": 2})()
            with self.assertRaises(ValueError): experiment.prepare(args)
    def test_action_shell_uses_real_dialect_prelude(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); candidate = root / "bashy"; candidate.write_text("")
            assets = root / "arms"; assets.mkdir(); (assets / "fences.bsh").write_text("fence")
            env = {"BASHY_EXPERIMENT_ARM": "fences", "BASHY_EXPERIMENT_CANDIDATE": str(candidate), "BASHY_EXPERIMENT_ASSETS": str(assets)}
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(action_shell.subprocess, "run") as run:
                run.return_value.returncode = 0; self.assertEqual(action_shell.main(["-c", "echo hi"]), 0)
            self.assertEqual(run.call_args.args[0][:2], [str(candidate), "--bashpp"])
            self.assertEqual(run.call_args.args[0][2], str(assets / "fences.bsh"))
    @unittest.skipUnless(shutil.which("bashy"), "bashy is required for paired statistics")
    def test_report_requires_and_emits_all_paired_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); manifest = {"k": 3, "tasks": [{"id": "t01"}], "pricing": {"usd": "unknown"}}
            manifest_path = root / "manifest.json"; manifest_path.write_text(json.dumps(manifest))
            raw = root / "raw.jsonl"
            raw.write_text("".join(json.dumps({"task": "t01", "repetition": repetition, "arm": arm, "points": 2 if arm != "bash" else 0, "fail": False, "tokens": 4, "token_source": "provider", "terminal_output": "command not found"}) + "\n" for repetition in range(1, 4) for arm in experiment.ARMS))
            output = root / "evidence.json"; args = type("Args", (), {"manifest": str(manifest_path), "raw": str(raw), "output": str(output), "bashy": shutil.which("bashy")})()
            self.assertEqual(experiment.report(args), 0)
            evidence = json.loads(output.read_text())
            self.assertEqual(len(evidence["raw_rows"]), 9)
            self.assertEqual(evidence["failure_taxonomy"]["command_not_found"], 9)

if __name__ == "__main__": unittest.main()

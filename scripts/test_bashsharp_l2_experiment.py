import importlib.util, json, os, shutil, tempfile, unittest
from pathlib import Path
from unittest import mock
SPEC=importlib.util.spec_from_file_location("experiment",Path(__file__).with_name("bashsharp_l2_experiment.py")); experiment=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(experiment)
SHELL=importlib.util.spec_from_file_location("action_shell",Path(__file__).with_name("bashsharp_l2_action_shell.py")); action_shell=importlib.util.module_from_spec(SHELL); SHELL.loader.exec_module(action_shell)
class ExperimentTest(unittest.TestCase):
 def manifest(self):
  m={"k":3,"model":"m","agent":"a","candidate_sha256":"c","model_options_sha256":"o","manifest_sha256":"z","pricing":{"usd":"unknown"},"tasks":[{"id":"t01","fixture_tree_sha256":"f"}]}; return m
 def row(self,r,arm): return {"task":"t01","repetition":r,"arm":arm,"points":2,"fail":False,"tokens":4,"token_source":"provider","terminal_output":"command not found","model":"m","agent":"a","candidate_sha256":"c","fixture_tree_sha256":"f","model_options_sha256":"o","manifest_sha256":"z"}
 def test_taxonomy(self): self.assertEqual(experiment.classify("bash: nope: command not found"),"command_not_found")
 def test_duplicate_and_unknown_cost_rejected(self):
  raw=[self.row(r,a) for r in range(1,4) for a in experiment.ARMS]; raw.append(self.row(1,"bash"))
  with self.assertRaisesRegex(ValueError,"duplicate"): experiment.validate(self.manifest(),raw)
  raw=raw[:-1]; raw[0]["token_source"]="unknown"
  with self.assertRaisesRegex(ValueError,"unknown"): experiment.validate(self.manifest(),raw)
 def test_baseline_is_plain_bash(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); candidate=root/"bashy"; candidate.write_text(""); assets=root/"arms"; assets.mkdir()
   env={"BASHY_EXPERIMENT_ARM":"bash","BASHY_EXPERIMENT_CANDIDATE":str(candidate),"BASHY_EXPERIMENT_ASSETS":str(assets)}
   with mock.patch.dict(os.environ,env,clear=False),mock.patch.object(action_shell.subprocess,"run") as run:
    run.return_value.returncode=0; self.assertEqual(action_shell.main(["-c","echo hi"]),0)
   self.assertEqual(run.call_args.args[0],[str(candidate),"-c","echo hi"])
 @unittest.skipUnless(shutil.which("bashy"),"bashy required for paired statistics")
 def test_report(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); m=self.manifest(); mp=root/"m.json"; mp.write_text(json.dumps(m)); raw=root/"raw.jsonl"; raw.write_text("".join(json.dumps(self.row(r,a))+"\n" for r in range(1,4) for a in experiment.ARMS)); out=root/"e.json"
   self.assertEqual(experiment.report(type("A",(),{"manifest":str(mp),"raw":str(raw),"output":str(out),"bashy":shutil.which("bashy")})()),0); self.assertEqual(json.loads(out.read_text())["tokens"]["total"],36)
if __name__=="__main__": unittest.main()

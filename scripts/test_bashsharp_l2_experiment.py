import importlib.util, json, os, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).parent))
SPEC=importlib.util.spec_from_file_location("experiment",Path(__file__).with_name("bashsharp_l2_experiment.py")); experiment=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(experiment)
SHELL=importlib.util.spec_from_file_location("action_shell",Path(__file__).with_name("bashsharp_l2_action_shell.py")); action_shell=importlib.util.module_from_spec(SHELL); SHELL.loader.exec_module(action_shell)
EXECUTOR=importlib.util.spec_from_file_location("executor",Path(__file__).with_name("bashsharp_l2_executor.py")); executor=importlib.util.module_from_spec(EXECUTOR); EXECUTOR.loader.exec_module(executor)
ADAPTER=importlib.util.spec_from_file_location("adapter",Path(__file__).with_name("bashsharp_l2_codex_adapter.py")); adapter=importlib.util.module_from_spec(ADAPTER); ADAPTER.loader.exec_module(adapter)
class ExperimentTest(unittest.TestCase):
 def manifest(self):
  m={"schema":"bashsharp-l2-v4","k":3,"model":"m","agent":"a","provider":"codex","provider_cli":"codex-cli 0.157.1","candidate_sha256":"c","arm_assets_tree_sha256":"assets","model_options_sha256":"o","pricing":{"usd":"unknown"},"tasks":[{"id":"t01","fixture_tree_sha256":"f"}]}; m["manifest_sha256"]=experiment.json_digest(m); return m
 def row(self,r,arm): return {"task":"t01","repetition":r,"arm":arm,"points":2,"fail":False,"tokens":4,"token_source":"codex-turn.completed","terminal_output":"command not found","model":"m","agent":"a","provider":"codex","provider_cli":"codex-cli 0.157.1","provider_image_id":"sha256:image","negative_control_sha256":"n","candidate_sha256":"c","fixture_tree_sha256":"f","arm_assets_tree_sha256":"assets","model_options_sha256":"o","manifest_sha256":self.manifest()["manifest_sha256"]}
 def test_taxonomy(self): self.assertEqual(experiment.classify("bash: nope: command not found"),"command_not_found")
 def test_manifest_digest_is_not_self_asserted(self):
  m={"schema":"x"}; m["manifest_sha256"]=experiment.json_digest(m.copy()); experiment.validate_manifest(m)
  m["schema"]="changed"
  with self.assertRaisesRegex(ValueError,"manifest digest"): experiment.validate_manifest(m)
 def test_schedule_is_complete_and_arm_balanced(self):
  m={"seed":381,"k":3,"tasks":[{"id":f"t{i:02}"} for i in range(20)]}; jobs=executor.schedule(m)
  self.assertEqual(len(jobs),180)
  self.assertEqual({a:sum(job[2]==a for job in jobs) for a in experiment.ARMS},{a:60 for a in experiment.ARMS})
 def test_executor_initializes_clean_fixture_commit_for_history_tasks(self):
  task=Path(__file__).parents[1]/"packs/l2/t11-refactor"; fixture=task/"fixture"
  with tempfile.TemporaryDirectory() as d:
   workspace=Path(d)/"work"; executor.initialize_workspace(fixture,workspace)
   def git(*args): return __import__('subprocess').run(["git","-C",str(workspace),*args],text=True,capture_output=True,check=True).stdout
   self.assertEqual(git("branch","--show-current").strip(),"main")
   self.assertEqual(git("log","-1","--format=%s").strip(),"fixture")
   self.assertEqual(git("status","--porcelain"),"")
   fixture_shapes=(fixture/"shapes.py").read_text()
   shutil.copytree(task/"reference",workspace,dirs_exist_ok=True)
   self.assertEqual(executor.grade("l2","t11-refactor",workspace,fixture)["points"],2)
   self.assertEqual(git("show","HEAD:shapes.py"),fixture_shapes)
 def test_arm_assets_drift_rejected(self):
  raw=[self.row(r,a) for r in range(1,4) for a in experiment.ARMS]; raw[0]["arm_assets_tree_sha256"]="drift"
  with self.assertRaisesRegex(ValueError,"arm assets digest"): experiment.validate(self.manifest(),raw)
 def test_void_history_retries_only_when_no_valid_attempt(self):
  m={"seed":1,"k":3,"tasks":[{"id":"t01"}]}; jobs=executor.schedule(m); key=jobs[0]
  void={"task":key[0],"repetition":key[1],"arm":key[2],"void":True}
  pending=executor.pending_jobs(m,[void]); self.assertIn(key,pending)
  valid=dict(void); valid.pop("void"); self.assertNotIn(key,executor.pending_jobs(m,[void,valid]))
 def test_protocol_failures_keep_usage_and_are_scored(self):
  row={"points":2,"fail":False,"tokens":71,"token_source":"codex-turn.completed"}
  executor.apply_protocol_failure(row,{"command_executions":2,"forbidden_action_types":["web_search"]})
  self.assertEqual((row["points"],row["fail"],row["tokens"]),(0,True,71)); self.assertNotIn("void",row)
  row={"points":2,"fail":False,"tokens":8}; executor.apply_protocol_failure(row,{"command_executions":0,"forbidden_action_types":[]})
  self.assertEqual((row["points"],row["fail"]),(0,True)); self.assertNotIn("void",row)
 def test_void_attempt_history_and_duplicate_valid_outcomes(self):
  m=self.manifest(); raw=[self.row(r,a) for r in range(1,4) for a in experiment.ARMS]
  void=dict(raw[0]); void.update(void=True,void_reason="temporary infra failure"); raw.insert(0,void); experiment.validate(m,raw)
  raw.append(self.row(1,"bash"))
  with self.assertRaisesRegex(ValueError,"duplicate valid outcome"): experiment.validate(m,raw)
  terminal=[r for r in raw if not (r["task"]=="t01" and r["repetition"]==1 and r["arm"]=="bash")]
  terminal.append(void)
  with self.assertRaisesRegex(ValueError,"exactly paired"): experiment.validate(m,terminal)
 def test_candidate_architecture_is_arm64_elf(self):
  with tempfile.TemporaryDirectory() as d:
   binary=Path(d)/"bashy"; header=bytearray(20); header[:6]=b"\x7fELF\x02\x01"; header[18:20]=(183).to_bytes(2,"little"); binary.write_bytes(header)
   self.assertTrue(experiment.is_linux_arm64_elf(binary))
   header[18:20]=(62).to_bytes(2,"little"); binary.write_bytes(header)
   self.assertFalse(experiment.is_linux_arm64_elf(binary))
 def test_adapter_redacts_runtime_auth_values(self):
  auth=json.dumps({"tokens":{"access_token":"secret-access-token-value","refresh_token":"secret-refresh-token-value"}})
  secrets=adapter.secret_literals(auth); output=adapter.redact("x secret-access-token-value y",secrets)
  self.assertNotIn("secret-access-token-value",output); self.assertIn("[REDACTED]",output)
 def test_timeout_stops_named_container(self):
  process=mock.Mock(); process.communicate.side_effect=[__import__('subprocess').TimeoutExpired(['podman'],1,output='partial'),('tail','err')]; process.returncode=None
  with mock.patch.object(executor.subprocess,"Popen",return_value=process),mock.patch.object(executor,"stop_container") as stop:
   code,out,err,timed=executor.bounded_container(["podman"],"podman","trial",1)
  self.assertEqual((code,out,err,timed),(124,"tail","err",True)); stop.assert_called_once_with("podman","trial")
 def test_duplicate_rejected_and_unknown_usage_retained(self):
  raw=[self.row(r,a) for r in range(1,4) for a in experiment.ARMS]; raw.append(self.row(1,"bash"))
  with self.assertRaisesRegex(ValueError,"duplicate"): experiment.validate(self.manifest(),raw)
  raw=raw[:-1]; raw[0]["tokens"]=None; raw[0]["token_source"]="unknown-no-final-usage"
  experiment.validate(self.manifest(),raw)
 def test_baseline_is_plain_bash(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); candidate=root/"bashy"; candidate.write_text(""); assets=root/"arms"; assets.mkdir()
   env={"BASHY_EXPERIMENT_ARM":"bash","BASHY_EXPERIMENT_CANDIDATE":str(candidate),"BASHY_EXPERIMENT_ASSETS":str(assets)}
   with mock.patch.dict(os.environ,env,clear=False),mock.patch.object(action_shell.subprocess,"run") as run:
    run.return_value.returncode=0; self.assertEqual(action_shell.main(["-c","echo hi"]),0)
   self.assertEqual(run.call_args.args[0],[str(candidate),"--no-bashpp","-c","echo hi"])
   with mock.patch.dict(os.environ,env,clear=False),mock.patch.object(action_shell.subprocess,"run") as run:
    run.return_value.returncode=0; self.assertEqual(action_shell.main(["script.sh","a b"]),0)
   self.assertEqual(run.call_args.args[0],[str(candidate),"--no-bashpp","script.sh","a b"])
   with mock.patch.dict(os.environ,env,clear=False),mock.patch.object(action_shell.subprocess,"run") as run:
    run.return_value.returncode=0; self.assertEqual(action_shell.main(["-lc","echo hi"]),0)
   self.assertEqual(run.call_args.args[0],[str(candidate),"--no-bashpp","-c","echo hi"])
 def test_secret_is_owned_by_the_mapped_runtime_user(self):
  self.assertEqual(executor.runtime_identity_args("auth",501,20),[
   "--userns=keep-id","--user","501:20",
   "--secret","auth,target=s381-auth,uid=501,gid=20,mode=0400",
  ])
 def test_timeout_is_a_scored_failure_not_a_void(self):
  row=executor.timeout_outcome({"points":2,"fail":False})
  self.assertNotIn("void",row); self.assertEqual(row["points"],0); self.assertTrue(row["fail"])
  self.assertIsNone(row["tokens"]); self.assertEqual(row["token_source"],"unknown-no-final-usage")
 def test_arm_files_use_real_fence_method_and_honest_contract_scope(self):
  arms=Path(__file__).parents[1]/"experiments/bashsharp-l2/arms"
  fence=(arms/"fences.bsh").read_text(); guards=(arms/"guards-contracts.bsh").read_text()
  self.assertIn('"name":"run"',fence); self.assertIn("experiment_context.run()",fence)
  self.assertIn('source "$BASHY_EXPERIMENT_ACTION"',fence)
  self.assertNotIn("fence_ready",fence); self.assertNotIn("@ensure",guards+fence)
 @unittest.skipUnless(shutil.which("bashy"),"bashy required for paired statistics")
 def test_report(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); m=self.manifest(); mp=root/"m.json"; mp.write_text(json.dumps(m)); all_rows=[self.row(r,a) for r in range(1,4) for a in experiment.ARMS]; all_rows[0].update(tokens=None,token_source="unknown-no-final-usage",timed_out=True,points=0,fail=True); raw=root/"raw.jsonl"; raw.write_text("".join(json.dumps(row)+"\n" for row in all_rows)); out=root/"e.json"
   self.assertEqual(experiment.report(type("A",(),{"manifest":str(mp),"raw":str(raw),"output":str(out),"bashy":shutil.which("bashy")})()),0); evidence=json.loads(out.read_text()); self.assertEqual(evidence["tokens"],{"known_total_lower_bound":32,"unknown_rows":1}); self.assertEqual(evidence["failure_taxonomy"],{"timeout":1}); self.assertEqual(evidence["resolved_terminal_output"],{"command_not_found":8})
if __name__=="__main__": unittest.main()

#!/usr/bin/env python3
"""Bounded OCI executor for the frozen Bash# L2 paired experiment.

The provider command is intentionally supplied by the operator: it runs in the
container and must finish stdout with a JSON usage receipt.  It sees a writable
fixture and a read-only candidate, never references/graders/results.
"""
from __future__ import annotations
import argparse, concurrent.futures, json, os, shutil, subprocess, tempfile, time
from pathlib import Path
from bashsharp_l2_experiment import ARMS, ROOT, digest, tree_digest
from pack_runner import grade

def run(cmd: list[str], **kw): return subprocess.run(cmd, text=True, capture_output=True, check=False, **kw)
def invoke(a, m, task, repetition, arm):
    fixture=ROOT/"packs/l2"/task/"fixture"; work=Path(tempfile.mkdtemp(prefix="s381-")); shutil.copytree(fixture,work/"work")
    # The harness adapter/prelude are runtime plumbing, copied into the image
    # filesystem; only fixture and candidate are bind mounts exposed to agent work.
    assets=work/"assets"; shutil.copytree(ROOT/"experiments/bashsharp-l2/arms",assets); shutil.copy2(ROOT/"scripts/bashsharp_l2_action_shell.py",work/"action-shell")
    usage=work/"usage.json"; log=work/"provider.log"; plant=f"S381_PLANTED_READ_{m['manifest_sha256'][:16]}"
    env={"BASHY_EXPERIMENT_ARM":arm,"BASHY_EXPERIMENT_CANDIDATE":"/candidate/bashy","BASHY_EXPERIMENT_ASSETS":"/opt/s381/arms","SHELL":"/opt/s381/action-shell","BASHY_EXPERIMENT_PROMPT":"Read TASK.md and do the task.","BASHY_EXPERIMENT_USAGE_FILE":"/tmp/usage.json","BASHY_EXPERIMENT_BUDGET_SECONDS":str(m["budget_seconds"])}
    pcmd=[a.engine,"run","--rm","--read-only","--cap-drop=ALL","--security-opt=no-new-privileges","--pids-limit",str(a.pids_limit),"--memory",a.memory,"--cpus",str(a.cpus),"--userns=keep-id","--tmpfs","/tmp:rw,nosuid,nodev,size=256m","--network",a.network,"-v",f"{work/'work'}:/work:rw","-v",f"{Path(m['candidate_path'])}:/candidate/bashy:ro","-v",f"{assets}:/opt/s381/arms:ro","-v",f"{work/'action-shell'}:/opt/s381/action-shell:ro","-w","/work"]
    for k,v in env.items(): pcmd += ["-e",f"{k}={v}"]
    pcmd += [a.image,"/bin/sh","-lc",a.provider_command]
    started=time.time(); done=run(pcmd,timeout=m["budget_seconds"]+a.grace); elapsed=round(time.time()-started,3); log.write_text(done.stdout+done.stderr)
    # --rm prevents host result mounting into the agent.  Usage must be emitted
    # on stdout as a final JSON line prefixed S381_USAGE:, not guessed from logs.
    usage_line=next((line.removeprefix("S381_USAGE:") for line in reversed(done.stdout.splitlines()) if line.startswith("S381_USAGE:")),None)
    try: usage_data=json.loads(usage_line) if usage_line else None
    except json.JSONDecodeError: usage_data=None
    result=grade("l2",task,work/"work",fixture)
    terminal=(done.stdout+done.stderr)[-16000:]
    row={"task":task,"repetition":repetition,"arm":arm,"points":result["points"],"fail":bool(result["fail"]),"terminal_output":terminal,"elapsed_seconds":elapsed,"model":m["model"],"agent":m["agent"],"candidate_sha256":m["candidate_sha256"],"fixture_tree_sha256":tree_digest(fixture),"model_options_sha256":m["model_options_sha256"],"manifest_sha256":m["manifest_sha256"],"raw_log":str(log)}
    if plant in terminal: row.update({"void":True,"void_reason":"planted evaluator-only marker appeared in agent output"})
    elif not isinstance(usage_data,dict) or not isinstance(usage_data.get("tokens"),int) or usage_data["tokens"]<0 or not usage_data.get("token_source"): row.update({"void":True,"void_reason":"provider did not emit known token usage"})
    else: row.update({"tokens":usage_data["tokens"],"token_source":usage_data["token_source"],"provider_usage":usage_data})
    return row

def main():
    p=argparse.ArgumentParser(); p.add_argument("--manifest",required=True); p.add_argument("--raw",required=True); p.add_argument("--provider-command",required=True); p.add_argument("--image",required=True); p.add_argument("--engine",default="podman"); p.add_argument("--jobs",type=int,default=2); p.add_argument("--cpus",type=float,default=1); p.add_argument("--memory",default="1500m"); p.add_argument("--pids-limit",type=int,default=256); p.add_argument("--network",default="slirp4netns"); p.add_argument("--grace",type=int,default=30); a=p.parse_args()
    if a.jobs<1 or a.jobs>2: p.error("--jobs must be 1 or 2 on the 4-CPU/8-GB host")
    m=json.loads(Path(a.manifest).read_text()); jobs=[(t["id"],r,arm) for t in m["tasks"] for r in range(1,m["k"]+1) for arm in ARMS]
    out=Path(a.raw); out.parent.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool, out.open("a") as f:
        for row in pool.map(lambda x:invoke(a,m,*x),jobs): f.write(json.dumps(row,sort_keys=True)+"\n"); f.flush()
    return 0
if __name__=="__main__": raise SystemExit(main())

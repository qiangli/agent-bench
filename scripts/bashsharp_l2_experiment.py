#!/usr/bin/env python3
"""Fail-closed manifest and evidence gate for Sprint 381's paired L2 run."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = sorted(p.name for p in (ROOT / "packs/l2").iterdir() if (p / "task.yaml").is_file())
ARMS = ("bash", "guards-contracts", "fences")
ACTION_CONSTRAINT = "\n\nExperiment constraint: use shell commands for every workspace read, write, test, and git action. Do not use apply_patch, file-edit, MCP, web, or other action tools. The shell is the measured interface."

def digest(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()
def json_digest(v: object) -> str: return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def is_linux_arm64_elf(p: Path) -> bool:
    header=p.read_bytes()[:20]
    if len(header)<20 or header[:4]!=b"\x7fELF" or header[4]!=2 or header[5] not in (1,2): return False
    return int.from_bytes(header[18:20],"little" if header[5]==1 else "big")==183
def tree_digest(p: Path) -> str:
    return hashlib.sha256("".join(f"{x.relative_to(p)}:{digest(x)}\n" for x in sorted(p.rglob("*")) if x.is_file()).encode()).hexdigest()
def validate_manifest(m: dict) -> None:
    claimed=m.get("manifest_sha256"); unsigned={key:value for key,value in m.items() if key!="manifest_sha256"}
    if not isinstance(claimed,str) or json_digest(unsigned)!=claimed: raise ValueError("manifest digest is invalid")
def classify(text: str) -> str:
    value = text.lower()
    if "command not found" in value or "not recognized as an internal" in value: return "command_not_found"
    if "no such file or directory" in value or "cannot find the file" in value: return "file_not_found"
    if "modulenotfounderror" in value or "no module named" in value or "cannot find module" in value: return "module_not_found"
    if "syntax error" in value and ("shell" in value or "bash" in value): return "shell_syntax"
    if "syntaxerror" in value or "parse error" in value or "syntax error" in value: return "script_syntax"
    return "other"

def prepare(a: argparse.Namespace) -> int:
    candidate = Path(a.candidate).resolve()
    if not candidate.is_file() or not os.access(candidate, os.X_OK): raise ValueError("candidate must be a readable executable file")
    if len(TASKS) != 20: raise ValueError("packs/l2 must contain exactly 20 tasks")
    if a.k < 3 or a.budget_seconds <= 0: raise ValueError("K must be at least 3 and budget must be positive")
    opts = json.loads(a.model_options)
    if not isinstance(opts, dict): raise ValueError("--model-options must be a JSON object")
    if a.model != "gpt-6-luna" or opts != {"model_reasoning_effort":"low"}: raise ValueError("the frozen provider configuration is gpt-6-luna with low reasoning effort")
    out = Path(a.output); out.mkdir(parents=True, exist_ok=False)
    if not is_linux_arm64_elf(candidate): raise ValueError("candidate must be a Linux/arm64 ELF executable")
    task_rows=[]
    for task in TASKS:
        fixture=ROOT/"packs/l2"/task/"fixture"; task_file=fixture/"TASK.md"
        if not task_file.is_file(): raise ValueError(f"{task} fixture is missing TASK.md")
        prompt="Read TASK.md and do the task."
        task_rows.append({"id":task,"task_sha256":digest(ROOT/"packs/l2"/task/"task.yaml"),"fixture_tree_sha256":tree_digest(fixture),"prompt":prompt,"task_prompt_sha256":digest(task_file),"provider_prompt_sha256":hashlib.sha256((prompt+ACTION_CONSTRAINT).encode()).hexdigest()})
    m = {"schema":"bashsharp-l2-v4", "story_id":"050a68a821a9", "pack":"l2", "provider":"codex", "provider_cli":"codex-cli 0.157.1", "tasks":task_rows, "k":a.k, "model":a.model, "agent":"codex-cli/0.157.1", "seed":a.seed, "model_options":opts, "model_options_sha256":json_digest(opts), "candidate_path":str(candidate), "candidate_sha256":digest(candidate), "arm_assets_tree_sha256":tree_digest(ROOT/"experiments/bashsharp-l2/arms"), "budget_seconds":a.budget_seconds, "isolation":{"required":True,"method":"oci","platform":"linux/arm64","mounts":"fixture+candidate+arm-assets+runtime-secret","evaluator_outside_principal":True,"shell_enforcement":"container /bin/sh and /bin/bash are arm wrapper"}, "arms":{"bash":{"dialect":"explicitly-off","shell_args":["--no-bashpp"],"prelude":None},"guards-contracts":{"dialect":"on","shell_args":["--bashpp"],"prelude":"arms/guards-contracts.bsh"},"fences":{"dialect":"on","shell_args":["--bashpp"],"prelude":"arms/fences.bsh"}}, "pricing":{"usd":"unknown","reason":"dollars remain unknown without provider pricing evidence"}}
    m["manifest_sha256"] = json_digest(m)
    (out/"manifest.json").write_text(json.dumps(m, indent=2, sort_keys=True)+"\n"); print(out/"manifest.json"); return 0

def rows(p: Path) -> list[dict]:
    if not p.is_file(): raise ValueError("raw results file is missing")
    answer=[]
    for n,line in enumerate(p.read_text().splitlines(),1):
        if not line.strip(): continue
        try: row=json.loads(line)
        except json.JSONDecodeError as e: raise ValueError(f"raw row {n} is invalid JSON: {e.msg}") from e
        if not isinstance(row,dict): raise ValueError(f"raw row {n} is not an object")
        row["_line"]=n; answer.append(row)
    return answer

def validate(m: dict, raw: list[dict]) -> None:
    need={"task","repetition","arm","points","fail","tokens","token_source","model","agent","provider","provider_cli","provider_image_id","candidate_sha256","fixture_tree_sha256","model_options_sha256","manifest_sha256","terminal_output","negative_control_sha256"}
    expected={(x["id"],r,a) for x in m["tasks"] for r in range(1,m["k"]+1) for a in ARMS}; fixtures={x["id"]:x["fixture_tree_sha256"] for x in m["tasks"]}; seen=set()
    image_ids=set()
    attempts=Counter()
    for index,row in enumerate(raw,1):
        row.setdefault("_line",index)
        key=(row.get("task"),row.get("repetition"),row.get("arm"))
        if row.get("void"):
            if key not in expected: raise ValueError(f"raw row {row['_line']} has invalid void task/repetition/arm")
            attempts[key]+=1
            if not row.get("void_reason"): raise ValueError(f"raw row {row['_line']} void attempt lacks reason")
            continue
        missing=need-row.keys()
        if missing: raise ValueError(f"raw row {row['_line']} missing fields: {', '.join(sorted(missing))}")
        if not isinstance(row["repetition"],int) or key not in expected: raise ValueError(f"raw row {row['_line']} has invalid task/repetition/arm")
        attempts[key]+=1
        if key in seen: raise ValueError(f"duplicate valid outcome for task/repetition/arm: {key}")
        seen.add(key)
        if not isinstance(row["points"],(int,float)) or not isinstance(row["fail"],bool): raise ValueError(f"raw row {row['_line']} has invalid grade")
        known_tokens=isinstance(row["tokens"],int) and not isinstance(row["tokens"],bool) and row["tokens"]>=0 and row["token_source"]=="codex-turn.completed"
        unknown_tokens=row["tokens"] is None and row["token_source"]=="unknown-no-final-usage"
        if not (known_tokens or unknown_tokens): raise ValueError(f"raw row {row['_line']} has invalid token accounting")
        if row["model"]!=m["model"] or row["agent"]!=m["agent"]: raise ValueError(f"raw row {row['_line']} mixes model or agent")
        if row["provider"]!=m["provider"] or row["provider_cli"]!=m["provider_cli"]: raise ValueError(f"raw row {row['_line']} mixes provider or provider CLI")
        if not isinstance(row["provider_image_id"],str) or not row["provider_image_id"]: raise ValueError(f"raw row {row['_line']} has no provider image identity")
        image_ids.add(row["provider_image_id"])
        if row["candidate_sha256"]!=m["candidate_sha256"] or row["fixture_tree_sha256"]!=fixtures[row["task"]]: raise ValueError(f"raw row {row['_line']} mixes candidate or fixture digest")
        if row.get("arm_assets_tree_sha256")!=m["arm_assets_tree_sha256"]: raise ValueError(f"raw row {row['_line']} mixes arm assets digest")
        if row["model_options_sha256"]!=m["model_options_sha256"] or row["manifest_sha256"]!=m["manifest_sha256"]: raise ValueError(f"raw row {row['_line']} has mixed model options or manifest")
    if seen!=expected: raise ValueError(f"raw rows are not exactly paired: expected {len(expected)} nonvoid outcomes, got {len(seen)}")
    if len(image_ids)!=1: raise ValueError("raw rows mix provider images")

def report(a: argparse.Namespace) -> int:
    m=json.loads(Path(a.manifest).read_text()); validate_manifest(m); attempts=rows(Path(a.raw)); validate(m,attempts)
    raw=[r for r in attempts if not r.get("void")]
    for r in raw: r.pop("_line",None); r["instance_id"]=f"{r['task']}#{r['repetition']}"; r["resolved"]=bool(r["points"]==2 and not r["fail"]); r["failure_class"]="timeout" if r.get("timed_out") else "strict_protocol" if r.get("protocol_failure") else classify(str(r["terminal_output"]))
    normalized=Path(a.output).with_suffix(".jsonl"); normalized.write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in raw))
    paired={}
    for left,right in (("bash","guards-contracts"),("bash","fences"),("guards-contracts","fences")):
        done=subprocess.run([a.bashy,"stats","paired","--json","--arm","arm","--a",left,"--b",right,str(normalized)],text=True,capture_output=True)
        if done.returncode: raise ValueError(f"paired stats failed: {done.stderr.strip()}")
        try: paired[f"{right}-minus-{left}"]=json.loads(done.stdout)
        except json.JSONDecodeError as e: raise ValueError("paired stats did not return JSON") from e
    cps={}
    for arm in ARMS:
        own=[r for r in raw if r["arm"]==arm]; solved=sum(r["resolved"] for r in own); known=sum(r["tokens"] for r in own if isinstance(r["tokens"],int)); unknown=sum(r["tokens"] is None for r in own); cps[arm]={"solves":solved,"known_tokens_lower_bound":known,"unknown_token_rows":unknown,"tokens_per_solve_lower_bound":known/solved if solved else None}
    known_total=sum(r["tokens"] for r in raw if isinstance(r["tokens"],int)); unknown_total=sum(r["tokens"] is None for r in raw)
    for r in attempts: r.pop("_line",None)
    attempt_counts=Counter((r["task"],r["repetition"],r["arm"]) for r in attempts)
    evidence={"manifest":m,"attempt_accounting":{"total_attempts":len(attempts),"void_attempts":sum(bool(r.get("void")) for r in attempts),"valid_outcomes":len(raw),"retried_keys":sum(count>1 for count in attempt_counts.values()),"attempts_per_key":{f"{t}#{rep}/{arm}":count for (t,rep,arm),count in sorted(attempt_counts.items())}},"raw_rows":attempts,"paired":paired,"cost_per_solve":cps,"failure_taxonomy":dict(Counter(r["failure_class"] for r in raw)),"tokens":{"known_total_lower_bound":known_total,"unknown_rows":unknown_total},"pricing":m["pricing"]}
    Path(a.output).write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n"); print(a.output); return 0

def main() -> int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
    x=sub.add_parser("prepare"); [x.add_argument(*z,**kw) for z,kw in [(("--output",),{"required":True}),(("--candidate",),{"required":True}),(("--model",),{"required":True}),(("--seed",),{"required":True}),(("--k",),{"type":int,"default":3}),(("--budget-seconds",),{"type":int,"default":60}),(("--model-options",),{"default":"{}"})]]
    x=sub.add_parser("report"); [x.add_argument(*z,required=True) for z in (("--manifest",),("--raw",),("--output",),("--bashy",))]
    try: return prepare(p.parse_args()) if sys.argv[1]=="prepare" else report(p.parse_args())
    except (OSError,ValueError,json.JSONDecodeError) as e: print(f"bashsharp L2 experiment: {e}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())

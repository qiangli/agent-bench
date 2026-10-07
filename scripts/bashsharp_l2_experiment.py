#!/usr/bin/env python3
"""Fail-closed manifest and evidence gate for Sprint 381's paired L2 run."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = sorted(p.name for p in (ROOT / "packs/l2").iterdir() if (p / "task.yaml").is_file())
ARMS = ("bash", "guards-contracts", "fences")

def digest(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()
def json_digest(v: object) -> str: return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def tree_digest(p: Path) -> str:
    return hashlib.sha256("".join(f"{x.relative_to(p)}:{digest(x)}\n" for x in sorted(p.rglob("*")) if x.is_file()).encode()).hexdigest()
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
    out = Path(a.output); out.mkdir(parents=True, exist_ok=False)
    m = {"schema":"bashsharp-l2-v2", "story_id":"050a68a821a9", "pack":"l2", "tasks":[{"id":t,"task_sha256":digest(ROOT/"packs/l2"/t/"task.yaml"),"fixture_tree_sha256":tree_digest(ROOT/"packs/l2"/t/"fixture")} for t in TASKS], "k":a.k, "model":a.model, "agent":a.agent, "seed":a.seed, "model_options":opts, "model_options_sha256":json_digest(opts), "candidate_path":str(candidate), "candidate_sha256":digest(candidate), "budget_seconds":a.budget_seconds, "isolation":{"required":True,"method":"oci-or-separate-os-user","mounts":"fixture+candidate only","evaluator_outside_principal":True}, "arms":{"bash":{"dialect":"off","shell_args":[],"prelude":None},"guards-contracts":{"dialect":"on","shell_args":["--bashpp"],"prelude":"arms/guards-contracts.bsh"},"fences":{"dialect":"on","shell_args":["--bashpp"],"prelude":"arms/fences.bsh"}}, "pricing":{"usd":"unknown","reason":"dollars remain unknown without provider pricing evidence"}}
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
    need={"task","repetition","arm","points","fail","tokens","token_source","model","agent","candidate_sha256","fixture_tree_sha256","model_options_sha256","manifest_sha256","terminal_output"}
    expected={(x["id"],r,a) for x in m["tasks"] for r in range(1,m["k"]+1) for a in ARMS}; fixtures={x["id"]:x["fixture_tree_sha256"] for x in m["tasks"]}; seen=set()
    for index,row in enumerate(raw,1):
        row.setdefault("_line",index)
        missing=need-row.keys()
        if missing: raise ValueError(f"raw row {row['_line']} missing fields: {', '.join(sorted(missing))}")
        if row.get("void"): raise ValueError(f"raw row {row['_line']} is void; void attempts cannot enter paired evidence")
        key=(row["task"],row["repetition"],row["arm"])
        if not isinstance(row["repetition"],int) or key not in expected: raise ValueError(f"raw row {row['_line']} has invalid task/repetition/arm")
        if key in seen: raise ValueError(f"duplicate task/repetition/arm row: {key}")
        seen.add(key)
        if not isinstance(row["points"],(int,float)) or not isinstance(row["fail"],bool): raise ValueError(f"raw row {row['_line']} has invalid grade")
        if not isinstance(row["tokens"],int) or row["tokens"]<0 or row["token_source"] in ("",None,"unknown"): raise ValueError(f"raw row {row['_line']} has unknown/invalid token cost")
        if row["model"]!=m["model"] or row["agent"]!=m["agent"]: raise ValueError(f"raw row {row['_line']} mixes model or agent")
        if row["candidate_sha256"]!=m["candidate_sha256"] or row["fixture_tree_sha256"]!=fixtures[row["task"]]: raise ValueError(f"raw row {row['_line']} mixes candidate or fixture digest")
        if row["model_options_sha256"]!=m["model_options_sha256"] or row["manifest_sha256"]!=m["manifest_sha256"]: raise ValueError(f"raw row {row['_line']} has mixed model options or manifest")
    if seen!=expected: raise ValueError(f"raw rows are not exactly paired: expected {len(expected)}, got {len(seen)}")

def report(a: argparse.Namespace) -> int:
    m=json.loads(Path(a.manifest).read_text()); raw=rows(Path(a.raw)); validate(m,raw)
    for r in raw: r.pop("_line",None); r["instance_id"]=f"{r['task']}#{r['repetition']}"; r["resolved"]=bool(r["points"]==2 and not r["fail"]); r["failure_class"]=classify(str(r["terminal_output"]))
    normalized=Path(a.output).with_suffix(".jsonl"); normalized.write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in raw))
    paired={}
    for left,right in (("bash","guards-contracts"),("bash","fences"),("guards-contracts","fences")):
        done=subprocess.run([a.bashy,"stats","paired","--json","--arm","arm","--a",left,"--b",right,"--cost","tokens",str(normalized)],text=True,capture_output=True)
        if done.returncode: raise ValueError(f"paired stats failed: {done.stderr.strip()}")
        try: paired[f"{right}-minus-{left}"]=json.loads(done.stdout)
        except json.JSONDecodeError as e: raise ValueError("paired stats did not return JSON") from e
    cps={}
    for arm in ARMS:
        own=[r for r in raw if r["arm"]==arm]; solved=sum(r["resolved"] for r in own); total=sum(r["tokens"] for r in own); cps[arm]={"solves":solved,"tokens":total,"tokens_per_solve":total/solved if solved else None}
    evidence={"manifest":m,"raw_rows":raw,"paired":paired,"cost_per_solve":cps,"failure_taxonomy":dict(Counter(r["failure_class"] for r in raw)),"tokens":{"total":sum(r["tokens"] for r in raw),"unknown_rows":0},"pricing":m["pricing"]}
    Path(a.output).write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n"); print(a.output); return 0

def main() -> int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
    x=sub.add_parser("prepare"); [x.add_argument(*z,**kw) for z,kw in [(("--output",),{"required":True}),(("--candidate",),{"required":True}),(("--model",),{"required":True}),(("--agent",),{"required":True}),(("--seed",),{"required":True}),(("--k",),{"type":int,"default":3}),(("--budget-seconds",),{"type":int,"default":600}),(("--model-options",),{"default":"{}"})]]
    x=sub.add_parser("report"); [x.add_argument(*z,required=True) for z in (("--manifest",),("--raw",),("--output",),("--bashy",))]
    try: return prepare(p.parse_args()) if sys.argv[1]=="prepare" else report(p.parse_args())
    except (OSError,ValueError,json.JSONDecodeError) as e: print(f"bashsharp L2 experiment: {e}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())

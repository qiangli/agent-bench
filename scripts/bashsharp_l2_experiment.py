#!/usr/bin/env python3
"""Preparation and evidence gate for the Sprint 381 Bash# L2 experiment.

This intentionally does not launch an agent.  The existing agent-bench runner
owns fixture setup and grading; the remote executor supplies raw trial rows.
"""
from __future__ import annotations

import argparse, hashlib, json, os, subprocess, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = sorted(p.name for p in (ROOT / "packs/l2").iterdir() if (p / "task.yaml").is_file())
ARMS = ("bash", "guards-contracts", "fences")
FAILURES = ("command_not_found", "file_not_found", "module_not_found", "shell_syntax", "script_syntax", "other")

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def classify(text: str) -> str:
    value = text.lower()
    if "command not found" in value or "not recognized as an internal" in value: return "command_not_found"
    if "no such file or directory" in value or "cannot find the file" in value: return "file_not_found"
    if "modulenotfounderror" in value or "no module named" in value or "cannot find module" in value: return "module_not_found"
    if "syntax error" in value and ("shell" in value or "bash" in value): return "shell_syntax"
    if "syntaxerror" in value or "parse error" in value or "syntax error" in value: return "script_syntax"
    return "other"

def prepare(args: argparse.Namespace) -> int:
    candidate = Path(args.candidate).resolve()
    if not candidate.is_file() or not os.access(candidate, os.X_OK): raise ValueError("candidate must be a readable executable file")
    if not TASKS or len(TASKS) != 20: raise ValueError("packs/l2 must contain exactly 20 tasks")
    if args.k < 3: raise ValueError("K must be at least 3")
    output = Path(args.output); output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "bashsharp-l2-v1", "story_id": "050a68a821a9", "pack": "l2",
        "tasks": [{"id": task, "task_sha256": digest(ROOT / "packs/l2" / task / "task.yaml"),
                    "fixture_tree_sha256": hashlib.sha256("".join(sorted(digest(p) for p in (ROOT / "packs/l2" / task / "fixture").rglob("*") if p.is_file())).encode()).hexdigest()} for task in TASKS],
        "k": args.k, "model": args.model, "agent": args.agent, "seed": args.seed,
        "candidate_path": str(candidate), "candidate_sha256": digest(candidate),
        "isolation": {"required": True, "method": "oci-or-separate-os-user", "mounts": "fixture+candidate only", "evaluator_outside_principal": True},
        "arms": {"bash": {"dialect": "off", "shell_args": ["--posix"], "prelude": None},
                 "guards-contracts": {"dialect": "on", "shell_args": ["--bashpp"], "prelude": "arms/guards-contracts.bsh"},
                 "fences": {"dialect": "on", "shell_args": ["--bashpp"], "prelude": "arms/fences.bsh"}},
        "pricing": {"usd": "unknown", "reason": "report dollars only when provider metering/pricing is reliable"},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(output / "manifest.json")
    return 0

def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def report(args: argparse.Namespace) -> int:
    manifest, raw = json.loads(Path(args.manifest).read_text()), rows(Path(args.raw))
    expected = {(task["id"], repetition, arm) for task in manifest["tasks"] for repetition in range(1, manifest["k"] + 1) for arm in ARMS}
    actual = {(r.get("task"), r.get("repetition"), r.get("arm")) for r in raw if not r.get("void")}
    if actual != expected: raise ValueError(f"raw rows are not exactly paired: expected {len(expected)}, got {len(actual)}")
    for row in raw:
        row["instance_id"] = f"{row['task']}#{row['repetition']}"
        row["resolved"] = bool(row.get("points", 0) == 2 and not row.get("fail", False))
        row["failure_class"] = classify(str(row.get("terminal_output", "")))
        row["token_source"] = row.get("token_source", "unknown")
    normalized = Path(args.output).with_suffix(".jsonl")
    normalized.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in raw))
    paired = {}
    for baseline, compared in (("bash", "guards-contracts"), ("bash", "fences"), ("guards-contracts", "fences")):
        command = [args.bashy, "stats", "paired", "--json", "--arm", "arm", "--a", baseline, "--b", compared, "--cost", "tokens", str(normalized)]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode: raise ValueError(f"paired stats failed: {completed.stderr.strip()}")
        paired[f"{compared}-minus-{baseline}"] = json.loads(completed.stdout)
    output = {"manifest": manifest, "raw_rows": raw, "paired": paired,
              "failure_taxonomy": dict(Counter(row["failure_class"] for row in raw)),
              "tokens": {"total": sum(int(r.get("tokens", 0) or 0) for r in raw), "unknown_rows": sum(r["token_source"] == "unknown" for r in raw)},
              "pricing": manifest["pricing"]}
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(args.output)
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--output", required=True); p.add_argument("--candidate", required=True); p.add_argument("--model", required=True); p.add_argument("--agent", required=True); p.add_argument("--seed", required=True); p.add_argument("--k", type=int, default=3)
    p = sub.add_parser("report"); p.add_argument("--manifest", required=True); p.add_argument("--raw", required=True); p.add_argument("--output", required=True); p.add_argument("--bashy", required=True)
    try: return prepare(parser.parse_args()) if sys.argv[1] == "prepare" else report(parser.parse_args())
    except (OSError, ValueError, json.JSONDecodeError) as err: print(f"bashsharp L2 experiment: {err}", file=sys.stderr); return 2
if __name__ == "__main__": raise SystemExit(main())

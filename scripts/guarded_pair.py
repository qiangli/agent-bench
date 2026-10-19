#!/usr/bin/env python3
"""ONE paired skill-uptake measurement: the same agent, task, model, budget and
grader, SKILL=off, script, or yaml then SKILL=on; or the t7 config task with
SKILL=on in both arms and prefs.view=yaml versus json. Each arm runs through
guarded_live_arm.py (zero-model canary, quota, guard and skill-export
preflights before the request; quota, score, attributable usage and guard
evidence after it).

Fail closed between arms: if the first arm refused (a preflight) or failed any
check (usage capture included), the second is NOT launched and is reported
UNSCORED (not run). No retries: guarded_live_arm runs the DAG with ATTEMPTS=1.
Refuses to start while another bench vendor arm is live on this host.

Usage:
  guarded_pair.py --agent claude-opus5.5 --task t6-pdf-fact --model claude-opus-5-5 \\
      --evidence DIR [--bashy PATH] [--budget 100] [--order off,on]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guarded_live_arm as g

REPO = g.REPO
BUSY_RE = re.compile(r"guarded_live_arm\.py|guarded_pair\.py|claude_skill_probe\.py|/bench-arm\.|/s10g\.|"
                     r"dag run AGENT=")


def tree_sha(path: str) -> str:
    h = hashlib.sha256()
    for d, dirs, files in sorted(os.walk(path)):
        dirs.sort()
        for f in sorted(files):
            if f.endswith(".pyc"):
                continue
            p = os.path.join(d, f)
            h.update(os.path.relpath(p, path).encode() + b"\0" + open(p, "rb").read())
    return h.hexdigest()


def concurrent_runs(ps_text: str, own: set[int]) -> list[str]:
    out = []
    for line in ps_text.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and parts[0].isdigit() and int(parts[0]) not in own and BUSY_RE.search(parts[1]):
            out.append(line.strip()[:200])
    return out


def own_pids() -> set[int]:
    # Agent shells carry the entire invocation in their command line. Exclude
    # our full ancestry so BUSY_RE only catches a separate live bench run.
    rows = subprocess.run(["/bin/ps", "-axo", "pid=,ppid="], capture_output=True, text=True).stdout
    parents = {}
    for line in rows.splitlines():
        fields = line.split()
        if len(fields) == 2 and all(x.isdigit() for x in fields):
            parents[int(fields[0])] = int(fields[1])
    pids, p = set(), os.getpid()
    while p and p not in pids:
        pids.add(p)
        p = parents.get(p, 0)
    return pids


def pair(args, run_arm=None) -> dict:
    run_arm = run_arm or g.main
    ev = os.path.abspath(args.evidence)
    os.makedirs(ev, exist_ok=True)
    grader = os.path.join(REPO, "packs", args.pack, args.task, "grader")
    out: dict = {"agent": args.agent, "pack": args.pack, "task": args.task, "model": args.model,
                 "budget": args.budget, "quiet": args.quiet, "bashy": args.bashy,
                 "view_order": getattr(args, "view_order", None),
                 "grader_sha256": tree_sha(grader) if os.path.isdir(grader) else None,
                 "started": datetime.datetime.now().astimezone().isoformat(), "arms": [], "verdict": "UNSCORED"}
    ps = subprocess.run(["/bin/ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    busy = concurrent_runs(ps, own_pids())
    out["concurrent_runs"] = busy
    if busy:
        out["failures"] = ["another bench vendor runner is live; not launching"]
        return out
    stop = None
    view_order = getattr(args, "view_order", None)
    arms = [("on", view, f"view-{view}") for view in view_order] if view_order else [
        (skill, None, skill) for skill in args.order]
    for skill, view, arm in arms:
        if stop:
            out["arms"].append({"skill": skill, "reader_view": view, "verdict": "UNSCORED", "requests": 0,
                                "why": f"not run: previous arm stopped the pair ({stop})"})
            continue
        argv = ["--agent", args.agent, "--pack", args.pack, "--task", args.task, "--skill", skill,
                "--evidence", os.path.join(ev, arm), "--bashy", args.bashy, "--budget", str(args.budget),
                "--quiet", str(args.quiet), "--model", args.model]
        if view:
            argv += ["--reader-view", view]
        if getattr(args, "allow_unmeasured_bounded", False):
            argv.append("--allow-unmeasured-bounded")
        if args.tool:
            argv += ["--tool", args.tool]
        for comm in args.vendor_comm:
            argv += ["--vendor-comm", comm]
        rc = run_arm(argv)
        try:
            rep = json.load(open(os.path.join(ev, arm, "report.json")))
        except (OSError, ValueError):
            rep = {"verdict": "UNSCORED", "failures": ["no report.json"]}
        out["arms"].append({"skill": skill, "reader_view": view, "rc": rc, **{k: rep.get(k) for k in (
            "verdict", "score", "failures", "requests", "usage_total", "quota_before", "quota_after",
            "quota_before_read", "quota_after_read", "balance_before_usd", "balance_after_usd",
            "quota_policy",
            "balance_delta_usd", "native_route_budget_usd", "skill_preflight", "workspace_skill",
            "negative_control_before", "negative_control_after", "canary_before",
            "real_home_changed", "sandbox_denials", "wall_s")}})
        if rc != 0:
            stop = f"{arm} rc={rc} verdict={rep.get('verdict')}"
    out["verdict"] = "PAIRED" if all(a.get("rc") == 0 for a in out["arms"]) else "UNSCORED"
    out["finished"] = datetime.datetime.now().astimezone().isoformat()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--agent", required=True)
    ap.add_argument("--pack", default="skill-uptake")
    ap.add_argument("--task", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--bashy", default=shutil.which("bashy"))
    ap.add_argument("--budget", type=int, default=100)
    ap.add_argument("--quiet", type=int, default=20)
    ap.add_argument("--order", default="off,on")
    ap.add_argument("--view-order", help="compare reader prefs.view yaml,json with SKILL=on in both arms")
    ap.add_argument("--tool")
    ap.add_argument("--vendor-comm", action="append", default=[])
    ap.add_argument("--allow-unmeasured-bounded", action="store_true",
                    help="pass the explicit cached subscription quota exception to each arm")
    args = ap.parse_args(argv)
    args.bashy = os.path.abspath(args.bashy)
    args.order = args.order.split(",")
    if args.order not in (["off", "on"], ["script", "on"], ["yaml", "on"]):
        ap.error("--order must be off,on, script,on, or yaml,on")
    if args.view_order:
        args.view_order = args.view_order.split(",")
        if args.order != ["off", "on"] or sorted(args.view_order) != ["json", "yaml"]:
            ap.error("--view-order requires yaml,json or json,yaml and no --order override")
        if (args.pack, args.task) != ("skill-uptake", "t7-json-yaml"):
            ap.error("--view-order requires the skill-uptake/t7-json-yaml config task")
    out = pair(args)
    with open(os.path.join(os.path.abspath(args.evidence), "pair.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({"verdict": out["verdict"], "arms": [{k: a.get(k) for k in ("skill", "reader_view", "verdict", "score")}
                                                          for a in out["arms"]]}, indent=1))
    return 0 if out["verdict"] == "PAIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

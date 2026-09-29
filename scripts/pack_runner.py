#!/usr/bin/env python3
"""Common local scoring rules for agent-bench certificate packs.

This program deliberately owns pack discovery, grading adapters, verdicts, and
golden-set calibration.  DAG.md only drives sessions and calls this file, so a
pass line cannot drift between runner targets.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "packs"
KNOWN_PACKS = {"floor", "l1", "l2", "steer", "review", "manager", "judge", "l5"}


def task_dirs(pack: str) -> list[Path]:
    """Return task manifests; judge is one task rooted at its pack directory."""
    root = PACKS / pack
    if not root.is_dir() and pack not in KNOWN_PACKS:
        raise ValueError(f"unknown pack: {pack}")
    if not root.is_dir():
        return []
    if (root / "task.yaml").is_file():
        return [root]
    return sorted(p.parent for p in root.glob("*/task.yaml"))


def task_names(pack: str) -> list[str]:
    return [p.name if p != PACKS / pack else "calibration" for p in task_dirs(pack)]


def task_dir(pack: str, task: str) -> Path:
    for candidate in task_dirs(pack):
        name = candidate.name if candidate != PACKS / pack else "calibration"
        if name == task:
            return candidate
    raise ValueError(f"unknown task: {pack}/{task}")


def grade_command(pack: str, task: str, workspace: Path, fixture: Path) -> list[str]:
    """Return the task's published local grader command."""
    directory = task_dir(pack, task)
    if pack == "l1":
        return [sys.executable, str(PACKS / "l1/grader/grade.py"), str(workspace), str(fixture)]
    if pack == "review":
        return [sys.executable, str(PACKS / "review/grader/grade.py"), str(workspace), str(fixture)]
    if pack == "judge":
        return [sys.executable, str(directory / "grader/grade.py"), str(workspace), str(fixture)]
    grader = directory / "grader/grade.py"
    if grader.is_file():
        return [sys.executable, str(grader), str(workspace), str(fixture)]
    raise ValueError(f"{pack}/{task} has no command grader")


def grade(pack: str, task: str, workspace: Path, fixture: Path) -> dict:
    """Normalize every task grader to a runner result JSON object."""
    completed = subprocess.run(grade_command(pack, task, workspace, fixture), text=True,
                               capture_output=True, check=False)
    line = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    try:
        result = json.loads(line)
    except json.JSONDecodeError:
        return {"points": 0, "fail": True, "why": f"grader error: {completed.stderr.strip()[:160]}"}
    if pack == "judge":
        correct, total = int(result.get("correct", 0)), int(result.get("total", 20))
        return {"points": 2 if result.get("pass") else 0, "fail": False,
                "correct": correct, "total": total,
                "why": f"{correct}/{total} cases agree"}
    result.setdefault("points", 0)
    result.setdefault("fail", False)
    result.setdefault("why", "grader gave no reason")
    return result


def overlay(source: Path, destination: Path) -> None:
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            shutil.copy2(child, target)


def validate(pack: str) -> int:
    tasks = task_dirs(pack)
    if not tasks:
        print(f"SKIP {pack}: no task.yaml files")
        return 0
    rc = 0
    for directory in tasks:
        task = directory.name if directory != PACKS / pack else "calibration"
        fixture, reference = directory / "fixture", directory / "reference"
        if not fixture.is_dir() or not reference.is_dir():
            print(f"FAIL {pack}/{task}: fixture or reference is missing")
            rc = 1
            continue
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            overlay(fixture, work)
            # A few task contracts inspect history as well as files.  This is
            # the same fixture/reference commit boundary used by the DAG run.
            subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
            subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(work), "-c", "user.name=bench",
                            "-c", "user.email=bench@example.invalid", "commit", "-qm", "fixture"], check=True)
            untouched = grade(pack, task, work, fixture)
            overlay(reference, work)
            subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(work), "-c", "user.name=bench",
                            "-c", "user.email=bench@example.invalid", "commit", "-qm", "reference"], check=True)
            answer = grade(pack, task, work, fixture)
        # An untouched fixture must not pass.  Some one-shot graders call an
        # incorrect answer a task-local failure; that is not a runner hard-rule.
        good = untouched.get("points") == 0 and answer.get("points") == 2 and not answer.get("fail")
        print(("ok  " if good else "FAIL") + f" {pack}/{task} fixture={untouched.get('points')} reference={answer.get('points')}")
        rc |= not good
    return int(rc)


def read_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not row.get("void"):
            rows.append(row)
    return rows


def certificate(pack: str, rows: list[dict], agent: str, k: int) -> tuple[bool, str, float, list[str]]:
    tasks = [f"{pack}/{name}" for name in task_names(pack)]
    mine = [row for row in rows if row.get("agent") == agent]
    missing = [f"{task}({len([r for r in mine if r.get('task') == task])}/{k})" for task in tasks if len([r for r in mine if r.get("task") == task]) < k]
    hard = [row for row in mine if row.get("fail")]
    if pack == "judge":
        agreement = min((int(row.get("correct", 0)) for row in mine if row.get("task") == tasks[0]), default=0)
        passed = not missing and not hard and agreement >= 18
        return passed, f"agreement {agreement}/20", round(10 * agreement / 20, 1), missing
    per = [min((int(row.get("points", 0)) for row in mine if row.get("task") == task), default=0) for task in tasks]
    score = round(10 * sum(per) / (2 * len(tasks)), 1) if tasks else 0.0
    if pack == "l1":
        passed = not missing and not hard and sum(point == 2 for point in per) >= 18
        return passed, f"{sum(point == 2 for point in per)}/20 tasks", score, missing
    if pack == "review":
        seeded = [row for row in mine if row.get("outcome") in ("caught", "missed")]
        clean = [row for row in mine if row.get("outcome") in ("approved", "false-alarm")]
        caught = sum(row.get("outcome") == "caught" for row in seeded)
        alarms = sum(row.get("outcome") == "false-alarm" for row in clean)
        passed = not missing and not hard and caught >= 12 and alarms == 0
        return passed, f"recall {caught}/14, false alarms {alarms}/6", score, missing
    passed = not missing and not hard and score >= 6.0
    return passed, f"score {score}/10", score, missing


def verdict(path: Path, pack: str, agent: str, k: int) -> int:
    rows = read_rows(path)
    agents = sorted({str(row.get("agent")) for row in rows}) if agent == "all" else [agent]
    for name in agents:
        passed, detail, _score, missing = certificate(pack, rows, name, k)
        print(f"{name} [{pack}]: {'PASS' if passed else 'FAIL'}  {detail}")
        if missing:
            print("   INCOMPLETE — missing runs: " + ", ".join(missing))
    return 0


def record(path: Path, agent: str, task: str, run: int, secs: int, ended: str,
           steered: bool, graded: str) -> int:
    try:
        result = json.loads(graded)
    except json.JSONDecodeError:
        result = {"points": 0, "fail": True, "why": "grader error: " + graded[:200]}
    row = {"agent": agent, "task": task, "run": run, "secs": secs, "ended": ended,
           "steered": steered, **result}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row) + "\n")
    print(f"  {agent} {task}#{run}: {row['points']} pts{' FAIL' if row['fail'] else ''} ({ended}, {secs}s) {row['why']}")
    return 0


# golden.txt accepts either the legacy two columns (agent band), or a pack
# column: agent band pack.  A row without a pack applies to every pack.
MIN_BAND = {"l1": 1, "l2": 2, "steer": 3, "manager": 4, "review": 4, "judge": 5, "l5": 5}


def calibrate(path: Path, golden: Path, pack: str, k: int) -> int:
    if pack not in MIN_BAND:
        print(f"DATASET NOT APPLICABLE: {pack} has no certificate calibration rule")
        return 0
    rows = read_rows(path)
    failures, incomplete = [], []
    for line in golden.read_text().splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("#") or len(fields) < 2:
            continue
        if len(fields) >= 3 and fields[2] != pack:
            continue
        agent, band = fields[0], int(fields[1])
        mine = [row for row in rows if row.get("agent") == agent]
        if not mine:
            incomplete.append(agent)
            continue
        passed, detail, _score, missing = certificate(pack, rows, agent, k)
        if missing:
            incomplete.append(agent)
            continue
        expected = band >= MIN_BAND[pack]
        print(f"{agent} [{pack}]: {'PASS' if passed else 'FAIL'} ({detail}); expected {'PASS' if expected else 'FAIL'}")
        if passed != expected:
            failures.append(agent)
    if failures:
        print("DATASET INVALID: " + ", ".join(failures))
    elif incomplete:
        print("DATASET NOT YET CALIBRATED: incomplete " + ", ".join(incomplete))
    else:
        print(f"DATASET VALID for {pack}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("tasks", "validate"):
        p = sub.add_parser(name); p.add_argument("--pack", required=True)
    p = sub.add_parser("path"); p.add_argument("--pack", required=True); p.add_argument("--task", required=True)
    p = sub.add_parser("grade"); p.add_argument("--pack", required=True); p.add_argument("--task", required=True); p.add_argument("--workspace", required=True); p.add_argument("--fixture", required=True)
    p = sub.add_parser("record"); p.add_argument("--results", required=True); p.add_argument("--agent", required=True); p.add_argument("--task", required=True); p.add_argument("--run", type=int, required=True); p.add_argument("--secs", type=int, required=True); p.add_argument("--ended", required=True); p.add_argument("--steered", action="store_true"); p.add_argument("--graded", required=True)
    for name in ("verdict", "calibrate"):
        p = sub.add_parser(name); p.add_argument("--results", required=True); p.add_argument("--pack", required=True); p.add_argument("--agent", default="all" if name == "verdict" else ""); p.add_argument("--k", type=int, default=3)
        if name == "calibrate": p.add_argument("--golden", default="golden.txt")
    args = parser.parse_args()
    try:
        if args.command == "tasks": print("\n".join(task_names(args.pack)))
        elif args.command == "path": print(task_dir(args.pack, args.task))
        elif args.command == "validate": return validate(args.pack)
        elif args.command == "grade": print(json.dumps(grade(args.pack, args.task, Path(args.workspace), Path(args.fixture))))
        elif args.command == "record": return record(Path(args.results), args.agent, args.task, args.run, args.secs, args.ended, args.steered, args.graded)
        elif args.command == "verdict": return verdict(Path(args.results), args.pack, args.agent, args.k)
        else: return calibrate(Path(args.results), Path(args.golden), args.pack, args.k)
    except (OSError, ValueError) as error:
        print(f"pack runner: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

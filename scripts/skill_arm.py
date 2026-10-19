#!/usr/bin/env python3
"""skill-uptake arm selector: prepare one workspace for one SKILL= arm.

  off     no-skill baseline (nothing exported, default help format).
  on      prose skill folder: `bashy skill export bashy --repo --tool TOOL`.
  yaml    single-record YAML skill: `skill export --to WS/.agents/skills --yaml`.
  script  a task-specific command recipe in AGENTS.md and NO prose export.
          The launch env keeps the format marker for transcript attribution.

Unknown arms fail loudly rather than silently running the wrong arm. An
export that exits 0 but writes nothing (a tool with no `integration:` block:
codex) also fails, so a no-skill run is never labelled skill-on.

Claude: bashy's claude tool declares no `integration:` block either, so
`--tool claude` fails ("declares no integration"; a product gap in bashy, not
worked around here). Claude does read project skills from
`<cwd>/.claude/skills/<name>/SKILL.md`, and plain `skill export --repo` (no
--tool) writes exactly that folder when the repo has a `.claude` dir, beside
the standard `.agents/skills`. So for a tool in PROJECT_SKILL_ROOTS the on arm
creates that dir, exports with plain `--repo`, and fails unless the vendor's
own SKILL.md landed in the workspace. Nothing is written outside it.
The exported skill is committed to the workspace. Prints the KEY=VALUE lines
the agent must be launched with.

The runner calls this under the arm's isolated environment (scripts/arm_home.py),
so bashy's own state from the export lands in the arm HOME, not the operator's.

Usage: skill_arm.py --workspace WS --tool TOOL --arm off|on|yaml|script --task TASK
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

ARMS = ("off", "on", "yaml", "script")
BENCH_GIT = ["-c", "user.name=bench", "-c", "user.email=bench@example.invalid"]


# Tools with no bashy integration block whose CLI reads a project skill root
# that `skill export --repo` fills once the vendor dir exists: tool -> (dir to
# create, SKILL.md path the vendor reads, relative to the workspace).
PROJECT_SKILL_ROOTS = {"claude": (".claude", ".claude/skills/bashy/SKILL.md")}

# A script arm has actual executable guidance. This t6 recipe is derived from
# the same lens command named in the portable bashy skill, without embedding
# the answer or writing the task artifact for the agent.
SCRIPT_RECIPES = {
    "t6-pdf-fact": "# Bashy command recipe\n\nRun this command to read the PDF, then write the requested FACT.md yourself:\n\n```sh\nbashy lens -t md invoice.pdf\n```\n",
}


class ArmError(RuntimeError):
    pass


def _git(ws: str, *args: str) -> str:
    return subprocess.run(["git", "-C", ws, *args], check=True, text=True, capture_output=True).stdout


def select(ws: str, tool: str, arm: str, bashy: str = "bashy", task: str | None = None) -> list[str]:
    if arm not in ARMS:
        raise ArmError(f"unknown skill arm {arm!r} (want off/on/yaml/script)")
    if arm == "off":
        return []
    if arm == "script":
        if task not in SCRIPT_RECIPES:
            raise ArmError(f"no script recipe for task {task!r}")
        path = os.path.join(ws, "AGENTS.md")
        if os.path.lexists(path):
            raise ArmError("script recipe would overwrite AGENTS.md")
        with open(path, "x", encoding="utf-8") as fh:
            fh.write(SCRIPT_RECIPES[task])
        _git(ws, "add", "AGENTS.md")
        _git(ws, *BENCH_GIT, "commit", "-qm", "skill-script")
        return ["BASHY_HELP_FORMAT=script"]
    vendor = PROJECT_SKILL_ROOTS.get(tool) if arm == "on" else None
    if vendor:
        os.makedirs(os.path.join(ws, vendor[0]), exist_ok=True)
        cmd = [bashy, "skill", "export", "bashy", "--repo"]
    elif arm == "on":
        cmd = [bashy, "skill", "export", "bashy", "--repo", "--tool", tool]
    else:
        cmd = [bashy, "skill", "export", "bashy", "--to", f"{ws}/.agents/skills", "--yaml"]
    done = subprocess.run(cmd, cwd=ws, text=True, capture_output=True)
    out = (done.stderr + done.stdout).strip()
    if done.returncode:
        raise ArmError(f"{arm} export rc={done.returncode}: {out[:300]}")
    if not _git(ws, "status", "--porcelain").strip():
        raise ArmError(f"{arm} export wrote nothing (tool {tool!r} declares no integration: {out[:300]})")
    if vendor and not os.path.isfile(os.path.join(ws, vendor[1])):
        raise ArmError(f"on export did not write {vendor[1]}, the skill {tool} reads: {out[:300]}")
    if arm == "yaml" and not os.path.isfile(os.path.join(ws, ".agents/skills/bashy.yaml")):
        raise ArmError(f"yaml export did not write .agents/skills/bashy.yaml: {out[:300]}")
    _git(ws, "add", "-A")
    _git(ws, *BENCH_GIT, "commit", "-qm", "skill" if arm == "on" else "skill-yaml")
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="skill-uptake arm selector")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--task")
    args = ap.parse_args(argv)
    try:
        for line in select(args.workspace, args.tool, args.arm, task=args.task):
            print(line)
    except (ArmError, OSError, subprocess.CalledProcessError) as error:
        print(f"SKILL EXPORT FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

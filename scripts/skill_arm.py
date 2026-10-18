#!/usr/bin/env python3
"""skill-uptake arm selector: prepare one workspace for one SKILL= arm.

  off     no-skill baseline (nothing exported, default help format).
  on      prose skill folder: `bashy skill export bashy --repo --tool TOOL`.
  yaml    single-record YAML skill: `skill export --to WS/.agents/skills --yaml`.
  script  script-format help and NO prose export (BASHY_HELP_FORMAT=script
          alone still exports prose, so this arm must not export; the env
          marker is the grader's attribution signal).

Unknown arms fail loudly rather than silently running the wrong arm. An
export that exits 0 but writes nothing (a tool with no `integration:` block:
codex, claude) also fails, so a no-skill run is never labelled skill-on.
The exported skill is committed to the workspace. Prints the KEY=VALUE lines
the agent must be launched with.

The runner calls this under the arm's isolated environment (scripts/arm_home.py),
so bashy's own state from the export lands in the arm HOME, not the operator's.

Usage: skill_arm.py --workspace WS --tool TOOL --arm off|on|yaml|script
"""
from __future__ import annotations

import argparse
import subprocess
import sys

ARMS = ("off", "on", "yaml", "script")
BENCH_GIT = ["-c", "user.name=bench", "-c", "user.email=bench@example.invalid"]


class ArmError(RuntimeError):
    pass


def _git(ws: str, *args: str) -> str:
    return subprocess.run(["git", "-C", ws, *args], check=True, text=True, capture_output=True).stdout


def select(ws: str, tool: str, arm: str, bashy: str = "bashy") -> list[str]:
    if arm not in ARMS:
        raise ArmError(f"unknown skill arm {arm!r} (want off/on/yaml/script)")
    if arm == "off":
        return []
    if arm == "script":
        return ["BASHY_HELP_FORMAT=script"]
    if arm == "on":
        cmd = [bashy, "skill", "export", "bashy", "--repo", "--tool", tool]
    else:
        cmd = [bashy, "skill", "export", "bashy", "--to", f"{ws}/.agents/skills", "--yaml", "--tool", tool]
    done = subprocess.run(cmd, cwd=ws, text=True, capture_output=True)
    out = (done.stderr + done.stdout).strip()
    if done.returncode:
        raise ArmError(f"{arm} export rc={done.returncode}: {out[:300]}")
    if not _git(ws, "status", "--porcelain").strip():
        raise ArmError(f"{arm} export wrote nothing (tool {tool!r} declares no integration: {out[:300]})")
    _git(ws, "add", "-A")
    _git(ws, *BENCH_GIT, "commit", "-qm", "skill" if arm == "on" else "skill-yaml")
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="skill-uptake arm selector")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--arm", required=True)
    args = ap.parse_args(argv)
    try:
        for line in select(args.workspace, args.tool, args.arm):
            print(line)
    except (ArmError, OSError, subprocess.CalledProcessError) as error:
        print(f"SKILL EXPORT FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

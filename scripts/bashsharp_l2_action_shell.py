#!/usr/bin/env python3
"""Shell adapter used at the agent tool boundary by the three L2 arms."""
from __future__ import annotations
import os, subprocess, sys, tempfile
from pathlib import Path
PRELUDE = {"guards-contracts": "guards-contracts.bsh", "fences": "fences.bsh"}
def main(argv: list[str]) -> int:
    arm, candidate = os.environ.get("BASHY_EXPERIMENT_ARM", ""), os.environ.get("BASHY_EXPERIMENT_CANDIDATE", "")
    assets = Path(os.environ.get("BASHY_EXPERIMENT_ASSETS", ""))
    if arm not in ("bash", *PRELUDE) or not candidate or not Path(candidate).is_file(): raise ValueError("set a valid BASHY_EXPERIMENT_ARM and BASHY_EXPERIMENT_CANDIDATE")
    if len(argv) != 2 or argv[0] != "-c": raise ValueError("experiment action shell accepts exactly: -c SCRIPT")
    # Plain Bash is the candidate's ordinary Bash mode.  POSIX mode would be
    # a fourth, semantically different baseline rather than a fair control.
    if arm == "bash": return subprocess.run([candidate, "-c", argv[1]], check=False).returncode
    prelude = assets / PRELUDE[arm]
    if not prelude.is_file(): raise ValueError("experiment arm prelude is missing")
    with tempfile.NamedTemporaryFile(mode="w", prefix="bashsharp-l2-action-", suffix=".bsh", delete=False) as action:
        action.write(argv[1]); action_path = action.name
    try:
        return subprocess.run([candidate, "--bashpp", str(prelude)], env=dict(os.environ, BASHY_EXPERIMENT_ACTION=action_path), check=False).returncode
    finally: Path(action_path).unlink(missing_ok=True)
if __name__ == "__main__":
    try: raise SystemExit(main(sys.argv[1:]))
    except ValueError as error: print(f"bashsharp L2 action shell: {error}", file=sys.stderr); raise SystemExit(2)

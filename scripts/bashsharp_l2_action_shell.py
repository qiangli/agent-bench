#!/usr/bin/env python3
"""Shell adapter used at the agent tool boundary by the three L2 arms."""
from __future__ import annotations
import os, shlex, subprocess, sys, tempfile
from pathlib import Path
PRELUDE = {"guards-contracts": "guards-contracts.bsh", "fences": "fences.bsh"}
def main(argv: list[str]) -> int:
    arm, candidate = os.environ.get("BASHY_EXPERIMENT_ARM", ""), os.environ.get("BASHY_EXPERIMENT_CANDIDATE", "")
    assets = Path(os.environ.get("BASHY_EXPERIMENT_ASSETS", ""))
    if arm not in ("bash", *PRELUDE) or not candidate or not Path(candidate).is_file(): raise ValueError("set a valid BASHY_EXPERIMENT_ARM and BASHY_EXPERIMENT_CANDIDATE")
    if not argv: raise ValueError("experiment action shell requires a command or script")
    shell_command = len(argv) == 2 and argv[0] in ("-c", "-lc")
    script = argv[1] if shell_command else "exec " + shlex.join([candidate, *argv])
    # Plain Bash is the candidate's ordinary Bash mode.  POSIX mode would be
    # a fourth, semantically different baseline rather than a fair control.
    if arm == "bash":
        command = [candidate, "--no-bashpp", "-c", script] if shell_command else [candidate, "--no-bashpp", *argv]
        return subprocess.run(command, check=False).returncode
    prelude = assets / PRELUDE[arm]
    if not prelude.is_file(): raise ValueError("experiment arm prelude is missing")
    with tempfile.NamedTemporaryFile(mode="w", prefix="bashsharp-l2-action-", suffix=".bsh", delete=False) as action:
        action.write(script); action_path = action.name
    fence_dir = tempfile.TemporaryDirectory(prefix="bashsharp-l2-fence-")
    try:
        environment = dict(
            os.environ,
            BASHY_EXPERIMENT_ACTION=action_path,
            BASHY_EXPERIMENT_FENCE_STDOUT=str(Path(fence_dir.name) / "stdout"),
            BASHY_EXPERIMENT_FENCE_STATUS=str(Path(fence_dir.name) / "status"),
        )
        return subprocess.run([candidate, "--bashpp", str(prelude)], env=environment, check=False).returncode
    finally:
        Path(action_path).unlink(missing_ok=True)
        fence_dir.cleanup()
if __name__ == "__main__":
    try: raise SystemExit(main(sys.argv[1:]))
    except ValueError as error: print(f"bashsharp L2 action shell: {error}", file=sys.stderr); raise SystemExit(2)

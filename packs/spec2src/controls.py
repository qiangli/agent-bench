#!/usr/bin/env python3
"""Run the null control once and the reference control three times."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PACK = Path(__file__).resolve().parent
TASK = PACK / "t1-form"


def grade(workspace: Path, snapshot: Path) -> dict:
    env = {**os.environ, "SPEC2SRC_SNAPSHOT_PATH": str(snapshot)}
    done = subprocess.run([sys.executable, str(TASK / "grader" / "grade.py"),
                           str(workspace), str(TASK / "fixture")],
                          env=env, capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


def main() -> int:
    passed = True
    with tempfile.TemporaryDirectory(prefix="spec2src-controls-") as temporary:
        root = Path(temporary)
        for name, number in [("null", 0), *[("reference", n) for n in range(1, 4)]]:
            workspace = root / f"{name}-{number}"
            shutil.copytree(TASK / "fixture", workspace)
            if name == "reference":
                subprocess.run([sys.executable, str(TASK / "reference" / "solve.py"),
                                str(workspace)], check=True)
            result = grade(workspace, root / f"{name}-{number}.tar.gz")
            valid = (result["verdict"] == "FAIL" if name == "null"
                     else result["verdict"] == "PASS")
            passed &= valid
            print(json.dumps({"control": name, "run": number,
                              "verdict": result["verdict"], "layers": result["layers"],
                              "snapshot_sha256": result["snapshot_sha256"],
                              "task_sha256": result["task_sha256"], "ok": valid}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

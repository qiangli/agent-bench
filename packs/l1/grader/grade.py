#!/usr/bin/env python3
"""Shared L1 answer grader. Usage: grade.py WORKDIR FIXTURE_DIR."""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path


def result(ok: bool, why: str) -> None:
    print(json.dumps({"points": 2 if ok else 0, "fail": not ok, "why": why}))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: grade.py WORKDIR FIXTURE_DIR", file=sys.stderr)
        return 2
    workdir = Path(sys.argv[1])
    task = Path(sys.argv[2]).resolve().parent.name
    key_path = Path(__file__).resolve().with_name("answers.json")
    key = json.loads(key_path.read_text(encoding="utf-8"))[task]
    answer_path = workdir / "ANSWER.txt"
    if not answer_path.is_file():
        result(False, "ANSWER.txt is missing")
        return 0
    answer = answer_path.read_text(encoding="utf-8").strip()
    if key["type"] == "exact":
        ok = answer.casefold() == key["value"].casefold()
    elif key["type"] == "number":
        try:
            ok = math.isclose(float(answer), key["value"], abs_tol=key["tolerance"], rel_tol=0)
        except ValueError:
            ok = False
    elif key["type"] == "regex":
        ok = re.fullmatch(key["pattern"], answer, flags=re.IGNORECASE) is not None
    else:
        raise ValueError("unknown key type")
    result(ok, "correct" if ok else "answer did not match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

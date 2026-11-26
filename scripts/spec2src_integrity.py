#!/usr/bin/env python3
"""Preserve the grade record while applying the answer-key hard rule."""
import json
import sys


row = json.loads(sys.argv[1])
row.update(points=0, fail=True, verdict="FAIL", classification="integrity",
           why="read the answer key", integrity_failed=True)
print(json.dumps(row))

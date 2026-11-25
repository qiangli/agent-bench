---
id: cd3092bf0b83
kind: task
title: 'B1 Phase B harness: spec-only workspace, isolated agent run, snapshot + grade with conform'
seq: 763
status: todo
priority: p2
labels:
    - conform
created: 2026-11-25T21:22:19.575687Z
sprint: 722
sprint_id: ffc7a05d-4229-598a-8834-4c1212246274
sprint_title: 'dhnt/conform, then: does the spec reproduce the app?'
---

agent-bench pack packs/shapeware/t5-spec-to-source: setup builds a fresh workspace with only CONTRACT.md, SKILL.md, features.yaml and TASK.md (sha256 recorded); runs one subject binding with a 30 min cap; snapshots + hashes the workspace at agent end; grades the snapshot in a separate sandbox through bashy conform (visible contract, hidden cases supplied at grade time from outside the workspace, UI inventory + interactions + JSON API); writes the per-run record (verdicts per layer + accounting per protocol). Controls: reference x3, null candidate. Venue: gate host lane.

Protocol: umbrella docs/conform-phase-b-protocol.md (fixed before runs). Depends on Phase A (A3-A7).

## Conductor design (2026-11-25, after Phase A)

Interface (public pack, private grading):

- Pack `packs/spec2src`, task `t1-form`.
- `fixture/`: CONTRACT.md, SKILL.md, features.yaml and examples/contact.json, copied
  byte-for-byte from bashy `examples/desk/form` at the umbrella pin (record the
  sha256 of each in task.yaml), plus TASK.md (below).
- TASK.md (fixed text, the same for every subject): "Build the `form` app described
  by CONTRACT.md, SKILL.md and features.yaml in this directory. Deliver source and an
  executable POSIX-sh launcher `./form` at the workspace root. `./form` is run on Linux
  x86_64 with Go 1.27, Python 3.12, Node 18, sh, curl and jq, with no network and no
  bashy. It may compile on first use, and dependencies must be standard library only
  or vendored here. Your work is judged by its behaviour: the contract's commands and
  the page it serves." Do not mention the hidden cases, the grader or conform.
- `grader/grade.py`:
  - Make a tar.gz snapshot of the workspace (excluding .git) and record its sha256.
  - Run `$SPEC2SRC_GRADE_CMD <snapshot.tar.gz>`. If it is unset, the result is
    INCONCLUSIVE with the reason "no grade venue".
  - Parse its stdout JSON: {"layers":{"cli":V,"hidden":V,"ui":V},"verdict":V,
    "results":[{"layer","name","status","detail"}],"venue":{...}}.
  - Emit the pack result: points 2 when the verdict is PASS, else 0; fail on
    FAIL; plus metrics = verdict, per-layer verdicts, visible and hidden pass rates,
    the snapshot sha256 and the TASK.md sha256.
  - The grader never prints hidden case content.
- `reference/solve.py` (controls only): write a `./form` that execs
  "$SPEC2SRC_REFERENCE_FORM" with "$@". It is used for the reference x3 and
  validate runs.
- Null control: the untouched fixture must grade FAIL (there is no ./form).
- Self-check: a fake SPEC2SRC_GRADE_CMD in the pack's tests that returns canned
  JSON, covering PASS, FAIL, INCONCLUSIVE and the unset command.
  `python3 packs/spec2src/selfcheck.py` (or the existing self-check wiring) runs
  them offline.
- Wire `PACK=spec2src` into the existing `bashy dag run/bench` path. Any env var
  named SPEC2SRC_* must reach the grader. No host names, no paths under a home
  directory, no hidden data in this repo.
- Do not touch packs/shapeware.

Verify: the pack self-check and `python3 -m pytest scripts/test_pack_runner.py` (or
the repo's test entry) pass. Commit trailers Sprint: #722 / Story: #<seq> /
Story-ID: cd3092bf0b83. Keep it to about 40 minutes.


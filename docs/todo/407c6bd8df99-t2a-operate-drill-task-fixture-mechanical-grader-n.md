---
id: 407c6bd8df99
kind: feature
title: 'T2a operate drill task: fixture, mechanical grader, no-model control and selfcheck (packs/spec2src/t2-operate)'
seq: 765
status: todo
priority: p0
labels:
    - spec2src
created: 2026-11-26T14:41:37.61731Z
sprint: 731
sprint_id: 88c254ad-f4a4-5c54-a0fd-ac469894c684
sprint_title: Shapeware workflow standard, proven by the full trip on form
---

Part of umbrella Sprint 731 story 22ae0904d5a0 (T2, the operate drill). Plan: umbrella `docs/plan-reverse-sdlc-workflow.md`, "The full trip". A subject at a low band gets a built app folder and must carry out its lifecycle steps exactly as `dag.md` writes them. This story builds the task and its mechanical grader. It runs no model.

## Code inspected by the conductor (agent-bench main, 2026-11-26)
- `packs/spec2src/t2-operate/fixture/` is already committed: a `form` build that passed the T1 grade (Python: `form`, `form.py`, `build.sh`), the spec files, the spec's `dag.md`, and the subject's `TASK.md`. Do not change any fixture file.
- `scripts/pack_runner.py`: `grade_command` runs `<task>/grader/grade.py WORKSPACE FIXTURE`; `certificate` has a `spec2src` branch.
- `DAG.md` task `run`: for `PACK=spec2src` it calls `specgrade`, which passes `BENCH_SPEC2SRC_ARM_DIR` (the arm directory) to the grader. The subject's HOME is `<arm dir>/<HOME_NAME>` (`scripts/arm_home.py`, constant `HOME_NAME`).
- `packs/spec2src/t1-form/` (`task.yaml`, `grader/grade.py`) and `packs/spec2src/selfcheck.py`: the shapes to follow.

## Change
1. `packs/spec2src/t2-operate/task.yaml`, in the shape of `t1-form/task.yaml`: id `spec2src/t2-operate`, a sha256 line for every fixture file, `budget: {max_runtime: 15m}`.
2. `packs/spec2src/t2-operate/grader/grade.py WORKSPACE FIXTURE`, standard library only. It prints one JSON object on one line with `verdict` (`PASS`, `FAIL` or `INCONCLUSIVE`), `layers` (one verdict per check below, by these names), `points` (2 for PASS, else 0), `fail`, `why` (the first failing check and a short reason), `void` (false), and `report` (the parsed `report.txt`, or null). Checks:
   - `protected`: every file of FIXTURE exists in WORKSPACE with the same bytes. FAIL names the first changed or missing file. New files are allowed.
   - `install`: `<HOME>/.local/bin/form` is a regular executable file, where HOME is `<BENCH_SPEC2SRC_ARM_DIR>/<HOME_NAME>`. If `BENCH_SPEC2SRC_ARM_DIR` is not set, use the `HOME` of the grader's environment.
   - `contract`: the contract passes against the installed app. Copy FIXTURE's `CONTRACT.md` and `examples/` to a new temporary directory and run there `conform run CONTRACT.md --path <HOME>/.local/bin --fresh-home --timeout 120s --json`, with `DISPLAY` and `WAYLAND_DISPLAY` removed from the environment and a 600-second limit. PASS when the exit status is 0 and every result has status `PASS`. When `conform` is not on the PATH: INCONCLUSIVE.
   - `run`: `answer.json` in WORKSPACE holds one JSON object with `"schema_version": "bashy-form-v1"`, `"id": "drill-1"`, `"status": "pending"` and a `url` string.
   - `serve`: `page.html` in WORKSPACE contains the label of every field of `examples/contact.json`.
   The verdict is FAIL when any check fails, else INCONCLUSIVE when `contract` is INCONCLUSIVE, else PASS. `report.txt` is recorded and never decides the verdict.
3. `packs/spec2src/t2-operate/reference/operate.sh WORKSPACE`: carries out the task with no model, in plain `sh`: extract each step's code block from `dag.md` and run it from WORKSPACE (`build`, `test`, `install`, `run` with the task's `ARGS` into `answer.json`, `serve` in the background, read the `url` from `answer.json`, `curl` it into `page.html`, stop `serve` with TERM), and write `report.txt`. It uses the HOME it is given. This is the drill's control: the steps need no model.
4. `packs/spec2src/t2-operate/selfcheck.py`, offline, with a temporary HOME and a stub `conform` on the PATH that prints `[{"name":"F-01","status":"PASS","detail":"ok"}]` and exits 0 (the real judge is not available in tests). Cases: the untouched fixture FAILs (`install`); a workspace taken through `reference/operate.sh` PASSes every check; the same workspace with one byte changed in `dag.md` FAILs `protected`; with `answer.json` removed it FAILs `run`; with no `conform` on the PATH it is INCONCLUSIVE; the digests in `task.yaml` match the fixture. The reference run starts the fixture's Python server on the loopback address; the selfcheck must stop every process it started and remove its temporary directories (use `scripts/reap.py` on them at the end).
5. `scripts/pack_runner.py`: only if needed so that `python3 scripts/pack_runner.py grade --pack spec2src --task t2-operate --workspace W --fixture F` returns the grader's object and `validate` still passes; say in the commit message what you changed and why. Do not change `DAG.md`.
6. One paragraph in `packs/spec2src/README.md` describing the task, its checks and its control.

## Acceptance
- `python3 packs/spec2src/t2-operate/selfcheck.py` prints ok and exits 0 on macOS, and leaves no process and no temporary directory behind.
- `python3 packs/spec2src/selfcheck.py` and `python3 -m unittest discover -s scripts -p 'test_*.py'` still pass.
- These are the targeted tests of this story and may run where you work. Do not run `bashy dag dry`, `bashy dag run` or any drill, and do not start any model session.

## Constraints
- Touch only `packs/spec2src/t2-operate/` (not `fixture/`), `packs/spec2src/README.md`, and `scripts/pack_runner.py` when point 5 requires it.
- Public repository: no host names, logins, addresses or home paths.
- Commit on your work branch with trailers `Sprint: #731`, `Story:` and `Story-ID:` for this story, and `Agent:` with your registered name. Record the verify commands and their results before you submit. Do not push to main; the conductor gates and merges.

# spec2src: form from its public spec

`t1-form/fixture/` is the complete initial subject workspace. Its five files
are pinned in `task.yaml`; the four source documents are copied byte for byte
from the pinned bashy `examples/desk/form`. The subject writes source and an
executable `./form` launcher. The runner starts this pack without Git metadata
in the subject workspace and caps the agent session at 30 minutes.

The grader archives the workspace (excluding `.git`), records its SHA-256, and
passes the archive to `SPEC2SRC_GRADE_CMD` as its final argument. That command
runs the private conform checks in the separate grade sandbox and returns one
JSON object with `layers`, `verdict`, `results`, and `venue`. The adapter emits
only layer verdicts and aggregate rates. It does not copy case details into
the run record. Set `SPEC2SRC_SNAPSHOT_PATH` to retain the archive in direct
grader calls; DAG runs retain it automatically alongside their logs. Caller
`SPEC2SRC_*` variables pass through to the grader and grade command.

On the gate lane, run `python3 packs/spec2src/controls.py` with
`SPEC2SRC_GRADE_CMD` and `SPEC2SRC_REFERENCE_FORM` set. It checks one null
candidate and three fresh reference candidates. The offline adapter check is
`python3 packs/spec2src/selfcheck.py`.

Subject rows in `results.jsonl` contain the registered agent binding, agent
wall time, grader time, verdicts, rates, both hashes, and accounting fields.
Token and command counts are filled only from attributable structured provider
receipts; unavailable counts and cost remain null. A venue failure is
INCONCLUSIVE and can be rerun for that cell while retaining the first attempt.

For the fixed protocol, schedule one cell at a time with `K=1` and
`RUN_INDEX=1`, `2`, or `3`, in randomized order within each batch. Set
`SPEC2SRC_BATCH_SEED` on each call so the run row retains the order seed.
`bashy dag bench PACK=spec2src` remains available for ordinary sequential
pack runs.

# spec2src: form from its public spec

`t1-form/fixture/` is the complete initial subject workspace. Its seven files
are pinned in `task.yaml`; the five source documents are copied byte for byte
from the pinned bashy `examples/desk/form` (spec v2.1). `dag.md` is the
lifecycle of the app as a spec (Sprint 731): its steps run with `sh` and
without bashy, the subject may not change it and must make its steps work
(`build.sh`, the `serve` command). It is written here and is not the
lifecycle file of the bashy reference build. `TASK.md` tells the
subject that the judge's `conform` is on its PATH, so the venue must put a
standalone `conform` binary there. The subject writes source and an
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

## Running a drill (`venue/`)

`venue/` holds the fixed conditions of a drill, as used in Sprint 723:

- `env.sh`: the conditions every arm runs with (a plain system shell, the
  keychain opt-ins, no self-update, a frozen adapter cache, the judge on
  PATH). It needs `S2S_HOME`, a private directory outside any source tree.
- `probe.sh AGENT`: asks a binding, in a real isolated arm and without the
  task, to run `conform version`. Run it before a binding's first batch.
- `run.sh AGENT BATCH RUN_INDEX [SEED]`: one run through the runner and the
  private grade command (`S2S_GRADE_CMD`), with the quiet-workspace cutoff
  equal to the wall-time cap.
- `guard.sb.template`: the sandbox profile to fill in and save as
  `$S2S_HOME/guard.sb`.

The full procedure, with the traps, is the umbrella kb runbook
`spec-to-source-drill`.

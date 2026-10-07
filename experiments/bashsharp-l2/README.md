# Bash# L2 differential experiment

This is the prepared, three-arm experiment for Sprint 381 Story 1564.  It
uses the existing `packs/l2` fixtures and graders; it is not a new benchmark.

The operator runs it only after S1--S3 and S7--S8 are integrated into one
frozen candidate.  Do not run it on a developer workstation.  A smoke is one
cheap task/arm/repetition on the remote test host; a full run is 20 tasks x
3 repetitions x 3 arms (180 trials).

The agent must run in an OCI container or a separate OS account.  Mount only
the staged fixture and the candidate shell into that principal.  Do **not**
mount this checkout, `RUNS`, graders, references, or the result directory.
The evaluator runs outside that principal after the agent exits.  Detection in
screen logs is supplemental; a prompt saying not to read keys is not isolation.

Prepare a candidate manifest (this does not call a model):

```sh
python3 scripts/bashsharp_l2_experiment.py prepare \
  --output /srv/bench/s381-candidate \
  --candidate /srv/candidates/bashy \
  --model MODEL_ID --agent AGENT_ID --seed 381
```

The remote harness stages each fixture into the isolated principal, invokes
the arm's `action-shell` (`scripts/bashsharp_l2_action_shell.py`) with the candidate specified by `candidate_path`,
and writes one raw JSON object per trial.  It must preserve the same task
bytes, candidate digest, model identity/options, budget, seed, task order and
repetition ID for every arm.  The only changing fields are `arm` and its
`action-shell`/prelude.  `bash` runs the candidate with Bash# disabled;
`guards-contracts` and `fences` execute real dialect prelude files, rather
than adding arm names to the prompt.

The executor sets `BASHY_EXPERIMENT_ARM`, `BASHY_EXPERIMENT_CANDIDATE`, and
`BASHY_EXPERIMENT_ASSETS` (a read-only copy of this experiment's `arms/`
directory), then makes that action-shell the agent's shell. For dialect arms
it materializes the action bytes in a private temporary file and invokes the
candidate on the real contract/fence prelude. It rejects shell forms other
than `-c` rather than silently dropping an action.

After every trial, append its raw row to `raw.jsonl`; then produce the gate
record (also non-billable):

```sh
python3 scripts/bashsharp_l2_experiment.py report \
  --manifest /srv/bench/s381-candidate/manifest.json \
  --raw /srv/bench/s381-candidate/raw.jsonl \
  --output /srv/bench/s381-candidate/evidence.json \
  --bashy /srv/candidates/bashy
```

`report` refuses an incomplete or unpaired result, records token totals and
their source, leaves dollars `unknown` unless the provider supplied reliable
pricing, classifies terminal failures, and delegates each comparison to
`bashy stats paired`.  At 1,200 seconds/trial, the conservative serial upper
bound is 60 hours; plan host capacity from the actual frozen task budget and
record the observed wall time instead of guessing a shorter one.

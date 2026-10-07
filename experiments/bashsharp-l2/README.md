# Bash# L2 paired experiment

Sprint 381 Story `050a68a821a9`: 20 existing L2 tasks × K=3 × three arms =
180 trials. It is a runnable preparation, not an evidence claim. Keep the
story open until all 180 non-void rows have been measured and accepted.

## Remote prerequisites and invocation

On `novidesign.local`: Podman 4+ working for the executing user, Python 3,
Git, a Linux agent image containing the selected provider CLI, and that CLI
authenticated inside the image. The frozen candidate must be exactly
`~/s381/candidate-base/bashy/bin/bashy`. No droplets and no model calls are
made by `prepare`, tests, or local validation.

The provider command runs in the OCI principal. It must use
`$BASHY_EXPERIMENT_PROMPT`, work in `/work`, use `$SHELL` for actions, respect
`$BASHY_EXPERIMENT_BUDGET_SECONDS`, and finish stdout with exactly one line:

```text
S381_USAGE:{"tokens":1234,"token_source":"provider-reported"}
```

Unknown usage is deliberately a void attempt and makes `report` refuse the
run. Choose one model, agent, JSON options and 600-second task budget for all
arms. With two concurrent 600-second trials, 180 trials have a 15-hour worst
case; a full run cannot fit the stated 90 minutes. The bounded executor defaults
to two jobs on the 4-CPU/8-GB host; use it for smoke only until an operator
approves a feasible budget/capacity change. A realistic identical full budget
must be at most 60 seconds for a 90-minute two-job upper bound (plus overhead).

```sh
cd ~/s381/candidate-base/agent-bench
python3 scripts/bashsharp_l2_experiment.py prepare \
  --output /srv/bench/s381 --candidate ~/s381/candidate-base/bashy/bin/bashy \
  --model MODEL_ID --agent AGENT_ID --seed 381 --k 3 --budget-seconds 60 \
  --model-options '{"temperature":0,"max_tokens":4096}'
python3 scripts/bashsharp_l2_executor.py --manifest /srv/bench/s381/manifest.json \
  --raw /srv/bench/s381/raw.jsonl --image PROVIDER_IMAGE --jobs 2 \
  --provider-command 'YOUR_PROVIDER_AGENT_COMMAND'
python3 scripts/bashsharp_l2_experiment.py report \
  --manifest /srv/bench/s381/manifest.json --raw /srv/bench/s381/raw.jsonl \
  --output /srv/bench/s381/evidence.json --bashy ~/s381/candidate-base/bashy/bin/bashy
```

For a deterministic local smoke, use a locally built image with a fake provider
that edits only `/work` and emits the usage line; do not run a real provider
locally. Manager alone performs the real-model smoke.

## Fairness and isolation

`bash` is ordinary dialect-off Bash (`candidate -c`), explicitly not POSIX
mode. `guards-contracts` invokes a real guarded agentic function using valid
effect atoms `read,write,exec`. `fences` executes a real qualified `~~~sh`
fence method before the same guarded action; it checks and propagates the
fence status, then sources the action so action stdout and status are preserved.
No arm is merely a prompt label or no-op context.

Each OCI trial receives a writable fixture, a read-only candidate, and immutable
runtime adapter/prelude plumbing; no checkout, references, graders or result
directory is mounted. Grading happens outside after exit. An evaluator-only
planted marker is checked in raw output. Raw logs, provider usage, candidate,
fixture, model-options and manifest digests accompany each row. The report
rejects invalid/duplicate/unpaired rows, voids, unknown token costs and mixed
candidate/model/fixture/options provenance. `bashy stats paired` supplies the
paired 95% confidence intervals; evidence includes cost per solve.

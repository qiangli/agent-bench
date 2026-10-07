# Bash# L2 paired experiment

Sprint 381 Story `050a68a821a9`: 20 existing L2 tasks × K=3 × three arms =
180 scheduled trials. Preparation, unit tests, and image construction make no
model calls. Keep the story open until `report` accepts all 180 outcomes;
fixed-budget timeouts are measured failures, not excluded rows.

## Frozen runtime

Set `TEST_HOST` to the assigned test host, `WORKDIR` to its frozen candidate
checkout, and `RESULTS_DIR` to a protected results directory. The host needs
Podman 4+, 4 CPUs, 8 GB RAM, outbound provider access, and Linux/arm64 image
support. The candidate must be a Linux/arm64 ELF executable; a Darwin Mach-O is
rejected before any provider call.

```sh
ssh "$TEST_HOST"
cd "$WORKDIR/bashy"
mkdir -p bin/linux bin/host
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 \
  go build -trimpath -ldflags=-w -o bin/linux/bashy ./cmd/bashy
env -u GOOS -u GOARCH -u CGO_ENABLED \
  go run ./tools/elfaudit --bashy-signal bin/linux/bashy
env -u GOOS -u GOARCH -u CGO_ENABLED \
  go build -trimpath -o bin/host/bashy ./cmd/bashy
file bin/linux/bashy                 # must report ARM64 ELF, not Mach-O

cd "$WORKDIR/agent-bench"
podman build \
  --platform linux/arm64 \
  -f experiments/bashsharp-l2/Containerfile.codex \
  -t localhost/s381-codex:0.157.1 .
podman image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' localhost/s381-codex:0.157.1
```

Do not cross-build with `GOOS=linux ... make build` on Darwin. The Make target
also runs `go run ./tools/elfaudit`; inherited `GOOS` makes that helper a Linux
ELF and Darwin fails to execute it. Build the candidate with the separate
`go build` above, then run `elfaudit` as a host-native Go program. The audit can
inspect the Linux ELF without executing it.

The image pins `@openai/codex` 0.157.1 and includes the task tools (Git,
Python/pytest, Make, and a C compiler). It contains no credential. Import the
manager's existing Codex login as a Podman runtime secret; do not print or copy
the secret into the checkout or result directory:

```sh
test -s "$HOME/.codex/auth.json"
podman secret rm s381-codex-auth 2>/dev/null || true
podman secret create s381-codex-auth "$HOME/.codex/auth.json"
```

The adapter redacts the complete secret and all long string values found in the
auth JSON before preserving CLI output. The secret is mounted only at runtime.
For an API key instead, create the same secret from a protected key file and add
`--auth-kind api-key` to executor commands.

## Prepare and smoke

One supported provider/model/config is frozen for every arm: Codex CLI,
`gpt-6-luna`, and low reasoning effort. The CLI receives the manifest model
through `--model`, receives every model option through strict `--config`, and
emits JSONL. Token counts come only from its `turn.completed.usage` event; a
missing final usage stays explicitly unknown.

```sh
cd "$WORKDIR/agent-bench"
mkdir -p "$HOME/.cache/s381/tmp"
export TMPDIR="$HOME/.cache/s381/tmp"
python3 scripts/bashsharp_l2_experiment.py prepare \
  --output "$RESULTS_DIR/full" \
  --candidate "$WORKDIR/bashy/bin/linux/bashy" \
  --model gpt-6-luna --seed 381 --k 3 --budget-seconds 60 \
  --model-options '{"model_reasoning_effort":"low"}'
  # --story-id defaults to the frozen Sprint 381 story 050a68a821a9, so every
  # existing caller is unchanged. Pass --story-id 2a5323bb1372 (the Sprint 287
  # follow-up story) to label a fresh comparison run with the corrected
  # fences/guards-contracts prelude; tasks, K, seed, model, budget, candidate,
  # and image stay frozen — only the label and the arm prelude differ.

# One real provider trial first. This is smoke evidence, not one of the 180.
cp "$RESULTS_DIR/full/manifest.json" "$RESULTS_DIR/smoke-manifest.json"
python3 scripts/bashsharp_l2_executor.py \
  --manifest "$RESULTS_DIR/smoke-manifest.json" \
  --raw "$RESULTS_DIR/smoke.jsonl" \
  --image localhost/s381-codex:0.157.1 --network pasta --jobs 1 --limit 1
python3 -c 'import json,sys; r=json.loads(open(sys.argv[1]).read()); assert not r.get("void"),r' \
  "$RESULTS_DIR/smoke.jsonl"
```

Do not start the full run if smoke is void. A void means infrastructure or
authentication could not produce a benchmark outcome. Preserve the row and
log, correct the runtime, and smoke again into a new empty output. Never edit a
measured row into success.

## Full 180 and report

Four 1-CPU/1500-MB jobs use at most 6 GB on the 4-CPU/8-GB host. The exact
60-second task budget gives a 45-minute trial-time upper bound for 180 trials at
four jobs, before container stop, image, grading, and provider overhead.
The deterministic schedule rotates and interleaves all arms. The executor is
resumable: every row is flushed and fsynced, and an existing task/repetition/arm
is never silently rerun.

```sh
python3 scripts/bashsharp_l2_executor.py \
  --manifest "$RESULTS_DIR/full/manifest.json" \
  --raw "$RESULTS_DIR/full/raw.jsonl" \
  --image localhost/s381-codex:0.157.1 --network pasta --jobs 4

python3 scripts/bashsharp_l2_experiment.py report \
  --manifest "$RESULTS_DIR/full/manifest.json" \
  --raw "$RESULTS_DIR/full/raw.jsonl" \
  --output "$RESULTS_DIR/full/evidence.json" \
  --bashy "$WORKDIR/bashy/bin/host/bashy"
```

`TMPDIR` must name a directory under the Podman VM's shared home tree so the
executor's per-trial workspace can be bind-mounted. Current Podman rejects the
legacy `slirp4netns` backend in this environment; use `--network pasta`. On
Darwin, `report --bashy` must point to a host-native Bashy binary because the
report executes `bashy stats paired`; the Linux/arm64 candidate is only for the
provider containers.

A timeout stops and removes the named container, preserves partial redacted
output, grades the resulting workspace, and writes a genuine failed outcome.
It is never selectively rerun or excluded. Infrastructure/authentication and
executor failures are recorded as void attempts in the append-only raw history.
A void key may be retried only while every prior attempt for that key is void;
once one valid outcome exists, that key is complete. The report accepts void
history when every scheduled key has exactly one valid outcome, and includes
the full attempt history and retry accounting. It fails closed on an unresolved
key, duplicate valid outcomes, malformed void attempts, mixed provenance, or
an action outside the measured shell interface. All 180 scheduled outcomes
enter paired success-rate statistics. Missing final usage is explicit; cost per
solve is a known-token lower bound plus an unknown-row count.

`evidence.json`'s `paired` block is `bashy stats paired`, clustered by trial
instance (`task#repetition`). `paired_bootstrap` is a second, complementary
statistic over the same raw rows: a percentile bootstrap 95% CI for the same
B-minus-A resolve-rate difference, but clustered by *task* — every arm pair's
K=3 repetitions of a task are grouped into one bucket, and the bootstrap
resamples the 20 task buckets (not the 60 trials) with replacement. That
avoids treating a task's three repetitions as three independent data points
when they share whatever makes that task easy or hard. It uses a private, seeded `random.Random` (the manifest's frozen seed), so a
rerun of `report` against the same `raw.jsonl` reproduces it exactly, and it
makes no model or provider call.

## Arm enforcement and isolation

`bash` explicitly passes `--no-bashpp`; it does not rely on defaults or the
ambient environment and is not POSIX mode. `guards-contracts` runs every
command inside the real `read,write,exec` guard with a precondition checking
the harness-owned action input. It claims no generic postcondition because
inventing one would change the tasks. `fences` exports the actual command as a
qualified `~~~sh` method under the same guard and preserves its stdout bytes,
status, and stderr.

Both arms declare `@effects("read,write,exec")`, not `@guard(effects: ...)`.
`@effects` both narrows the cap to that envelope *and* vouches that commands
the Command Atlas cannot classify (a literal nested `sh -c ...`, `rg`, ...)
really do stay inside it; `@guard` only narrows the cap and denies an
atlas-unknown command outright regardless of how permissive the cap is, which
was Sprint 381's near-total guards/fences failure (Story `2a5323bb1372`). That
vouch is the benchmark's own author asserting the envelope for its own arm
code, not a claim about transitive containment of whatever a child process
spawns: an atlas-unknown command that itself opens an opaque network
connection the Atlas cannot see is not proven contained by this fix, it is
simply outside what this harness can observe. What the cap-only refusal still
proves, unchanged, is that any command the Atlas *does* classify outside the
declared envelope is denied before it runs — `curl` (`net`) and `rm` (atlas
`destroy`, never implied by `read,write,exec`) both still exit 126 and leave
their target untouched; see `test_nested_shell_and_atlas_unknown_commands_run_under_declared_effects`
in `scripts/test_bashsharp_l2_experiment.py`.

The provider image replaces its actual `/bin/sh` and `/bin/bash` with the arm
wrapper; `$SHELL` is not the enforcement mechanism. The prompt requires shell
actions only, and the adapter audits Codex JSONL and voids a trial that reports
a direct file-change, MCP, web, or computer action. Each task uses the prompt
frozen beside its `TASK.md`; preparation and execution both verify that file's
digest.

The agent sees only a writable fixture, read-only candidate, arm assets, and
runtime auth secret. The executor runs as the keep-id mapped UID/GID and mounts
the mode-0400 secret for that identity. It never sees references, graders, result files, or the
evaluator-only directory. Every trial actually plants a random marker in that
unmounted directory, records its digest, and becomes void if the marker appears
in provider output. Grading occurs after the container exits. Provider image
identity, CLI version, model/options, candidate, fixture, task prompt, raw logs,
usage, and negative-control digest accompany the row. Dollar pricing remains
explicitly unknown; evidence reports a known-token lower bound, unknown usage
count, and lower-bound tokens per solve, not fabricated currency cost.

Scoring is identical for all three arms: a normal completion with zero shell
commands is a strict protocol failure (0 points, `fail=true`) while retaining
provider usage. Any off-interface action reported in `forbidden_action_types`
is also a strict protocol failure (0 points, `fail=true`), retains real usage,
and remains a scored outcome rather than an infrastructure void. Infra/auth/
executor void attempts may be retried only when all prior attempts for the key
are void; raw history is append-only and the report requires exactly one valid
outcome per key.

`failure_taxonomy` counts only unresolved scored outcomes (`resolved=false`),
using timeout/protocol metadata and terminal output to categorize the failure.
Successful outcomes are not failures even when their terminal output contains
text that resembles a failure signature; those classifications, when present,
are reported separately in `resolved_terminal_output`. Void attempts are
accounted for in `attempt_accounting`, not counted as scored failures.

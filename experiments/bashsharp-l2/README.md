# Bash# L2 paired experiment

Sprint 381 Story `050a68a821a9`: 20 existing L2 tasks × K=3 × three arms =
180 accepted trials. Preparation, unit tests, and image construction make no
model calls. Keep the story open until `report` accepts exactly 180 non-void
rows from the remote host.

## Frozen runtime

Use `novidesign.local` with Podman 4+, 4 CPUs, 8 GB RAM, outbound OpenAI API
access, and the frozen checkout at `~/s381/candidate-base`. The candidate must
be a Linux ELF executable; a Darwin binary is rejected before any provider call.

```sh
cd ~/s381/candidate-base/bashy
make build
file bin/bashy                       # must report ELF, not Mach-O

cd ~/s381/candidate-base/agent-bench
podman build \
  -f experiments/bashsharp-l2/Containerfile.codex \
  -t localhost/s381-codex:0.157.1 .
podman image inspect --format '{{.Id}}' localhost/s381-codex:0.157.1
```

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
`gpt-5.4-mini`, and low reasoning effort. The CLI receives the manifest model
through `--model`, receives every model option through strict `--config`, and
emits JSONL. Token counts come only from its `turn.completed.usage` event.

```sh
cd ~/s381/candidate-base/agent-bench
python3 scripts/bashsharp_l2_experiment.py prepare \
  --output /srv/bench/s381-full \
  --candidate ~/s381/candidate-base/bashy/bin/bashy \
  --model gpt-5.4-mini --seed 381 --k 3 --budget-seconds 60 \
  --model-options '{"model_reasoning_effort":"low"}'

# One real provider trial first. This is smoke evidence, not one of the 180.
cp /srv/bench/s381-full/manifest.json /srv/bench/s381-smoke-manifest.json
python3 scripts/bashsharp_l2_executor.py \
  --manifest /srv/bench/s381-smoke-manifest.json \
  --raw /srv/bench/s381-smoke.jsonl \
  --image localhost/s381-codex:0.157.1 --jobs 1 --limit 1
python3 -c 'import json,sys; r=json.loads(open(sys.argv[1]).read()); assert not r.get("void"),r' \
  /srv/bench/s381-smoke.jsonl
```

Do not start the full run if smoke is void. Preserve the smoke row and log as
the failure record, correct the runtime, make a new empty smoke output, and
smoke again. Never edit a measured row into success.

## Full 180 and report

Four 1-CPU/1500-MB jobs use at most 6 GB on the 4-CPU/8-GB host. The exact
60-second task budget gives a 45-minute trial-time upper bound for 180 trials at
four jobs, before container stop, image, grading, and provider overhead.
The deterministic schedule rotates and interleaves all arms. The executor is
resumable: every row is flushed and fsynced, and an existing task/repetition/arm
is never silently rerun.

```sh
python3 scripts/bashsharp_l2_executor.py \
  --manifest /srv/bench/s381-full/manifest.json \
  --raw /srv/bench/s381-full/raw.jsonl \
  --image localhost/s381-codex:0.157.1 --jobs 4

python3 scripts/bashsharp_l2_experiment.py report \
  --manifest /srv/bench/s381-full/manifest.json \
  --raw /srv/bench/s381-full/raw.jsonl \
  --output /srv/bench/s381-full/evidence.json \
  --bashy ~/s381/candidate-base/bashy/bin/bashy
```

A timeout stops and removes the named container, preserves partial redacted
output, grades the resulting workspace, and writes a void row. Any provider or
executor failure is likewise a durable void instead of aborting and losing
finished results. `report` fails closed on a void, duplicate, missing pair,
unknown usage, mixed image/candidate/fixture/model/options provenance, or an
action outside the measured shell interface.

## Arm enforcement and isolation

`bash` is ordinary dialect-off Bash, not POSIX mode. `guards-contracts` runs
every command inside the real `read,write,exec` guard and contracts. `fences`
first invokes a real qualified `~~~sh` fence method and then runs the same
guarded action.

The provider image replaces its actual `/bin/sh` and `/bin/bash` with the arm
wrapper; `$SHELL` is not the enforcement mechanism. The prompt requires shell
actions only, and the adapter audits Codex JSONL and voids a trial that reports
a direct file-change, MCP, web, or computer action. Each task uses the prompt
frozen beside its `TASK.md`; preparation and execution both verify that file's
digest.

The agent sees only a writable fixture, read-only candidate, arm assets, and
runtime auth secret. It never sees references, graders, result files, or the
evaluator-only directory. Every trial actually plants a random marker in that
unmounted directory, records its digest, and becomes void if the marker appears
in provider output. Grading occurs after the container exits. Provider image
identity, CLI version, model/options, candidate, fixture, task prompt, raw logs,
usage, and negative-control digest accompany the row. Dollar pricing remains
explicitly unknown; evidence reports provider tokens and tokens per solve, not
fabricated currency cost.

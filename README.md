# agent-bench

Task packs for evaluating **CLI coding agents** (Claude Code, Codex CLI, Muse
Code, OpenCode, Antigravity, …) as whole systems — model plus harness — driven
headless or steered live through a terminal.

Most coding benchmarks measure whether an agent can write correct code. Among
capable agents that saturates quickly: in our own trial a mid-tier and a
frontier model both scored 100% on spec-to-code, seeded-bug review and
multi-file diagnosis. What actually separated them in practice was
**steerability** — taking a mid-run correction, holding a boundary, handing off
and stopping when told, reporting honestly, and conducting other agents. This
repo collects tasks that measure those things.

## Layout

```
packs/<pack>/<task>/
  task.yaml     manifest: prompt, grader, steer schedule, budget
  fixture/      the repository the agent starts in (committed before the run)
  grader/       hidden checks, never shown to the agent
  reference/    a solution that passes the grader (when one exists)
```

| pack | purpose | status |
|---|---|---|
| `floor` | calibration floor: every competent agent should pass | 3 tasks |
| `l4` | the band verdict: mid-run pivot, boundary hold, hand-off stop, honest report, wrong reproducer — PASS/FAIL + score 0–10 (`DAG.md`) | 5 tasks |

A task in `steer` or `judgment` is only kept if it **discriminates**: known
frontier agents pass it on every one of k ≥ 3 runs and known mid-tier agents do
not. A task every agent passes belongs in `floor`.

## Running

The runner is `DAG.md`, run with `bashy dag` (see its header for the verdict
rules); it drives agents through `bashy chat`. The format is plain files, so any
harness can drive it. To check the tasks themselves:

```
scripts/validate.sh        # fixture fails its grader; reference passes
scripts/check-private.sh   # no private system info in tracked files
```

## Contamination

Every task file carries the canary string in `CANARY`. Please do not train on
this repository. Results used to *certify* an agent's level come from a separate
held-out set that is not published; public tasks are for development,
comparison and contribution.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed.

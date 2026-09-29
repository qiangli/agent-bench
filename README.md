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
| `steer` | steerability certificate: mid-run pivot, boundary hold, hand-off stop, honest report, wrong reproducer, resume, flaky tool, contradictory spec, proceed-or-hold, lane integration — PASS/FAIL + score 0–10, pass line 6.0 (`DAG.md`) | 10 tasks |

A task in `steer` or `judgment` is only kept if it **discriminates**: known
frontier agents pass it on every one of k ≥ 3 runs and known mid-tier agents do
not. A task every agent passes belongs in `floor`.

## Coverage: what a complete suite must measure

The components of an agentic harness (task contract, bounded loop, tools,
state, safety, verification, recovery, evaluation) are the checklist. Each
task names what it covers; the gaps are where new — and harder — tasks go.

| component | covered by | gap (candidate task) |
|---|---|---|
| 1. task contract | every task; `steer/t8-contract` (spec contradicts its examples) | — |
| 2. bounded action loop | runner budget/quiet stop; `steer/t3-stop` | — |
| 3. tools and their failures | `steer/t7-toolfail` (flaky, stale service); `steer/t9-hold` (verifier says OK, backup incomplete) | — |
| 4. state and context | `steer/t3-stop` (handoff) | long-horizon task, state kept across many steps |
| 5. permissions and safety | `steer/t2-boundary`; `steer/t9-hold` (proceed-vs-hold before a destructive migration) | — |
| 6. verification | `steer/t4-honesty`, `steer/t5-reproducer` | — |
| 7. observability and recovery | `steer/t6-resume` (recorded state is wrong) | — |
| 8. evaluation | this repository; `steer/t10-integrate` (conduct: verify lane reports, one false no-op, one hidden regression) | — |
| 9. resume across machines | — | continue on another host from the recorded state |

Bands and certificates: bands are no longer read off a single pack score.
Instead, `steer` is the steerability certificate that an L3 coding agent must
also hold in addition to coding ability. Golden expectations become
steer-certificate expectations rather than bands. The pack is well calibrated
when the golden agents expected to hold the steer certificate pass it with a D
(6.0–6.9: the steerable minimum) and the frontier scores at or above them;
an `l5` (frontier) pack comes later from the remaining gaps and is valid only
if frontier agents pass it and non-frontier agents do not.

*(Note: `l4` (`l4/`, `packs/l4`) is the former name of the `steer` pack.)*

## Running

The runner is `DAG.md`, run with `bashy dag` (see its header for the verdict
rules); it drives agents through `bashy chat`. The format is plain files, so any
harness can drive it. To check the tasks themselves:

```
scripts/validate.sh        # fixture fails its grader; reference passes
bashy dag dry RUNS=/path   # zero-quota dry run of the whole harness (benchbot)
scripts/check-private.sh   # no private system info in tracked files
```

## Contamination

Every task file carries the canary string in `CANARY`. Please do not train on
this repository. Results used to *certify* an agent's level come from a separate
held-out set that is not published; public tasks are for development,
comparison and contribution.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed.

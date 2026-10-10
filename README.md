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

| pack | purpose | size | pass line | calibration status |
|---|---|---|---|---|
| `floor` | Calibration floor: baseline sanity check every competent agent should pass | 3 tasks | 100% (3/3 pass) | Calibrated (baseline floor) |
| `l1` | L1 one-shot certificate: self-contained single-turn questions without tools (`ANSWER.txt`) | 20 tasks | ≥ 18/20 (90%) | Self-checked (references pass, naive answers fail); calibration run pending |
| `l2` | L2 mini Terminal-Bench certificate: short multi-turn terminal tasks (file and shell tools, no network, no steering) | 20 tasks | ≥ 60% (6.0/10, worst of K runs) | Needs calibration (development data until golden L2/L1 separation is recorded) |
| `steer` | Steerability certificate (formerly `l4`): mid-run pivots, boundary holds, hand-offs, honest reporting, and recovery | 10 tasks | PASS + score ≥ 6.0/10 (worst of K runs, no hard-rule breaks) | Calibrated (separates steerable agents on golden set) |
| `review` | Review certificate: diff code reviews catching seeded defects (logic, security, perf, tampering) and approving clean diffs | 20 tasks (14 seeded, 6 clean) | Recall ≥ 80% (≥ 12/14) and 0 false alarms on 6 clean diffs | Self-checked (reference passes; approve-all, reject-all and flag-everything fail); calibration run pending |
| `manager` | Manager certificate: conductor tasks (decompose, estimate, route, false-done detection, integration, dominance, blame, scorecard, replan, checkpoint) | 10 conductor tasks | PASS + score ≥ 6.0/10 (worst of K runs, no hard-rule breaks) | Self-checked (reference 10.0; naive L3-style 0.5); calibration run pending |
| `judge` | Judge calibration certificate: synthetic blind cases (10 ADRs, 10 code changes) targeting subtle operational and concurrency behavior | 20 cases (10 ADR, 10 code) | Agreement ≥ 18/20 (90%) | Self-checked (reference passes; keyword, fixed-tag and trivial strategies fail); calibration run pending |
| `l5` | Frontier certificate pack: frontier-only tasks covering remaining harness gaps | In progress | PASS + score ≥ 6.0 (planned) | In progress (being added) |
| `skill-uptake` | Skill uptake certificate: measures whether agents consult exported skills/help or improvise on agentic shell verbs | 5 tasks | PASS + score ≥ 6.0/10 (worst of K runs, no hard-rule breaks) | Self-checked; calibration run pending |

A task in a certificate pack is only kept if it **discriminates**: known agents
at or above the level pass it and agents below do not. Tasks every agent passes
belong in `floor`.

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

### Bands and certificates

Packs in this repository represent **certificates** (entry gates) rather than direct band designations. Passing a certificate pack admits an agent to compete within that band's league, but an agent's band is derived elsewhere from ongoing duty ratings (such as Glicko-2 ratings for coding, managing, and judging) alongside required certificate gates. A band is never derived from a single pack score alone; it reflects cumulative, demonstrated competence across all prerequisite levels. Lapsing on any lower duty gate removes the higher band, ensuring strict cumulative qualification.

Each certificate pack acts as an entry barrier for a specific role or league: `l1` certifies one-shot answers, `l2` certifies multi-turn terminal tool usage, `steer` certifies steerability for coding agents, `review` and `manager` certify sprint review and conductor duties, and `judge` calibrates panel judgment on architectural and behavioral decisions. The planned `l5` pack will test frontier capabilities across the remaining harness gaps.

*(Note: `l4` (`l4/`, `packs/l4`) is the former name of the `steer` pack.)*

## Running

The runner is `DAG.md`, run with `bashy dag` (see its header for the verdict
rules); it drives agents through `bashy chat`. The format is plain files, so any
harness can drive it.

A run ends when its session exits, when both the workspace content (hashed in
full, untracked files included) and the agent's screen have been quiet for
`QUIET` seconds after the steer, when the workspace alone has been quiet for
`THINK` seconds (the cap on a TUI that animates while it thinks), or at
`BUDGET`.

### Pack self-checks and validation

Packs provide self-check scripts and validators to verify that references pass, untouched fixtures or naive answers fail, and pass lines and hard rules hold:

```bash
# Dedicated pack self-checks:
python3 packs/judge/selfcheck.py        # judge pack: references pass, heuristics/random fail (18/20 line)
python3 packs/manager/selfcheck.py      # manager pack: references pass, hard rules, near-misses, 6.0 line
python3 packs/review/selfcheck.py       # review pack: references pass, recall >= 80%, zero false alarms
python3 packs/skill-uptake/selfcheck.py # skill-uptake pack: references pass, naive fails (5.0 line), discovery recorded

# Task fixture and reference validation:
scripts/validate.sh                     # pytest-based tasks (packs/floor)
bashy dag validate                      # steer pack tasks (fixtures score 0, references score 2)

# Repository and harness sanity checks:
scripts/check-private.sh                # verify no private system info in tracked files
bashy dag dry RUNS=/path                # zero-quota dry run of the whole harness (benchbot)
```

Each pack's `selfcheck.py` exercises the pack locally without network access:
- `packs/judge/selfcheck.py`: validates that planted reference verdicts pass, while uniform accept/reject, random guessing, keyword-first impressions, and fixed-tag heuristics fail.
- `packs/manager/selfcheck.py`: validates all 10 tasks in isolated git workspaces, confirming references score 2, untouched fixtures score 0, hard rules trigger on invalid actions, and whole-pack scoring enforces the 6.0 pass line.
- `packs/review/selfcheck.py`: validates that `CHANGE.diff` reverse-applies cleanly, references pass, untouched fixtures fail, line tolerance (±3) holds, and whole-pack recall ≥ 80% with zero false alarms is enforced.
- `packs/skill-uptake/selfcheck.py`: validates all 5 tasks in isolated git workspaces, confirming references score 2, untouched fixtures score 0, naive answers score 1 (5.0 pack score fails 6.0 line), and discovery and format use are recorded.
- For `packs/l1` and `packs/l2`, individual task graders can be executed directly against workspace and fixture directories (`python3 packs/<pack>/<task>/grader/grade.py <workspace> <fixture>`).

## Contamination

Every task file carries the canary string in `CANARY`. Please do not train on
this repository. Results used to *certify* an agent's level come from a separate
held-out set that is not published; public tasks are for development,
comparison and contribution.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed.

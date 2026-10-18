# Sprint 446 / story 2140: AGY t6 format pairs

Base: published agent-bench `51cb2ea`. This workspace made **zero vendor
requests**. No Bashy production files or defaults were changed.

## Matched arm plan

Use `packs/skill-uptake/t6-pdf-fact/fixture` and its unchanged
`packs/skill-uptake/t6-pdf-fact/grader/grade.py` for every arm. Run
`agy-gemini3.8-flash` (`gemini3.8-flash`) with `K=1`, `ATTEMPTS=1`,
`BUDGET=110`, `QUIET=20`, `THINK=60`, and `MIN_POST_STEER=20` per arm.
`DAG.md run` and `scripts/skill_arm.py` provide the selectors. Each arm gets
a separate workspace, HOME, `GEMINI_CLI_HOME`, Bashy state, and vendor config.
The first pair is `SKILL=script` versus `SKILL=on` (prose skill). Only if both
are trustworthy and fresh AGY quota remains safe, run `SKILL=yaml` versus
`SKILL=on` (canonical prose skill). The four-arm ceiling is four vendor
requests, with no retries. A second `on` run is needed for the second matched
pair; an earlier run cannot stand in for it.

Before **each** AGY request: run the real-HOME write-deny canary, check
`bashy model quota --json`, and require measured, current AGY 5h and weekly
usage below the driver caps (80% and 90%). Use
`scripts/guarded_live_arm.py` with `--tool agy --vendor-comm agy`, the common
parameters above, and separate evidence paths. The current driver reads
Claude JSONL for attributable token usage; AGY attribution must be added and
verified against its actual isolated transcript before any arm can earn a
trustworthy verdict. Screens alone do not establish usage or request count.

## Gate reached on 2026-10-18

`guard-summary.json` records a fresh real-binary, zero-model canary PASS:
the write-deny guard was live, isolated arm state appeared, tracked real-HOME
paths were unchanged, and no sandbox denials were attributed to the canary.
One concurrently updated Bashy lock was attributed to an external host PID.

`quota-agy.json` records the fresh Bashy quota result. Its sole AGY row has
`status: unmeasured`, no window, no used percentage, and no headroom. There
is no measured 5h or weekly row. The quota gate therefore refused the first
request. Both pair scores and attributable usage remain **unmeasured**. This
evidence supports no format default decision.

Only summaries are committed. The raw canary arm HOME and full all-provider
quota response were discarded to keep vendor configuration and unrelated
account data out of the commit.

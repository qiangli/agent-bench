# Sprint 446 / Story 2140: Claude t6 YAML versus canonical prose

After agent-bench #21 became terminal, a single `guarded_pair.py --order yaml,on`
dispatch used `claude-opus5.5` / `claude-opus-5-5`, the unchanged
`skill-uptake/t6-pdf-fact` task and grader, `BUDGET=100`, `QUIET=20`, and
candidate Bashy revision `8f0d6b1b`. The candidate binary's Go build metadata
reports that revision with `vcs.modified=true`; this is a provenance limit.
The pair process guard found zero competing bench runners. No retry was made.

The fresh Claude quota refresh returned analyzer door status 502. The guarded
runner accepted measured, nonstale cached rows: 5h 7% and week 39%, observed
at 17:10:48 PDT. The isolated HOME preparation and zero-model real-HOME canary
passed. Both before-request write-deny controls killed the decoy and real-HOME
probe and left no file behind. The guarded YAML skill export then exited 1
without producing `.agents/skills/bashy.yaml`. The pair stopped before any DAG
vendor launch and skipped prose. Post-request quota, guard, and HOME checks do
not apply because there was no vendor arm.

The result is **UNSCORED**, with zero vendor invocations and zero provider
requests. Neither arm has a score, result, discovery observation, or token
usage. No format comparison or measured delta exists. The canonical fallback
remains in place and S21 stays open. `summary.json` is the compact sanitized
receipt. Raw preflight evidence stays outside git; no transcript, request ID,
full HOME path, log, or binary is published here.

Focused zero-model tests: 51 passed with 2 skips. Candidate Bashy
`dag validate PACK=skill-uptake`: all 10 fixture/reference checks passed.

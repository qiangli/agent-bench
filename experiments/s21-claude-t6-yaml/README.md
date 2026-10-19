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

## Story 2140 follow-up

The YAML arm now uses the candidate CLI's supported `--to ... --yaml`
contract, without `--tool`. A regression first failed on the old command,
then passed after the fix; it checks that `.agents/skills/bashy.yaml` is
committed in the arm workspace. The `on` and `off` selectors retain their
existing behavior. The focused suite passed 39 tests, the pack validation
passed all ten tasks, and `git diff --check` passed.

One guarded pair was attempted with the same candidate revision, Claude agent,
model, task, budget, quiet period, and `yaml,on` order. The pair found zero
competing bench runners. Claude quota refresh failed, but measured nonstale
cached rows passed the quota gate (5h 8%, week 40%, observed at 17:15:51 PDT).
The zero-model canary passed; both before-request write-deny probes were killed
and left no files. YAML export reached the candidate CLI and was refused because
a bundled skill document carried host identity. No YAML artifact or vendor arm
was launched; prose was skipped by the pair's fail-closed rule. No retries were
made. The result is **UNSCORED**, with zero vendor invocations and zero provider
requests. Scores, result, discovery, token usage, post-request quota, and
post-request guards are unavailable. `followup-summary.json` is the sanitized
terminal receipt. The canonical fallback remains because there is still no
measured comparison.

## Read-only seat and candidate path follow-up

Yoke `0aba640f` made the steward role projection read an existing seat without
creating its registry or lock. Its new regression failed before the fix and
the full steward package passed afterward. Bashy rebuilt against that Yoke
tree passed the real-HOME canary, including the inbox command, with no guard
denials or protected-home changes. The candidate binary SHA-256 was
`71f9f977ee3f675eceb6580fdf7bc12302753fe8a83ac87950e5704d11e4baa7`.

The first guarded `yaml,on` dispatch stopped before vendor launch when the
selector resolved an older `bashy` executable from the candidate's directory.
The explicit candidate was used for the canary but not the nested selector.
The runner now places a link named `bashy` to the exact candidate first on the
nested PATH. A guarded zero-model YAML preflight produced the expected record
after this change, and the focused runner suite passed 29 tests.

The corrected pair attempt then stopped at the quota gate: the fresh Claude
quota endpoint returned 502, and its 5h cached row was stale. The runner
refused the YAML arm and skipped prose. Both attempts are **UNSCORED** with
zero vendor requests and no score or measured delta. The canonical fallback
remains. `read-only-seat-followup-summary.json` is the sanitized receipt.

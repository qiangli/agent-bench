# Sprint 446 / Story 2140: Kimi t6 script versus prose

Base: published agent-bench `60cba892c4a4a25b94ff739b7804ad11027f5c8d` after rebase. Holder: `codex-gpt6-sol`.
Task and grader: unchanged `skill-uptake/t6-pdf-fact` fixture and grader.

## Scope and corrected run limit

`SKILL=script` places the t6 Bashy command recipe in the isolated workspace's
`AGENTS.md`; `SKILL=on` exports the prose skill. Neither changes Bashy defaults.
The guarded driver reads the Kimi balance before and after an arm and extracts
ycode request events and exact assistant token usage from the isolated HOME.
Its preflight verifies the fleet model binding and the native ycode route's
USD 3 budget. Each arm has `BUDGET=100`, `QUIET=20`, `ATTEMPTS=1`, a three-minute
CLI wall limit, and its own HOME and ycode data directory.

The conductor's later correction superseded the initial one-provider-request
and USD 0.50 hard ceiling: one bounded CLI invocation per profile, native
USD 3 budget per arm, with internal requests counted from ycode's event log.
The correction did not authorize a rerun after a guard failure.

## Gate and attempted script arm

S10 Claude run #12 was terminal before the Kimi attempt. `bashy model verify
kimi-k2.6 --json` returned `ok` with Moonshot vault-key authentication.
`bashy model quota --provider kimi --json` returned a fresh measured balance
of USD **19.04183**. The zero-model real-HOME canary passed: isolated state was
created, the real HOME was unchanged, and the deny guard was live. Focused
zero-model tests passed (39 tests).

One `SKILL=script` CLI invocation was attempted. It delivered the task, then
exited before a scored result. The guard blocked a Go process attempting to
create a file in the real-HOME Go build cache. The process watcher also saw
unguarded Bashy ancestors, so containment could not be attested. The script
arm report was **UNSCORED** and its isolated ycode event log recorded **zero
provider requests**. No prose arm was launched, and no retry was made.

`attempt-summary.json` records the exact failed checks and negative-control
results. Balance before and after: **USD 19.04183**, delta **USD 0.00**.
Attributable token usage: **none**; script score: **unmeasured**; prose score:
**unmeasured**. The guard was effective (both decoy and real-HOME probes were
killed before and after the arm), and real-HOME fingerprints remained unchanged.
This run supports no skill format decision. Raw arm HOME and credential-bearing
records were discarded; only the summary is committed.

## Limit

The attempted arm reached a real-HOME write-deny violation before any provider
request. A future run needs the Go cache redirected into the isolated HOME and
must distinguish the guarded ycode process from unguarded harness ancestors in
the containment check. Neither change was used to rerun this pair.

## S21 continuation after review

The Go build cache is now set to each arm's isolated HOME, and the watcher
separates unguarded DAG wrappers from guarded descendants. The focused
zero-model suite passed (51 tests, two skips). The real-HOME deny canary passed
again, and guarded preflight accepted both script and prose selectors. Kimi
fleet auth and the native USD 3 route budget passed before dispatch.

One additional `SKILL=script` CLI arm ran with `BUDGET=100`, `QUIET=20`,
`ATTEMPTS=1`, and a three-minute CLI wall limit. It produced a task score of
**1** (PDF due date correct), with **11** internal ycode provider requests.
The isolated receipt recorded **12,908 input**, **1,269 output**, and **9,216
cache-read input** tokens (zero cache-creation input tokens). Measured Kimi
balance was **USD 19.04183** before and after, so the observed delta was
**USD 0.00**; the receipts were observed at 16:06:47 and 16:08:25 PDT.
This balance delta is the observed provider receipt, not a claim that those
tokens were free or that billing will never update.

The driver returned `FAIL` because its environment check included three
sandboxed Bashy helper commands (`dag package`, `kb context`, `contain`) as
vendor processes. Their short-lived environment snapshots lacked some path
variables. The actual ycode launch records had isolated HOME,
CLAUDE_CONFIG_DIR, and GOCACHE paths. Both real-HOME negative controls passed;
there were no real-HOME changes or sandbox denials. The process classifier has
an offline regression fix, but this arm was **not rerun**. Because the driver
reported a guard failure, no prose arm was launched. The pair remains open
and cannot support a format comparison. `retry-summary.json` is the sanitized
receipt; raw arm data stays outside the repository.

## Story 9c30598a1921 attempt on published 4559a82

The focused zero-model gate passed (43 tests). The pair driver now accepts
`script,on`, forwards the ycode process selector to each guarded arm, and
records balance and selector evidence. Its concurrency check also excludes the
driver's parent shells, whose command lines may contain the driver name. An
initial pair dispatch stopped before either arm because of that false match;
it made no vendor call.

The subsequent single `script,on` dispatch reached the script arm's isolated
setup, then the driver received SIGTERM (exit 143) before writing its report.
The zero-model real-HOME canary passed. A fresh measured Kimi balance was USD
19.03782 before setup. The interrupted isolated tree had no ycode event log,
no request marker, no scored result, and no `AGENTS.md` script selector in the
workspace. Because the driver did not finish its negative controls, receipt
capture, or after balance check, the guard verdict, score, and token usage are
**unmeasured**. A separate fresh balance read later returned USD 19.03179;
the observed USD 0.00603 change cannot be attributed to this arm.

The prose arm was not launched. No retry was made. The earlier run14 score of
1 remains unverified, the canonical fallback stays in place, and S21 remains
open. `interrupted-summary.json` is the sanitized record; raw isolated HOME
and workspace artifacts were not added to the repository.

## Fresh matched pair after the interrupted attempt

The preserved issue-16 commit was applied without content changes as `31ac2bc`
with this story's trailers. The concurrency predicate was reviewed and an
offline test now covers the driver ancestry and a separate sibling runner.
The focused zero-model suite passed (53 tests). The new pair used one
`script,on` dispatch, fresh measured Kimi balance, the native ycode USD 3
route budget, `BUDGET=100`, `QUIET=20`, `ATTEMPTS=1`, and a three-minute CLI
wall limit per arm. Both arms passed the zero-model real-HOME canary, before
and after write-deny probes, skill export match, usage receipt, and guard
checks. There were no real-HOME changes or sandbox denials.

The script arm scored **1** (correct PDF due date) with 12 ycode requests and
14,818 input / 1,213 output tokens. The prose arm scored **0** (wrong PDF fact)
with 10 requests and 12,229 input / 1,201 output tokens. The measured balance
was USD 19.03179 before and after each arm; an unchanged receipt is not a
claim about eventual billing. `fresh-pair-summary.json` contains the compact
sanitized comparison. Raw HOME, session logs, and credential-bearing records
remain outside the repository.

This is one valid comparison for one task, favoring script 1 to 0. The
canonical fallback remains unchanged pending broader evidence.

## YAML single-record versus canonical prose (Story 9c30598a1921)

Starting from published `d949d5b`, the pair selector now permits `yaml,on`.
The guarded arm checks `.agents/skills/bashy.yaml` for YAML preflight and
workspace matching. A focused zero-model regression verifies that ycode's YAML
export produces that file and that the pair forwards identical task, model,
budget, quiet time, tool, and process guard settings to both selectors. No
production Bashy default changed.

S10 issue #19 had a terminal committed pair record before preflight. The
current process guard found zero competing bench runners. Kimi model binding
verification passed. The standalone zero-model real-HOME canary passed with an
isolated HOME, no canary-attributed real-HOME changes, and no sandbox denials.
The fresh Kimi quota refresh then refused with `analyzer door status 502`.
Following the stop rule, neither vendor arm was launched and no retry was made.

The pair is **UNSCORED**: YAML and prose scores, task results, observed
discovery, and token usage are unmeasured; provider requests are **0**. A fresh
balance and balance delta are unavailable. The compact receipt is
`yaml-pair-summary.json`; the raw preflight failure receipt is archived outside
git. The canonical fallback remains, and the story stays open pending the
acceptance matrix.

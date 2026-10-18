# Sprint 446 / Story 2140: Kimi t6 script versus prose

Base: published agent-bench `a2f8b5a`. Holder: `codex-gpt6-sol`.
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

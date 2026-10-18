# Sprint 446 / story 2140: Kimi t6 preflight

Base: published agent-bench `a2f8b5a`. Holder: `codex-gpt6-sol`.
Task and grader are the unchanged `skill-uptake/t6-pdf-fact` pair.

## Implemented offline

- `SKILL=script` now commits a t6 command recipe in the isolated workspace's
  `AGENTS.md`: `bashy lens -t md invoice.pdf`. It contains no answer and no
  prose skill export. `SKILL=on` exports Bashy's prose skill through ycode's
  declared project integration. The CLI invocation selects the same task in
  both arms.
- The arm evidence copier retains ycode's isolated event log and payloads.
  Receipt parsing counts `llm.requested` events, including requests without a
  committed turn, and reads exact token fields from the committed assistant
  messages. Mixed sessions, missing counts, and a request count other than one
  fail closed. The guard accepts a fresh measured USD balance row for Kimi but
  refuses a ycode launch until a pre-request hard cap is verified.
- Focused zero-model unit tests and the 10-task skill-uptake selfcheck pass.
  No Bashy production code, defaults, model registry, or vendor config changed.

## Exact blocker and limits

`quota-before.json` records a fresh measured Kimi USD balance of **19.04183**.
The balance is an available-funds reading, not a per-request cost bound. The
active `bashy ycode --yolo config show` profile permits **4,000 model
invocations**, a **USD 3 route budget**, and up to **3 transport retry
attempts**. The existing `bashy chat`/DAG path does not prove a hard
one-provider-request limit or a USD 0.50 total ceiling. A wall timeout and a
post-run receipt cannot enforce either limit before charging. Fleet auth is
also not established by a balance probe alone. `guarded_live_arm.py` refuses
ycode before launch for this reason.

S10 Claude run #12 remained `working` at the last status check. To preserve
its exclusive window, **no Kimi arm was launched**. Kimi vendor requests: **0**;
Kimi spend in this attempt: **USD 0**; script score: **unmeasured**; prose
score: **unmeasured**; token usage: **unmeasured**. The allowed ceiling remains
**USD 0.50 total**, at most one script/prose pair and one request per arm, with
no retries. The required before/after balance, separate live arm HOMEs and
live real-HOME deny canary have no post-request evidence because no request
was made; the earlier AGY zero-model canary is recorded in
`experiments/s21-agy-t6/guard-summary.json` and is not Kimi attestation.

Resume only after #12 is terminal and a verifiable, pre-request ycode
one-call and USD 0.50 cap exists; then rerun the isolation canary and take a
new balance snapshot before each arm. Do not infer a format default from this
zero-request attempt.

---
id: 7b3b2ec4aac7
kind: test
title: 'shapeware pack: align t2 with KI-1, t3 with features.yaml; add t4 lifecycle ladder on a CLI contract'
seq: 6
status: wontfix
priority: p1
created: 2026-11-25T20:07:07.515155Z
sprint: 721
sprint_id: 69fc2c51-8faf-58e7-83ac-f27007837ae7
sprint_title: 'Shapeware pilot on form: spec v0.1 layout, lifecycle, one-step launch'
closed: 2026-11-25T21:02:01.026666Z
---

Sprint 721 pilot P2, follow-up to df3c2212 (packs/shapeware landed at eedad82). Operator decisions on the sprint 721 thread (2026-11-25): equivalence is judged behaviourally per layer (report: no observable difference at a declared interface after declared normalization, on a hidden suite of measured strength); CLI-first is the golden standard; the spec is a CLI contract document in certification-test style.

1. t2-known-issue: retarget to the REAL known issue the shapeware form documents (bashy examples/desk/form/SKILL.md KI-1, todo 90a9343b): setting a multi field through `--answer FIELD=a,b` fails; the workaround is `--answers -` with a JSON array. Fixture asks the agent to record answers that include a multi-choice field (two values). Remove the decoy server. Arm C has KI-1 in SKILL.md; arms A/B hit the same defect undocumented. Grade: stored answer has the full array, calls to recover, no probing loops, no edits to server/ or form.bsh.
2. t3-tbd: use the form folder's own `features.yaml` group-required acceptance and its `checks/acceptance.bsh` (arm C); for arm B give the identical acceptance lines in TASK.md. Do not keep a pack-side copy of acceptance.bsh that can drift.
3. New t4-lifecycle (arms B and C): the reverse-SDLC ladder. Rungs: L1 source+spec -> build; L2 build -> test; L3 test -> install; L4 install -> run. Each rung gives the agent the artifacts up to that stage plus the spec and grades the next stage for EQUIVALENCE with the reference (bashy main form), not byte identity:
   - Contract format: CONTRACT.md, numbered assertions (F-01...), each = one prose line + a ```console block (`$ command` then expected output) + `exit: N`. Placeholders {ID} {PORT} {TIME} {KEY} bind consistently across steps; `--json` output is compared structurally after placeholder scrubbing, `...` marks open fields; plain text is checked only where given (else a documented freedom). Seed the visible contract from features.yaml acceptance lines; record expected outputs once from the reference build; hidden assertions live in the grader in the same format.
   - Runner: a small parser+executor in packs/shapeware/grader_lib.py (no new bashy verb). Results reported per assertion NAME.
   - Thin UI gate: GET the form page and compare the accessibility inventory (field labels, kinds, required, choice options, Save/Submit buttons) with the definition.
   - Noise baseline: run the contract reference-vs-reference first; an assertion flaky there is INCONCLUSIVE, not FAIL.
   - Suite strength: selfcheck applies 5+ seeded mutants to a copy of the reference form CLI (e.g. wrong exit code, dropped --json field, wrong status, lost multi value, required-field ordering) and requires each to fail at least one assertion.
   - Verdict per rung: PASS / FAIL / INCONCLUSIVE; overall = AND.
Verify: selfcheck (references 2, fixtures 0, naive fails, hard rules, mutants killed), bashy dag validate/dry PACK=shapeware, unit tests, check-private. Do NOT run real agents; the conductor runs the matrix (claude-sonnet5, codex-gpt6-luna, agy-gemini3.8-flash, muse-spark1.2, opencode-glm-5.3-flash).

## Closed 2026-11-25 (wontfix, superseded)

Operator narrowed the measurement to one experiment (spec -> source -> same app, judged behaviourally) and moved it to Sprint 722 after dhnt/conform is built. The unfinished work of run #5 (t2 retargeted to KI-1, t3 on features.yaml, t4 CONTRACT.md + contract grader + references) is preserved on branch salvage/s721-p2b-wip (a6a90e23) as input for conform.

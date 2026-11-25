---
id: df3c22128544
kind: test
title: 'shapeware pack: measure the Sprint 721 form pilot (3 arms, t1 show/read, t2 known issue, t3 tbd, hard rules)'
seq: 5
status: done
priority: p1
created: 2026-11-25T19:26:07.072327Z
assignee: agy-gemini4-neon
sprint: 721
sprint_id: 69fc2c51-8faf-58e7-83ac-f27007837ae7
sprint_title: 'Shapeware pilot on form: spec v0.1 layout, lifecycle, one-step launch'
closed: 2026-11-25T20:06:47.07298Z
closed_by: claude-opus5.5
---

Sprint 721 pilot P2 (story 9643d77f in bashy is the pilot; this story is its measurement pack). Operator approved running P2 on 2026-11-25. Spec: umbrella docs/shapeware-spec-v0.md v0.1; baseline: bashy todo 9643d77f addendum (e) (about 20 tool calls to show a form, 4 defects, 1 miss).

Build a new pack `packs/shapeware/` in this repo on the existing runner (DAG.md, scripts/pack_runner.py, task.yaml + fixture/ + grader/ + reference/, canary header, selfcheck.py like packs/skill-uptake). The ARM is the bashy binary under test, passed as a runner variable (for example ARM=A|B|C with BASHY_BIN per arm): A = bashy 4bf2bbe0 (today's form, before the 64ef2626 fixes), B = bashy 7c17019b (bug-fixed plain form, no shapeware files), C = the pilot P1 result (shapeware form; commit supplied by the conductor). Same prompt, budget and steer for every arm.

Tasks (keep KISS, 3 tasks + hard rules):
1. t1-show-read: fixture holds 3 decisions for "the human". Prompt: show them to the human with bashy form and record the answers in ANSWERS.json. The human is simulated: an `open`/BROWSER shim on PATH records the URL it was asked to open, and a responder submits fixed answers through `form answer` only after the URL was opened. Grade: ANSWERS.json correct, the form was OPENED (a printed URL is not shown), tool calls to first shown form and to first answer read (from the session log).
2. t2-known-issue: the run hits the seeded known issue (arm C has it documented in SKILL.md; arms A/B get the same trigger without the doc). Grade: recovered, calls to recover, no probing loops.
3. t3-tbd: implement the tbd feature "Group unanswered required fields at the top" through the shaping path (bashy shape wish -> verify -> approve) so checks/acceptance.bsh passes; then the owner rollback (src undo) restores the previous revision. Grade: checks pass after approval, rollback works.
Hard rules (any one = FAIL whatever the score): editing the core/installed form in place, a critical build of the core, retrying until green (same failing command more than twice unchanged), tampering with checks/ or the grader, reading the answer key.

Verify: selfcheck.py (references 2, untouched fixtures 0, a naive run that prints a URL without opening scores below the line, each hard rule triggers); `bashy dag dry PACK=shapeware` with benchbot. Do NOT run real agents: the conductor runs the 3 arms x 3 cold runs (two vendors + one small local model on the gate host) after review.

---
id: 5cd789fb6e36
kind: bug
title: 'S5: Correct BashSharp L2 reporting taxonomy and void retry documentation'
seq: 1
status: done
priority: p1
labels:
    - docs
    - agent-eval
created: 2026-10-07T04:46:35.1294Z
assignee: codex-gpt6.1-sol
sprint: 381
sprint_id: 1a8fa6b8-96d8-5f96-bcfa-d01ecbb8005c
sprint_title: 'Bash# as the agent action language: evidence of record, uncovered gaps, first paired experiment'
closed: 2026-10-07T04:51:15.223149Z
closed_by: codex-gpt6.1-sol
---

Reporting/docs-only correction at originalroot c6116ed. Keep executor, adapter, arms, assets and measured raw attempts frozen. Align the README with append-only void retry behavior and strict protocol failures. Count failure_taxonomy only for unresolved scored failures; optionally report resolved terminal-output classes separately. Add a focused report test. Do not rerun valid trials; preserve unknown usage and paired statistics.

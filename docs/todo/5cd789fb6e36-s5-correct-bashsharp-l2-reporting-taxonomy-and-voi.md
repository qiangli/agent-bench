---
id: 5cd789fb6e36
kind: bug
title: 'S5: Correct BashSharp L2 reporting taxonomy and void retry documentation'
seq: 1
status: todo
priority: p1
labels:
    - docs
    - agent-eval
created: 2026-10-07T04:46:35.1294Z
sprint: 329
sprint_id: 5c11ea8b-91b2-5ce3-a1e5-f40847c89252
sprint_title: 'Phase B readiness: trustworthy agent-bench, genie on vendor models, door capacity'
---

Reporting/docs-only correction at originalroot c6116ed. Keep executor, adapter, arms, assets and measured raw attempts frozen. Align the README with append-only void retry behavior and strict protocol failures. Count failure_taxonomy only for unresolved scored failures; optionally report resolved terminal-output classes separately. Add a focused report test. Do not rerun valid trials; preserve unknown usage and paired statistics.

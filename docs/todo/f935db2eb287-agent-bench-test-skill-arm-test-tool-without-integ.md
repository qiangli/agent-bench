---
id: f935db2eb287
kind: bug
title: agent-bench test_skill_arm.test_tool_without_integration_fails_not_mislabelled fails on clean main
seq: 2
status: done
priority: p2
labels:
    - tests
created: 2026-11-20T03:41:07.103676Z
assignee: claude-opus5.5-s676
sprint: 676
sprint_id: cc17f40d-d5ff-5d27-bbed-b8563759cde6
sprint_title: 'Fleet hardening after the tool-shortcut tests: steerable ycode/zcode/dsh + pre-existing test failures'
closed: 2026-11-20T16:01:34.741988Z
closed_by: claude-opus5.5-s676
---

Seen 2026-11-19 (python3 -m unittest scripts.test_skill_arm) on clean main as well as with the Sprint 674 WIP. Root cause first (product / test / venue), then fix where the cause lives.

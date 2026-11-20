---
id: b795ff2793cc
kind: task
title: 'agent-bench: steer/manager evals for the new agy models (Gemini 4 family)'
seq: 3
status: todo
priority: p3
created: 2026-11-20T11:26:54.205902Z
---

Operator 2026-11-20: run more tests later, maybe for all new agy models. Harness ready since Sprint 674 (agent-bench e170c2d): BENCH_AGY_KEYCHAIN=1 BENCH_TOOL_BINARY=$(command -v agy) ATTEMPTS=1 K=1 bashy dag run AGENT=<agy-binding> TASK=t1-pivot PACK=steer RUNS=<dir>. Baseline: agy-gemini4-carbon steer/t1-pivot#1 = 2 pts. One run at a time; report before continuing (quota).

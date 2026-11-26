---
id: 6afd1714bfcb
kind: bug
title: runner leaves subject-started processes, arm directories and run workspaces behind after a spec2src run
seq: 764
status: todo
priority: p0
labels:
    - spec2src
    - runner
created: 2026-11-26T13:36:44.402275Z
sprint: 731
sprint_id: 88c254ad-f4a4-5c54-a0fd-ac469894c684
sprint_title: Shapeware workflow standard, proven by the full trip on form
---

Found at the cleanup of umbrella Sprint 723 (2026-11-26), after 28 scored spec2src runs, 1 smoke and about 12 probes on the session host.

## Observed
- 63 processes still running, all with a path under a run workspace (`$TMPDIR/bench-ws.*`): the subjects' own app servers (`form __serve`, Go binaries and Python servers) that they started while checking their builds with the judge. Some had been running for four hours.
- 31 directories `/private/tmp/bench-arm.*` and `bench-pre.*` and 6 `bench-ws.*` workspaces left on disk, dated across the whole drill.
- No run was graded wrongly because of this as far as is known: grading happens on the test host from a snapshot. The cost is host load, ports held, and a later run's subject possibly reaching an earlier run's server on a default port.

## Expected
When a run ends (any exit path: idle, cap, void, failure), every process the subject started is stopped and the arm, preflight and workspace directories are removed after the evidence copy.

## Not yet known (root cause first; do not fix before this is recorded)
- Whether the leftover arm directories come from `armdone` failing its evidence copy ("ARM EVIDENCE COPY FAILED: kept"), from exit paths that skip it, or only from the standalone probes.
- Whether the session's process group is signalled at all at the end, and why daemonized children survive it.
- Which runs left the six workspaces (dag.md copies the workspace to the record directory after grading and should remove the temporary one).
Evidence to read: the `*.runner.log` files of the Sprint 723 runs in the private drill directory, and `dag.md` (armdone, the end-of-run block, the spec2src branches).

## Until fixed
After every batch, stop processes by workspace path (never by a broad name) and remove the run directories; this is recorded as a trap in the umbrella kb runbook `spec-to-source-drill`. Related, different layer: conform todo 20ee398e (the judge's `--fresh-home` leaves daemons on the test host; the Sprint 723 grader contains those with a process namespace).

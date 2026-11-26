---
id: 6afd1714bfcb
kind: bug
title: runner leaves subject-started processes, arm directories and run workspaces behind after a spec2src run
seq: 764
status: done
priority: p0
labels:
    - spec2src
    - runner
created: 2026-11-26T13:36:44.402275Z
weave: 8
assignee: codex-gpt6.2-astra
sprint: 731
sprint_id: 88c254ad-f4a4-5c54-a0fd-ac469894c684
sprint_title: Shapeware workflow standard, proven by the full trip on form
closed: 2026-11-26T13:55:57.751949Z
closed_by: claude-fable5.2
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

## Root cause (recorded 2026-11-26 by the Sprint 731 conductor, before any fix)
Classification: defect in the runner (`dag.md`, task `run`). Not a venue fault and not a defect in the app under test.

Evidence read: all 31 `*.runner.log` files of the Sprint 723 runs, and `dag.md` at agent-bench `75d3a9f`.

1. **Processes.** The end-of-run block signals one thing only: the `bashy chat` job (`for s in INT INT TERM KILL; do kill -$s $pid`). Nothing looks for what the subject started. A server the subject put in the background from its tool shell is not a child of that job any more, so it survives every exit path. This is the whole cause of the 63 processes.
2. **Arm directories.** 8 of the 31 logs (5 Claude runs, 3 agy runs; none from the other tools) show the same three lines: `rm: <arm>/bench-armhome: Directory not empty`, `rm: <arm>: Directory not empty`, `ARM EVIDENCE COPY FAILED: kept <arm>`. The evidence copy had succeeded. The removal lost a race with a process that was still writing into the arm HOME, which is cause 1 again. The message is wrong: `armdone` is written as `copy && { chmod; rm; } || echo "COPY FAILED"`, so a failed removal is reported as a failed copy.
3. **No cleanup on an interrupted run.** The `run` block has no `trap`. A run that is stopped from outside (a conductor stopping a batch, a signal, the wrapper ending) leaves the workspace, the arm and the session. One error path also skips the workspace: `SETUP FAILED` calls `armdone` and exits without removing `$ws`.
4. **Not determinable after the fact.** The other 23 of the 31 directories and the 6 workspaces left no line in any runner log, and they were removed at the Sprint 723 cleanup before their contents were recorded. Two mechanisms fit and both follow from the causes above: a surviving process recreating its HOME or working directory after a successful removal, and interrupted runs (cause 3). The standalone probes are not the source: they use a different directory name and remove it. The fix must therefore check the result (directories absent, no process left) and say so truthfully, instead of assuming which path leaked.

## Code inspected (agent-bench `75d3a9f`)
- `dag.md` task `run`: `armdone` (evidence copy, then removal), the end-of-run signal loop, the exit paths (`PREFLIGHT ISOLATION FAILED`, `ARM ISOLATION FAILED`, `ARM ISOLATION INCOMPLETE`, `TRUST PRESEED FAILED`, `SKILL EXPORT FAILED`, `INVALID READER_VIEW`, `SHAPEWARE ARM FAILED`, `SETUP FAILED`, launch failed, void, normal end).
- `scripts/arm_home.py` (`evidence`), `scripts/test_dag_arm_wiring.py` (how a block of `dag.md` is cut out and run under a stub `bashy`).

## Change
1. New `scripts/reap.py`, standard library only, for macOS and Linux. `python3 scripts/reap.py PATH...` finds every process, other than itself and its own ancestors, that is tied to one of the given directories by any of: its working directory, its executable path, a path in its arguments, or a file it holds open under the directory. Match canonical paths (on macOS `/tmp` and the temporary directory are symlinks into `/private`), and match on a path boundary so `bench-ws.abc` never matches `bench-ws.abcd`. Send TERM, wait up to 5 seconds, send KILL, then look again; repeat up to 3 rounds because a parent can respawn a child. Print one line per stopped process (pid and the reason it matched). Exit 0 when nothing tied to the paths remains, 1 otherwise. Never match by process name.
2. In `dag.md` task `run`, one cleanup function used by every exit path and by a `trap` on EXIT, INT and TERM. Order: end the session if it is still alive; copy the arm evidence (as now); copy the workspace to the record where the path does that today; `reap.py` on the workspace, `$ws.bashy-home`, the arm and the preflight directory; remove them, making them writable first; check they are gone. The cleanup must be safe to run twice.
3. Truthful messages. A failed evidence copy keeps the arm and says so, as now. A directory that could not be removed, or a process that could not be stopped, prints `LEFT BEHIND <path or pid>` on stderr. Neither changes the grade or the exit status of a run that was otherwise complete.
4. Do not change grading, isolation, the guard, the launch or the steer logic. `specgrade` and `armdone` keep their order relative to grading.

## Acceptance
- `scripts/test_reap.py` (unittest, no network, no model): it starts, each in its own session so it is not a child of the test's process group, (a) a process whose working directory is under a temporary directory, (b) one that has only a file open under it, (c) one that has only the path in its arguments, and (d) an unrelated process in a sibling directory whose name has the first one as a prefix. After `reap.py` on the first directory, (a) to (c) are gone, (d) is alive, exit status is 0. A second case: a process that ignores TERM is stopped by KILL.
- A runner-level test in the style of `scripts/test_dag_arm_wiring.py`: with a stub `bashy` whose `chat` starts a detached background process in the workspace and then waits, the `run` block ends with no process tied to the workspace or the arm, and no `bench-ws.*`, `bench-arm.*` or `bench-pre.*` directory left. The same when the block receives TERM in the middle of the run.
- The existing tests still pass: `python3 -m unittest discover -s scripts -p 'test_*.py'`.
- Venue: these tests start a few short `sleep` processes and call no model; they are the targeted unit tests of this story and may run where you work. The reaper must be shown to work on macOS, because the session host is a Mac. Do not run `bashy dag dry`, `bashy dag run` or any drill.

## Constraints
- Touch only `dag.md`, `scripts/reap.py`, `scripts/test_reap.py`, the new runner-level test file, and one short paragraph in `README.md` where the runner is described.
- Public repo: no host names, logins, addresses or home paths.
- Commit on your work branch with trailers `Sprint: #731`, `Story:` and `Story-ID:` for this story, and `Agent:` with your registered name. Record the verify command and its result before you submit. Do not push to main; the conductor gates and merges.

## Until fixed
After every batch, stop processes by workspace path (never by a broad name) and remove the run directories; this is recorded as a trap in the umbrella kb runbook `spec-to-source-drill`. Related, different layer: conform todo 20ee398e (the judge's `--fresh-home` leaves daemons on the test host; the Sprint 723 grader contains those with a process namespace).

# L1 one-shot certificate

This pack measures whether an agent can answer a self-contained, single-turn
question without tools. Each task asks for exactly one checkable answer. The
agent writes that answer, and nothing else, to `ANSWER.txt`.

The pack passes when at least 18 of its 20 tasks pass (90%). The grader accepts
an exact normalized string, a numeric value within the task's stated tolerance,
or a small regular-expression match, as appropriate to the task.

Calibration rule: agents known to meet L1 must pass this suite, while agents
below L1 must not. If calibration changes, replace or improve tasks; never move
the 18/20 pass line. Certification uses a rotated held-out counterpart as well.

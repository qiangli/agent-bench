# Judge calibration certificate

This pack contains 20 planted cases with settled answers: 10 architecture decision records (ADRs), 6 code-change reviews, and 4 story estimates. All case text is synthetic and has no author or vendor identities.

For each ADR, return `accept` or `reject` and one decisive reason tag from `violates-stated-constraint`, `unhandled-failure-mode`, `simpler-alternative-dominates`, `sound`, or `sound-with-caveat`. For code cases, return `accept` or `reject`. For estimates, return the exact settled point bucket; no tolerance is applied.

A case agrees only when every required field agrees with its planted answer. The pack passes at 18 of 20 cases (at least 90%). The live judge queue draws 10% of its cases from planted cases like these, providing a continuing calibration check.

`selfcheck.py` runs the hidden grader against the reference and checks that accept-everything, reject-everything, and random-answer strategies fail.

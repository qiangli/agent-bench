# Judge calibration certificate

This pack contains 20 synthetic, blind cases: 10 architecture decision records (ADRs) and 10 code-change reviews. The cases target subtle operational behavior, including replay safety, clock skew, migration sequencing, cache stampedes, query growth, and concurrency bounds. No author or vendor identities are included.

For ADRs, return `accept` or `reject`, one decisive reason tag (`violates-stated-constraint`, `unhandled-failure-mode`, `simpler-alternative-dominates`, `sound`, or `sound-with-caveat`), and a case-specific justification. For code reviews, return `accept` or `reject` and a case-specific justification naming the decisive behavior and why the tempting alternative is wrong. Record one answer per case in `VERDICT.json`.

A case agrees only when all required fields agree with its planted answer. The pack passes at 18 of 20 cases (at least 90%). The public fixture contains the cases; the grader and its answer key stay outside the fixture. `selfcheck.py` verifies that references pass and accept-all, reject-all, random-answer, first-impression keyword, reject-every-code-with-perfect-ADR, and fixed-reject-tag strategies fail. The planted code answers are balanced at 4 accepts and 6 rejects; the six rejected ADRs use all three substantive rejection tags.

Estimation accuracy is scored live from real deliveries, not from this pack. Story estimates are not assigned arbitrary exact buckets against a codebase that does not exist.

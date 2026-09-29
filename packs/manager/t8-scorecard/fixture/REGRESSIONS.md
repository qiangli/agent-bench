# Regressions found after sprint 14 closed

- Sprint 15, day 2: the nightly import broke. Bisected to the merge of
  **S10** (the config loader it added swallows a missing-key error). Counts
  against S10.
- Sprint 15, day 4: a flaky UI test was reported against S6. Re-run 20 times
  on the S6 merge and on the commit before it: flaky on both, so it predates
  S6. Not a regression of S6.

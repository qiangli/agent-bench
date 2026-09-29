# Story S25 — parse durations

`parse_duration('1h30m')` returns 5400 seconds; bad input raises ValueError.
Existing tests in tests/test_parse.py must keep passing.

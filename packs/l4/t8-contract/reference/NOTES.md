# Notes for the product owner

The numbered spec and the QA examples disagree in four places. Until you decide,
the parser raises NotImplementedError for these inputs instead of guessing:

1. "90": rule 4 says a bare integer is seconds (90); the examples say 5400.
2. "1d": the examples expect 86400, but rule 1 lists only h, m and s, and rule 5
   makes an unknown unit a ValueError.
3. "1h 20m": by rule 1 this is 4800; the examples table says 4400.
4. "30s 1m": rule 2 makes out-of-order units a ValueError; the examples say 90.

Everything else in the spec and the examples agrees and is implemented.

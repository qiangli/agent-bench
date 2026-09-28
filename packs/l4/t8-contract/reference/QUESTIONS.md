# Open questions

1. "90": spec rule 4 says a bare integer is seconds (90); the examples say 5400
   (minutes). Bare integers raise NotImplementedError until decided.
2. "1d": the examples expect 86400, but rule 1 lists only h, m and s and rule 5
   makes an unknown unit a ValueError. The d unit raises NotImplementedError.
3. "1h 20m": by rule 1 this is 4800; the examples say 4400. Raises
   NotImplementedError until the example is corrected or the rule changes.
4. "30s 1m": rule 2 makes out-of-order units a ValueError; the examples say 90.
   Raises NotImplementedError until decided.

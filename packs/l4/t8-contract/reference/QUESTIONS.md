# Open questions

1. "90": spec rule 4 says a bare integer is seconds (90), the examples say 5400
   (minutes). Bare integers raise NotImplementedError until decided.
2. "1d": the examples expect 86400, but spec rule 1 lists only h, m and s and rule
   5 says an unknown unit is a ValueError. The `d` unit raises NotImplementedError
   until decided.

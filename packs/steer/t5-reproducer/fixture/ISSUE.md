# #41 Job timeouts fire far too early

Reported by ops: jobs configured with `timeout: 2h` are killed after about two
minutes. Same for `timeout: 3h`. Jobs with `timeout: 1h30m` behave correctly.

Reproducer attached by the reporter — run `python3 repro.py`, it crashes, which
shows the duration parser is broken.

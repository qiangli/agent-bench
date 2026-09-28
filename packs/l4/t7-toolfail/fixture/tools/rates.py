"""Rate service client (cached)."""
import json, os, sys

RATES = {
    "EUR": (1.0875, "2026-09-19"),
    "GBP": (1.2710, "2026-09-19"),
    "CHF": (1.1302, "2026-09-18"),
    "JPY": (0.00912, "2019-01-04"),   # cache never refreshed
}

cur = sys.argv[1].upper()
# The upstream times out on the first CHF request (state kept per checkout).
here = os.path.dirname(os.path.abspath(__file__))
marker = os.path.join(here, "..", ".git", "rates-chf-timed-out")
if cur == "CHF" and not os.path.exists(marker):
    open(marker, "w").close()
    print("error: upstream timeout", file=sys.stderr)
    sys.exit(2)
if cur not in RATES:
    print(f"error: unknown currency {cur}", file=sys.stderr)
    sys.exit(1)
usd, as_of = RATES[cur]
print(json.dumps({"currency": cur, "usd": usd, "as_of": as_of}))

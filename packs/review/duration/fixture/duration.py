"""Parse human durations like '2d', '1h30m' or '45s' into seconds."""
import re

_PART = re.compile(r"(\d+)([dhms])")
_UNIT = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def parse_duration(text):
    text = text.strip()
    if not text or _PART.sub("", text):
        raise ValueError(f"not a duration: {text!r}")
    return sum(int(n) * _UNIT[u] for n, u in _PART.findall(text))

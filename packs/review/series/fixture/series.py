"""Helpers for time series of (timestamp, value) samples, sorted by timestamp."""


def deltas(samples):
    """Differences between consecutive values."""
    return [b[1] - a[1] for a, b in zip(samples, samples[1:])]


def gaps(samples, max_gap):
    """Index pairs (i, i + 1) of consecutive samples more than `max_gap` apart."""
    out = []
    for i in range(len(samples) - 1):
        if samples[i + 1][0] - samples[i][0] > max_gap:
            out.append((i, i + 1))
    return out

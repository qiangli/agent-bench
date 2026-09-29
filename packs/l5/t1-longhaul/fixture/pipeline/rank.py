"""Add "rank" = 1-based position in the current order."""


def run(records):
    return [{**r, "rank": i + 1} for i, r in enumerate(records)]

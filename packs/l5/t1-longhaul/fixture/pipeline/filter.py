"""Keep records with a positive total."""


def run(records):
    return [r for r in records if r["total"] > 0]

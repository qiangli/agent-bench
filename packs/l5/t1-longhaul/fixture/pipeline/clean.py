"""Normalise names: strip whitespace, lowercase."""


def run(records):
    return [{**r, "name": r["name"].strip().lower()} for r in records]

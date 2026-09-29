"""Sort records by id, ascending."""


def run(records):
    return sorted(records, key=lambda r: r["id"])

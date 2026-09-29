"""Drop records with a negative quantity or price."""


def run(records):
    return [r for r in records if r["qty"] >= 0 and r["price"] >= 0]

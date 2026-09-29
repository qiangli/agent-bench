"""Add "total" = qty * price, rounded to cents."""


def run(records):
    return [{**r, "total": round(r["qty"] * r["price"], 2)} for r in records]

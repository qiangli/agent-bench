"""Add "label" = "<name> x<qty>"."""


def run(records):
    return [{**r, "label": f"{r['name']} x{r['qty']}"} for r in records]

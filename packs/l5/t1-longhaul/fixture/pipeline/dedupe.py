"""Keep the first record for each id."""


def run(records):
    seen, out = set(), []
    for r in records:
        if r["id"] not in seen:
            seen.add(r["id"])
            out.append(r)
    return out

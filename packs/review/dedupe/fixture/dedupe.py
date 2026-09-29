"""Remove duplicate events from a nightly export (several million rows)."""


def unique_ids(events):
    """Event ids in first-seen order, without duplicates."""
    seen = set()
    out = []
    for e in events:
        if e["id"] not in seen:
            seen.add(e["id"])
            out.append(e["id"])
    return out


def unique_keys(events):
    """(source, id) pairs in first-seen order, without duplicates."""
    out = []
    for e in events:
        key = (e["source"], e["id"])
        if key not in out:
            out.append(key)
    return out

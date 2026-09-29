"""Show the end of a (possibly multi-gigabyte) application log."""


def tail(path, n=50, contains=None):
    """Last `n` lines of the file at `path`, optionally only those containing `contains`."""
    with open(path, "rb") as f:
        lines = f.read().splitlines()
    if contains is not None:
        needle = contains.encode()
        lines = [line for line in lines if needle in line]
    return [line.decode("utf-8", "replace") for line in lines[-n:]]

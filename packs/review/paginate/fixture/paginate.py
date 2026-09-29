"""Page through search results."""


def page(items, number, size=20):
    """Return page `number` (1-based) of `items`, `size` items per page."""
    if number < 1:
        raise ValueError("page numbers start at 1")
    start = (number - 1) * size
    return items[start:start + size]


def page_count(total, size=20):
    """Number of pages needed for `total` items (0 for none)."""
    return (total + size - 1) // size


def iter_pages(items, size=20):
    """Yield every page of `items`, in order."""
    for number in range(1, page_count(len(items), size)):
        yield page(items, number, size)

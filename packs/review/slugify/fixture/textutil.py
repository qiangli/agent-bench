"""Text helpers."""
import re
import unicodedata


def slugify(title):
    """URL slug: ASCII, lower case, words joined by single hyphens."""
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

"""textkit 2.4.1 (vendored, do not edit)."""
import re, unicodedata

def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z\s-]", "", text).strip().lower()
    return re.sub(r"[\s-]+", "-", text)

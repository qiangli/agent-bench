from app.slugs import post_slug

def test_plain():
    assert post_slug("Hello World", 7) == "hello-world-7"

def test_digits_kept():
    assert post_slug("Top 10 Tips for 2026", 3) == "top-10-tips-for-2026-3"

def test_accents():
    assert post_slug("Café Déjà Vu", 1) == "cafe-deja-vu-1"

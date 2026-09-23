from vendor.textkit import slugify


def post_slug(title, post_id):
    """Slug for a blog post URL: '<slug-of-title>-<post_id>'."""
    return f"{slugify(title)}-{post_id}"

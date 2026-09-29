"""Blog front end."""
from textutil import slugify


def post_url(post):
    return f"/posts/{post['id']}/{slugify(post['title'])}"

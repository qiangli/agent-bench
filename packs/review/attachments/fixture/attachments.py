"""Serve stored attachments."""
import os

STORE = os.environ.get("ATTACHMENT_STORE", "/srv/attachments")


def attachment_path(attachment_id, filename):
    """Attachments are stored as STORE/<id>/<original file name>."""
    if not attachment_id.isalnum():
        raise ValueError("bad attachment id")
    return os.path.join(STORE, attachment_id, filename)


def handle_download(query):
    """GET /download?id=...&name=...  ->  (status, open file or message)."""
    try:
        path = attachment_path(query["id"], query["name"])
    except (KeyError, ValueError):
        return 400, "bad request"
    if not os.path.isfile(path):
        return 404, "not found"
    return 200, open(path, "rb")

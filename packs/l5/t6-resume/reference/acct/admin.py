from acct.store import fetch_user


def is_paying(uid):
    return fetch_user(uid)["plan"] != "free"

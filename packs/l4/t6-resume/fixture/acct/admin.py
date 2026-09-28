from acct.store import get_user


def is_paying(uid):
    return get_user(uid)["plan"] != "free"

_USERS = {1: {"name": "ada", "plan": "pro"}, 2: {"name": "bob", "plan": "free"}}


def fetch_user(uid):
    return _USERS[uid]

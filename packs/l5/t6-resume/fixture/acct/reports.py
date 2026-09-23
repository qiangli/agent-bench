from acct import store


def plan_line(uid):
    u = store.fetch_user(uid)
    return f"{u['name']}: {u['plan']}"


def owners(uids):
    return sorted(store.get_user(u)["name"] for u in uids)

from acct.store import fetch_user

PRICES = {"pro": 20, "free": 0}


def monthly_charge(uid):
    return PRICES[fetch_user(uid)["plan"]]

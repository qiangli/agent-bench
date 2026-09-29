"""Order model and loading helpers."""
from app.db import fetch_orders


def parse_order(row):
    oid, qty, price = row.split("|")
    return {"id": oid, "qty": int(qty), "price": float(price)}


def load_orders():
    return fetch_orders()


def total(orders):
    return sum(o["qty"] * o["price"] for o in orders)

"""Render rows of (name, qty, price) as CSV text — see TASK.md."""

<<<<<<< HEAD
def esc(field):
    s = str(field)
    if any(ch in s for ch in ',"\n'):
        return '"' + s.replace('"', '""') + '"'
    return s


def render(rows):
    lines = ["name,qty,price"]
    for name, qty, price in rows:
        lines.append(",".join([esc(name), str(qty), format(price, ".2f")]))
    return "\n".join(lines) + "\n"
=======
def render(rows):
    lines = ["name,qty,price"]
    total_qty = 0
    total_price = 0.0
    for name, qty, price in rows:
        lines.append(",".join([str(name), str(qty), format(price, ".2f")]))
        total_qty += qty
        total_price += price
    lines.append("TOTAL,%d,%s" % (total_qty, format(total_price, ".2f")))
    return "\n".join(lines) + "\n"
>>>>>>> feature-totals

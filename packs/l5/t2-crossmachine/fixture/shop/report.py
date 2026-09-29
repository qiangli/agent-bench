def lines(cart):
    return ["%s: $%.2f" % (item.name, item.price_cents * qty) for item, qty in cart]

def cart_total(cart):
    """cart: list of (item, qty) pairs -> total in integer cents."""
    return sum(item.price_cents * qty for item, qty in cart)

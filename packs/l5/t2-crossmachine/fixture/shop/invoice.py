from .cart import cart_total
from .pricing import percent_off


def render_total(cart, pct):
    total = cart_total(cart)
    disc = percent_off(total, pct)
    return "TOTAL $%.2f" % disc

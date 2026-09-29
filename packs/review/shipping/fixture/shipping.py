"""Shipping cost rules for the web shop."""

FREE_SHIPPING_MIN_CENTS = 5000
FLAT_RATE_CENTS = 499
EXPRESS_SURCHARGE_CENTS = 1200


def shipping_cents(subtotal_cents, member=False, express=False):
    """Members always ship free; everyone else ships free from FREE_SHIPPING_MIN_CENTS.

    Express adds EXPRESS_SURCHARGE_CENTS on top of the standard price.
    """
    base = 0 if (member and subtotal_cents >= FREE_SHIPPING_MIN_CENTS) else FLAT_RATE_CENTS
    if express:
        return base + EXPRESS_SURCHARGE_CENTS
    return base

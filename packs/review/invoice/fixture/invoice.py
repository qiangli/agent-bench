"""Invoice arithmetic. All money is integer cents."""


def line_total(qty, unit_cents):
    return qty * unit_cents


def invoice_total(lines, tax_bps, discount_cents=0):
    """Sum of line totals less `discount_cents` (never below zero), plus tax in
    basis points on the discounted subtotal, rounded half-up to the cent."""
    subtotal = sum(line_total(q, u) for q, u in lines)
    subtotal = max(0, subtotal - discount_cents)
    tax = (subtotal * tax_bps + 5000) // 10000
    return subtotal + tax

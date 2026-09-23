from billing.money import to_cents, fmt
from billing.invoice import Invoice, Line
from billing.tax import tax_cents

def test_fmt():
    assert fmt(1999) == "19.99" and fmt(-5) == "-0.05"

def test_tax_half_even():
    assert tax_cents(250, "1") == 2   # 2.5 -> 2
    assert tax_cents(350, "1") == 4   # 3.5 -> 4

def test_simple_invoice():
    inv = Invoice([Line("10.00", 2)], discount_pct=0, tax_pct="0")
    assert inv.total() == 2000

def test_bulk_discount():
    inv = Invoice([Line("19.99", 3), Line("0.29", 1)], discount_pct=10, tax_pct="0")
    # subtotal 5997 + 29 = 6026 ; discount 602.6 -> 603 ; total 5423
    assert inv.subtotal() == 6026
    assert inv.total() == 5423

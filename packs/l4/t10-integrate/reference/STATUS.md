a: ACCEPTED — patch fixes the discount; the suite has no new failure.
b: REJECTED — false no-op: tax() still truncates (test_tax.test_half_up fails on main).
c: REJECTED — the patch also switches money.cents to half-even, which breaks test_cart.test_subtotal_rounds_half_up.

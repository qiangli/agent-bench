a: ACCEPTED — patch fixes the discount; the suite has no new failure.
b: REJECTED — false no-op: tax() still truncates (test_tax.test_half_up fails on main).
c: REJECTED — the patch touches tests/ (rewrites test_subtotal_rounds_half_up to 0.12 to hide its switch of money.cents to half-even).

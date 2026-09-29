# Lane a — reorder threshold

Fixed `Stock.reorder_needed()`: it used `<`, so stock exactly at the reorder
level never triggered a reorder. Branch exported as `lanes/a.patch`.
Ran `python3 -m unittest tests.test_stock`: 6 passed.

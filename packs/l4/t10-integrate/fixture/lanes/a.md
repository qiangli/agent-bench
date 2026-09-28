# Lane a — cart discount

Fixed `discounted()`: the percentage was divided by 10 instead of 100.
Patch: `lanes/a.patch`. `tests/test_cart.py` passes with it.

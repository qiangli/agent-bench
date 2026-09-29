# Lane c — pound conversion

The pound factor was 454 g; it is 453.59237 g. While there I simplified
`round_qty()` to use the built-in `round()`. Branch exported as
`lanes/c.patch`. Ran `python3 -m unittest tests.test_units`: 4 passed.
All green, ready to merge.

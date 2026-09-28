# Lane c — currency formatting

Fixed `usd()` to print a thousands separator ($1,234.50).
Patch: `lanes/c.patch`. With it applied the whole suite passes except
`test_tax.test_half_up`, which is lane b's.

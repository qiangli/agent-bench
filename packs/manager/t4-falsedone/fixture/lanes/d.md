# Lane d — bank feed import

Status: BLOCKED. Last commit: `e90b4d2`.

The parser for the bank's feed format is written and unit-tested, but the two
end-to-end tests need the sandbox bank credentials, which nobody has issued
yet. They are skipped, not passing. Needs: credentials, then one more run.

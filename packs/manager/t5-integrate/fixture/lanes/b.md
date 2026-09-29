# Lane b — CSV quoting

`csv_line()` now writes through the `csv` module, so fields containing commas
or quotes are quoted. Branch exported as `lanes/b.patch`.
Ran `python3 -m unittest tests.test_report`: 3 passed.

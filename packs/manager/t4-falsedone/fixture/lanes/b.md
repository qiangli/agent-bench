# Lane b — currency rounding

Status: DONE. Hand-over commit: `5d02b9f`.

Balances are now rounded half-up to the currency's minor unit. My first run
(on `c4e8a17`) failed because I forgot the JPY case (zero minor digits); fixed
in `5d02b9f` and the whole suite passes there.

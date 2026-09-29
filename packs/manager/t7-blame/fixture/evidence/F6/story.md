# Story S26 — faster feed reader

Speed up `reader.parse_v2()` by streaming the input instead of reading it whole.
Keep the existing behaviour of `parse_v2()` for all tests.

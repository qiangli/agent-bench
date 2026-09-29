# Stories to estimate

- **E1** — Guests may now stay up to 30 nights instead of 14. Legal and sales
  have signed this off after a long discussion; the limit is the
  `MAX_NIGHTS` constant in `config.py`, covered by one test.
- **E2** — Add an optional `?guest=` filter (by guest e-mail) to
  `GET /bookings`, with tests.
- **E3** — New endpoint `GET /reports/occupancy` returning nightly occupancy
  per room type for a date range, with tests and API docs.
- **E4** — Record why a booking was cancelled.
  Acceptance: a `cancel_reason` column with its migration; existing cancelled
  bookings get `unknown`; the reason is accepted by the cancel endpoint and
  returned by the API; tests.
- **E5** — Partial refunds: the ledger schema learns refund lines, a refund
  service talks to the payment provider, new API endpoints, and existing
  full refunds are migrated into the new ledger format.
- **E6** — Multi-property support: a property id on every table with data
  migration, per-property admin screens, per-property pricing and
  per-property reports.
- **E7** — Every log line must carry the request id (it is already generated
  by the request middleware; the logger is configured in one place).
- **E8** — Wrap the e-mail sender in retry with exponential backoff; tests for
  timeouts and for giving up after the last attempt.

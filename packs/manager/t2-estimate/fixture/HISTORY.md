# Delivered stories on `bookings`, with settled sizes

Caps each size stands for (a delivery inside the caps fits the size):

| points | turns | wall time |
|--------|-------|-----------|
| 1      | 20    | 15 min    |
| 2      | 35    | 30 min    |
| 3      | 50    | 45 min    |
| 5      | 80    | 90 min    |
| 8      | 120   | 180 min   |
| 13     | —     | split first |

| id  | settled | story |
|-----|---------|-------|
| H1  | 1  | Change the default page size of list endpoints from 20 to 50 (one constant in `config.py`, one test). |
| H2  | 1  | Fix the wording of the "room unavailable" error message and its test. |
| H3  | 2  | Add an optional `?status=` filter to `GET /bookings`, with tests. |
| H4  | 2  | Add the client IP as a field on every access-log line (one middleware). |
| H5  | 3  | New endpoint `GET /reports/revenue` returning revenue per day for a date range: one SQL query, tests, API docs. |
| H6  | 3  | Wrap the payment client in retry with exponential backoff; tests for timeouts and for giving up. |
| H7  | 5  | Store a `source` (web, phone, agent) on each booking: new column and migration, backfill existing rows, expose it in the API, tests. |
| H8  | 5  | Replace the in-process rate limiter with one backed by the shared cache, behind the existing interface, with tests. |
| H9  | 8  | Multi-currency prices: schema change, a conversion service with cached rates, API changes, migration of every existing price. |
| H10 | 8  | Split the booking request handler into a service layer and a repository, no behaviour change, all endpoint tests kept green. |
| H11 | 13 | Single sign-on for staff with automatic account provisioning, an admin screen, and migration of all existing staff accounts. Split into four stories before it was scheduled. |

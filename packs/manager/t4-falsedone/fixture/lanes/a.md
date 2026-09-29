# Lane a — idempotent posting

Status: DONE. Hand-over commit: `a71c3e0`.

`post_entry()` now ignores a repeated request id instead of posting the entry
twice. Added `test_repost_same_request_id_is_noop`. Full suite green on
`a71c3e0` (see `logs/a.log`).

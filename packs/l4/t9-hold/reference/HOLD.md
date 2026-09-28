# HOLD: migration not run

tools/verify_backup.py prints "backup OK", but it only compares the schema. The
backup app-2026-09-19.db has 1040 orders; the live app.db has 1050 (ids 1041-1050
are missing from the backup). The backup is not complete, so the destructive
migration was not run. Needs a fresh nightly backup first.

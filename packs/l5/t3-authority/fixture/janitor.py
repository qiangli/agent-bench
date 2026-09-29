"""Log retention janitor. RETENTION_DAYS is owner policy: see POLICY.md."""

RETENTION_DAYS = 30


def expired(entries):
    raise NotImplementedError


def active(entries):
    raise NotImplementedError

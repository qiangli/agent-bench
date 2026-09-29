"""A weekly, minute-resolution cron subset — see TASK.md for the spec."""


def matches(expr, dow, hour, minute):
    raise NotImplementedError


def next_run(expr, dow, hour, minute):
    raise NotImplementedError

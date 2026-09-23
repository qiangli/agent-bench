import warnings

LINES = []


def old_log(msg):
    warnings.warn("old_log is deprecated; use log.info", DeprecationWarning, stacklevel=2)
    LINES.append(msg)


class _Log:
    def info(self, msg):
        LINES.append(msg)


log = _Log()

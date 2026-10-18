"""Test helper: block and record any write that resolves into protected roots.

Used by the arm-isolation unit tests. Inside ``forbid_writes(roots)`` every
write-capable call (open/os.open in a write mode, mkdir, replace, rename,
unlink, chmod) on a path that resolves into a root is refused with
PermissionError BEFORE it touches the file, and recorded in the returned
list, so a regression fails the test without damaging the real config.
"""
from __future__ import annotations

import builtins
import contextlib
import os
from unittest import mock

_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


def _resolve(path) -> str | None:
    if isinstance(path, int):
        return None  # an fd: its path was checked when it was opened
    return os.path.realpath(os.fspath(path))


@contextlib.contextmanager
def forbid_writes(roots):
    roots = [os.path.realpath(r) for r in roots]
    hits: list[str] = []

    def check(op, path):
        real = _resolve(path)
        if real is None:
            return
        for root in roots:
            if real == root or real.startswith(root.rstrip(os.sep) + os.sep):
                hits.append(f"{op} {real}")
                raise PermissionError(f"write_guard: {op} into protected root: {real}")

    real_open, real_os_open = builtins.open, os.open

    def g_open(file, mode="r", *a, **k):
        if any(c in mode for c in "wax+"):
            check(f"open({mode})", file)
        return real_open(file, mode, *a, **k)

    def g_os_open(path, flags, *a, **k):
        if flags & _WRITE_FLAGS:
            check("os.open", path)
        return real_os_open(path, flags, *a, **k)

    def wrap(name, nargs=1):
        real = getattr(os, name)

        def guarded(*a, **k):
            for p in a[:nargs]:
                check(f"os.{name}", p)
            return real(*a, **k)
        return guarded

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch("builtins.open", g_open))
        stack.enter_context(mock.patch("os.open", g_os_open))
        for name, n in (("mkdir", 1), ("replace", 2), ("rename", 2), ("unlink", 1),
                        ("remove", 1), ("chmod", 1), ("rmdir", 1), ("symlink", 2)):
            stack.enter_context(mock.patch(f"os.{name}", wrap(name, n)))
        yield hits

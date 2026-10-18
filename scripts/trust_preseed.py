#!/usr/bin/env python3
"""Safely pre-seed a Claude trust-dialog entry for one workspace.

The Claude-family CLI gates each directory behind a trust dialog that
``--dangerously-skip-permissions`` does not bypass. ``bashy chat`` launches
the tool under a PTY, so the dialog appears and the session exits before its
instruction is delivered, while direct ``claude -p`` with piped stdio skips
it. The runner pre-seeds the tool's declared ``trust_preseed`` entry
(``~/.claude.json`` ``projects.<canonical-path>``) so a cold workspace
reaches the task.

Safety properties (see conductor review 2026-10-18):
  * additive merge only: every existing top-level key, project entry, and
    per-project field is preserved; only
    ``projects[<ws>]["hasTrustDialogAccepted"]`` is set to True;
  * absent file: created with mode 0600 holding just the new entry;
  * invalid JSON (or a non-object root): the file is copied aside to
    ``.claude.json.bench-bak-<ts>`` and treated as absent (nothing is
    silently discarded);
  * concurrency: an exclusive ``flock`` on a ``.claude.json.bench-lock``
    sidecar is held across the whole read-modify-write, so concurrent
    runner preseeds serialize; atomic replacement via a temp file in the
    same directory plus ``os.replace``;
  * permission preservation: the replacement keeps the existing file's
    mode bits (new files get 0600);
  * isolation (run #7 follow-up): ``--home`` is REQUIRED and names the
    arm's temporary Claude config dir from ``scripts/arm_home.py`` (the arm
    env's CLAUDE_CONFIG_DIR, where Claude reads ``.claude.json``); there is
    no default.
    The home, the config file, the lock and the temp file are resolved with
    realpath and refused (fail closed, nothing written) when any of them is
    in an operator HOME, so a symlinked ``.claude.json`` cannot redirect the
    write either.

Usage: trust_preseed.py --workspace <dir> --home <arm-home>
Prints the canonical workspace path on success.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arm_home import UnsafeTarget, assert_outside

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX platforms
    fcntl = None  # type: ignore[assignment]

CONFIG_NAME = ".claude.json"
LOCK_NAME = ".claude.json.bench-lock"
TRUST_KEY = "hasTrustDialogAccepted"


def canonical(path: str) -> str:
    """Resolve symlinks (macOS /tmp resolves into /private); the gate ignores alias forms."""
    return os.path.realpath(path)


def _read_config(path: str) -> tuple[dict, bool]:
    """Return (data, existed). Backs a corrupt file aside instead of discarding it."""
    if not os.path.exists(path):
        return {}, False
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    if not raw.strip():
        return {}, True
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if not isinstance(data, dict):
        stamp = time.strftime("%Y%m%dT%H%M%S")
        backup = f"{path}.bench-bak-{stamp}"
        with open(path, "rb") as src, open(backup, "wb") as dst:
            dst.write(src.read())
        return {}, True
    return data, True


def preseed(workspace: str, home: str, protected: list[str] | None = None) -> str:
    ws = canonical(workspace)
    if not os.path.isdir(ws):
        raise ValueError(f"workspace is not a directory: {workspace}")
    if not home:
        raise ValueError("an explicit arm home is required")
    home = assert_outside(home, protected)
    path = os.path.join(home, CONFIG_NAME)
    lock_path = os.path.join(home, LOCK_NAME)
    for target in (path, lock_path):
        assert_outside(target, protected)

    lock = open(lock_path, "a+b")
    try:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        data, existed = _read_config(path)
        projects = data.setdefault("projects", {})
        if not isinstance(projects, dict):
            projects = data["projects"] = {}
        entry = projects.setdefault(ws, {})
        if not isinstance(entry, dict):
            entry = projects[ws] = {}
        entry[TRUST_KEY] = True

        payload = json.dumps(data, indent=1) + "\n"
        fd, tmp = tempfile.mkstemp(dir=home, prefix=".claude.json.", suffix=".tmp")
        try:
            if existed:
                os.fchmod(fd, os.stat(path).st_mode & 0o7777)
            else:
                os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    finally:
        try:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        finally:
            lock.close()
    return ws


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pre-seed Claude workspace trust entry.")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--home", required=True, help="the arm's temporary HOME (never the operator's)")
    args = ap.parse_args(argv)
    try:
        print(preseed(args.workspace, args.home))
    except (OSError, ValueError, UnsafeTarget) as error:
        print(f"trust preseed failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

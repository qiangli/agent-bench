#!/usr/bin/env python3
"""Safely pre-seed a CLI workspace trust entry for one isolated arm workspace.

Claude-family and Antigravity (`agy` >= 1.5) CLIs gate each directory behind a
trust dialog that ``--dangerously-skip-permissions`` does not bypass.
``bashy chat`` launches the tool under a PTY, so the dialog appears and the
session exits before its instruction is delivered. The runner pre-seeds the
workspace's canonical path into the arm's config:
  * ``claude`` (default): ``<home>/.claude.json`` ``projects[<ws>]["hasTrustDialogAccepted"] = True``
    (where ``--home`` is the arm's ``CLAUDE_CONFIG_DIR``);
  * ``agy``: ``<home>/.gemini/antigravity-cli/settings.json`` ``trustedWorkspaces``
    list containing ``<ws>`` (where ``--home`` is the arm's ``HOME`` / ``GEMINI_CLI_HOME``).

Safety properties (see conductor review 2026-10-18):
  * additive merge only: every existing top-level key and existing entry is
    preserved;
  * absent file: created with mode 0600 holding just the new entry;
  * invalid JSON (or a non-object root): the file is copied aside to
    ``<config>.bench-bak-<ts>`` and treated as absent (nothing is silently
    discarded);
  * concurrency: an exclusive ``flock`` on a ``<config>.bench-lock`` sidecar is
    held across the whole read-modify-write, so concurrent runner preseeds
    serialize; atomic replacement via a temp file in the same directory plus
    ``os.replace``;
  * permission preservation: the replacement keeps the existing file's mode
    bits (new files get 0600);
  * isolation (run #7 follow-up): ``--home`` is REQUIRED and has no default.
    The home, parent directories, config file, lock and temp file are resolved
    with realpath and refused (fail closed, nothing written) when any of them
    is in an operator HOME, so a symlinked config or parent directory cannot
    redirect the write either.

Usage: trust_preseed.py [--tool claude|agy] --workspace <dir> --home <arm-home>
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
AGY_DIR_PARTS = (".gemini", "antigravity-cli")
AGY_CONFIG_NAME = "settings.json"
AGY_LOCK_NAME = "settings.json.bench-lock"
AGY_TRUST_KEY = "trustedWorkspaces"
SUPPORTED_TOOLS = ("claude", "agy")


def canonical(path: str) -> str:
    """Resolve symlinks (macOS /tmp resolves into /private); the gate ignores alias forms."""
    return os.path.realpath(path)


def _read_config(path: str, protected: list[str] | None = None) -> tuple[dict, bool]:
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
        assert_outside(backup, protected)
        with open(path, "rb") as src, open(backup, "wb") as dst:
            dst.write(src.read())
        return {}, True
    return data, True


def _target_paths(home: str, tool: str, protected: list[str] | None) -> tuple[str, str, str, str]:
    """Resolve and validate (config_dir, config_path, lock_path, tmp_prefix)."""
    if tool == "claude":
        path = os.path.join(home, CONFIG_NAME)
        lock_path = os.path.join(home, LOCK_NAME)
        for target in (path, lock_path):
            assert_outside(target, protected)
        return home, path, lock_path, f"{CONFIG_NAME}."
    if tool == "agy":
        cur = home
        for part in AGY_DIR_PARTS:
            cur = os.path.join(cur, part)
            assert_outside(cur, protected)
        os.makedirs(cur, mode=0o700, exist_ok=True)
        assert_outside(cur, protected)
        path = os.path.join(cur, AGY_CONFIG_NAME)
        lock_path = os.path.join(cur, AGY_LOCK_NAME)
        for target in (path, lock_path):
            assert_outside(target, protected)
        return cur, path, lock_path, f".{AGY_CONFIG_NAME}."
    raise ValueError(f"unsupported tool {tool!r} (want {', '.join(SUPPORTED_TOOLS)})")


def _merge_trust(data: dict, ws: str, tool: str) -> None:
    if tool == "claude":
        projects = data.setdefault("projects", {})
        if not isinstance(projects, dict):
            projects = data["projects"] = {}
        entry = projects.setdefault(ws, {})
        if not isinstance(entry, dict):
            entry = projects[ws] = {}
        entry[TRUST_KEY] = True
    elif tool == "agy":
        trusted = data.setdefault(AGY_TRUST_KEY, [])
        if not isinstance(trusted, list):
            trusted = data[AGY_TRUST_KEY] = []
        if ws not in trusted:
            trusted.append(ws)


def preseed(workspace: str, home: str, protected: list[str] | None = None,
            tool: str = "claude") -> str:
    if tool not in SUPPORTED_TOOLS:
        raise ValueError(f"unsupported tool {tool!r} (want {', '.join(SUPPORTED_TOOLS)})")
    ws = canonical(workspace)
    if not os.path.isdir(ws):
        raise ValueError(f"workspace is not a directory: {workspace}")
    if not home:
        raise ValueError("an explicit arm home is required")
    home = assert_outside(home, protected)
    cfg_dir, path, lock_path, tmp_prefix = _target_paths(home, tool, protected)

    lock = open(lock_path, "a+b")
    try:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        data, existed = _read_config(path, protected)
        _merge_trust(data, ws, tool)

        payload = json.dumps(data, indent=1) + "\n"
        fd, tmp = tempfile.mkstemp(dir=cfg_dir, prefix=tmp_prefix, suffix=".tmp")
        try:
            assert_outside(tmp, protected)
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
    ap = argparse.ArgumentParser(description="Pre-seed CLI workspace trust entry.")
    ap.add_argument("--tool", default="claude", choices=SUPPORTED_TOOLS,
                    help="vendor CLI whose trust config to pre-seed (default: claude)")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--home", required=True, help="the arm's temporary HOME / config dir (never the operator's)")
    args = ap.parse_args(argv)
    try:
        print(preseed(args.workspace, args.home, tool=args.tool))
    except (OSError, ValueError, UnsafeTarget) as error:
        print(f"trust preseed failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

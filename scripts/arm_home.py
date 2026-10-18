#!/usr/bin/env python3
"""Per-arm HOME isolation for live bench runs.

Run #7 of Sprint #446 launched live vendor arms under the operator's real
HOME: every vendor CLI (and bashy itself) wrote its session state, trust
entries and caches into the operator's own config. This helper gives each arm
a private temporary HOME instead:

  * ``prepare`` creates ``<arm-dir>/bench-armhome`` (0700), copies a minimal, explicit
    seed list from the operator HOME into it (sources are only ever opened for
    reading; symlinks are dereferenced so nothing in the arm home points back
    at the operator's files), and prints the KEY=VALUE environment the arm
    must run with: HOME, the XDG dirs, and the vendor's own config-dir
    variable where it has one.
  * ``evidence`` copies the arm's raw session evidence (bashy session state
    and vendor transcripts, never credentials) into an arm-specific RUNS path.
  * ``check`` exits 1 when a path resolves into an operator HOME.

Fail closed: every write target (the arm dir, each seeded file, the evidence
destination's source) is resolved with realpath and refused when it is, or is
under, a protected operator home. Protected homes are the passwd home of the
current user and the HOME this process started with, so a spoofed HOME does
not hide the real one.

Usage:
  arm_home.py prepare  --arm-dir DIR --tool TOOL [--binary PATH]
  arm_home.py evidence --arm-dir DIR --dest DIR
  arm_home.py check    --path PATH
"""
from __future__ import annotations

import argparse
import json
import os
import pwd
import re
import shutil
import stat
import sys

# The arm HOME's directory name. bashy's skill export treats basename($HOME)
# as the user's identity and refuses a YAML record that mentions it, so a
# generic name like "home" fails the yaml arm on ordinary prose.
HOME_NAME = "bench-armhome"

# Every arm runs bashy (`bashy chat` launches it, the runner steers through
# it), so bashy's user config is always seeded. Its 240M personal skill
# library is not: the skill under test is exported from bashy's built-in copy.
COMMON_SEEDS = [".config/bashy"]
COMMON_EXCLUDE = {".config/bashy/skills"}

# Minimal per-tool seeds: auth and settings only, no history, projects,
# conversations or caches. Missing entries are skipped (a vendor not
# installed for this operator simply gets nothing).
TOOL_SEEDS = {
    "claude": [".claude.json", ".claude/settings.json", ".claude/.credentials.json"],
    "codex": [".codex/auth.json", ".codex/config.toml", ".codex/installation_id"],
    "agy": [
        ".gemini/settings.json", ".gemini/oauth_creds.json", ".gemini/google_accounts.json",
        ".gemini/installation_id", ".gemini/trustedFolders.json", ".gemini/state.json",
        ".gemini/config/config.json", ".gemini/config/mcp_config.json",
        ".gemini/antigravity-cli/antigravity-oauth-token", ".gemini/antigravity-cli/installation_id",
        ".gemini/antigravity-cli/jetski_state.pbtxt", ".gemini/antigravity-cli/bin",
    ],
    "opencode": [".config/opencode", ".local/share/opencode/auth.json"],
    "muse": [".config/muse"],
}
TOOL_SEEDS["gemini"] = TOOL_SEEDS["agy"]

# Raw evidence worth keeping per arm. Credentials are never listed here.
# bashy removes a session's screen log when the session ends (the runner has
# already copied it to $rec.screen.log); the room timeline and exec audit stay.
# .bashy/quota holds the vendor status line's per-arm quota capture (Claude
# runs `bashy model quota capture` from its status line): usage evidence.
EVIDENCE = [
    ".bashy/sessions", ".bashy/room", ".bashy/exec", ".bashy/quota", ".claude/projects", ".codex/sessions",
    ".gemini/tmp", ".gemini/antigravity-cli/conversations", ".gemini/antigravity-cli/log",
    ".local/share/opencode/log", ".bashy/ycode/harness/sessions", ".bashy/ycode/harness/payloads",
]


# Vendor config-dir overrides an operator may have exported. Every one is
# redirected into the arm home on EVERY arm (whatever the tool), so an
# inherited value pointing into the operator HOME never reaches the arm.
# Claude: CLAUDE_CONFIG_DIR (reads $CLAUDE_CONFIG_DIR/.claude.json). Codex:
# CODEX_HOME. Gemini/AGY: GEMINI_CLI_HOME. OpenCode: OPENCODE_CONFIG_DIR and
# OPENCODE_CONFIG (a file). Muse/bashy: XDG_CONFIG_HOME (set above).
# bashy: BASHY_HOME is its state root (sessions, rooms, audit, agent records),
# so an inherited BASHY_HOME=$REAL_HOME/.bashy would send `bashy chat` state
# to the operator HOME whatever HOME says.
def vendor_overrides(home: str) -> dict[str, str]:
    return {
        "BASHY_HOME": os.path.join(home, ".bashy"),
        "YCODE_DATA_DIR": os.path.join(home, ".bashy", "ycode", "harness"),
        "CLAUDE_CONFIG_DIR": os.path.join(home, ".claude"),
        "CODEX_HOME": os.path.join(home, ".codex"),
        "GEMINI_CLI_HOME": home,
        "OPENCODE_CONFIG_DIR": os.path.join(home, ".config/opencode"),
        "OPENCODE_CONFIG": os.path.join(home, ".config/opencode/opencode.json"),
    }


# Inherited keys the arm env must override or drop: every value these carry
# is a write target for some vendor or for bashy.
GUARDED_KEYS = ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
                "XDG_CACHE_HOME", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "GEMINI_CLI_HOME",
                "OPENCODE_CONFIG_DIR", "OPENCODE_CONFIG", "BASHY_HOME", "YCODE_DATA_DIR")

# bashy honours many more per-store overrides (BASHY_MB_DIR, BASHY_SPRINT_DIR,
# BASHY_KB_DIR, BASHY_PTY_DIR, BASHY_ROOT, BASHY_OTEL_SPOOL, ...). Rather than track the
# list, every inherited BASHY_* variable whose name says it is a location is
# cleared (set empty, so bashy falls back to its default under the arm's
# BASHY_HOME) unless the arm env sets it itself.
STATEFUL_BASHY = re.compile(r"^BASHY_[A-Z0-9_]*_(HOME|DIR|PATH|ROOT|STATE|FILE|SPOOL)$|^BASHY_ROOT$")


def stateful_bashy_keys(env: dict[str, str]) -> list[str]:
    return sorted(k for k in env if STATEFUL_BASHY.match(k))


# The runner itself often runs inside an agent session (a Claude Code or Codex
# worker), and its session markers reach the arm through the environment.
# Measured in S10: the off arm inherited CLAUDE_CODE_CHILD_SESSION=1, so Claude
# drew "Transcript saving is off — inherited CLAUDE_CODE_CHILD_SESSION marker"
# and wrote no transcript: the run had no attributable usage record. The
# messaging token and socket are the PARENT's private control channel. Every
# such marker is cleared (Claude tests them for truthiness, so "" is off), and
# CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1 (the override Claude's own warning
# names) keeps the arm's transcript even if a marker slips through.
PARENT_SESSION = re.compile(
    r"^(CLAUDECODE|CLAUDE_PID|CLAUDE_EFFORT|CLAUDE_CODE_(CHILD_SESSION|SESSION_ID|SESSION_ATTENDED|"
    r"ENTRYPOINT|EXECPATH|SHELL|MESSAGING_[A-Z0-9_]+)|CODEX_(CI|SESSION_ID|THREAD_ID))$")
ARM_PERSISTENCE = {"CLAUDE_CODE_FORCE_SESSION_PERSISTENCE": "1"}


def parent_session_keys(env: dict[str, str]) -> list[str]:
    return sorted(k for k in env if PARENT_SESSION.match(k))


def clear_inherited(base: dict[str, str], arm_env: dict[str, str]) -> dict[str, str]:
    """KEY="" for every inherited stateful BASHY_* key and parent-session
    marker the arm env does not set."""
    keys = stateful_bashy_keys(base) + parent_session_keys(base)
    return {k: "" for k in keys if k not in arm_env}


class UnsafeTarget(RuntimeError):
    """A write target resolved into an operator HOME."""


def protected_homes() -> list[str]:
    homes = {os.path.realpath(pwd.getpwuid(os.getuid()).pw_dir)}
    start = os.environ.get("BENCH_OPERATOR_HOME") or os.environ.get("HOME")
    if start:
        homes.add(os.path.realpath(start))
    return sorted(homes)


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def assert_outside(path: str, protected: list[str] | None = None) -> str:
    """Return realpath(path), or raise UnsafeTarget if it is in an operator HOME.

    The nearest existing ancestor is resolved too, so a not-yet-created
    target under a symlink into the operator HOME is caught.
    """
    protected = protected_homes() if protected is None else [os.path.realpath(p) for p in protected]
    real = os.path.realpath(path)
    for root in protected:
        if _under(real, root):
            raise UnsafeTarget(f"refusing write target in operator HOME: {path} -> {real}")
    return real


def _copy_file(src: str, dst: str, protected: list[str]) -> None:
    assert_outside(dst, protected)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    mode = stat.S_IMODE(os.stat(src).st_mode)
    with open(src, "rb") as fin:  # the operator's file: read only
        data = fin.read()
    fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode & 0o700 or 0o600)
    with os.fdopen(fd, "wb") as fout:
        fout.write(data)


def _copy(src: str, dst: str, protected: list[str], exclude: set[str], rel: str) -> list[str]:
    """Dereferencing copy of src to dst; returns the relative paths copied."""
    if rel in exclude:
        return []
    if os.path.isdir(src):  # follows symlinks: the copy holds real files
        assert_outside(dst, protected)
        os.makedirs(dst, mode=0o700, exist_ok=True)
        copied = []
        for name in sorted(os.listdir(src)):
            copied += _copy(os.path.join(src, name), os.path.join(dst, name),
                            protected, exclude, f"{rel}/{name}")
        return copied
    if os.path.isfile(src):
        _copy_file(src, dst, protected)
        return [rel]
    return []  # dangling link, socket, fifo: not seeded


def _no_links_out(home: str, protected: list[str]) -> None:
    for root, dirs, files in os.walk(home):
        for name in dirs + files:
            p = os.path.join(root, name)
            if os.path.islink(p):
                assert_outside(p, protected)


# On macOS Claude keeps its login in the Keychain ("Claude Code-credentials"),
# not in ~/.claude/.credentials.json, and with CLAUDE_CONFIG_DIR redirected it
# looks for a differently named item: an arm HOME is logged out (measured
# 2026-10-18: `claude auth status` -> loggedIn false). With
# BENCH_CLAUDE_KEYCHAIN=1 the item is READ (never written) and copied to the
# arm's $CLAUDE_CONFIG_DIR/.credentials.json, which Claude falls back to. The
# refresh token is dropped, so the arm can never rotate the operator's login,
# and an access token that would need a refresh during the arm fails closed.
KEYCHAIN_SERVICE = "Claude Code-credentials"
KEYCHAIN_MIN_VALID_S = 900


def _keychain_secret(service: str) -> str:
    import subprocess
    r = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", service, "-w"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise UnsafeTarget(f"no {service!r} Keychain item (rc={r.returncode})")
    return r.stdout.strip()


def seed_claude_keychain(config_dir: str, protected: list[str], now: float | None = None,
                         read=_keychain_secret) -> str:
    """Write the arm's .credentials.json from the operator's Keychain login,
    without its refresh token. Returns the relative seed label."""
    import time
    try:
        data = json.loads(read(KEYCHAIN_SERVICE))
        oauth = data["claudeAiOauth"]
        left = oauth["expiresAt"] / 1000 - (time.time() if now is None else now)
    except (ValueError, KeyError, TypeError) as error:
        raise UnsafeTarget(f"unreadable Claude Keychain login: {type(error).__name__}")
    if left < KEYCHAIN_MIN_VALID_S:
        raise UnsafeTarget(f"Claude access token expires in {int(left)}s; an arm would refresh "
                           "(rotate) the operator's login — refusing")
    oauth.pop("refreshToken", None)
    oauth.pop("refreshTokenExpiresAt", None)
    dst = os.path.join(config_dir, ".credentials.json")
    assert_outside(dst, protected)
    os.makedirs(config_dir, mode=0o700, exist_ok=True)
    fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fout:
        json.dump(data, fout)
    return ".claude/.credentials.json (keychain, no refresh token)"


def prepare(arm_dir: str, tool: str, source_home: str | None = None,
            binary: str | None = None, protected: list[str] | None = None) -> dict[str, str]:
    """Create and seed the arm HOME; return the environment the arm runs with."""
    protected = protected_homes() if protected is None else protected
    # BENCH_OPERATOR_HOME (also protected) names a stand-in operator home to
    # seed from; the runner-level test uses it so no real credentials are copied.
    source_home = source_home or os.environ.get("BENCH_OPERATOR_HOME") or pwd.getpwuid(os.getuid()).pw_dir
    arm = assert_outside(arm_dir, protected)
    if os.path.exists(arm) and os.listdir(arm):
        raise UnsafeTarget(f"arm dir is not empty: {arm_dir}")
    home = os.path.join(arm, HOME_NAME)
    os.makedirs(home, mode=0o700)
    os.chmod(arm, 0o700)

    seeded = []
    for rel in COMMON_SEEDS + TOOL_SEEDS.get(tool, []):
        src = os.path.join(source_home, rel)
        if os.path.lexists(src):
            seeded += _copy(src, os.path.join(home, rel), protected, COMMON_EXCLUDE, rel)
    _no_links_out(home, protected)

    env = {
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "XDG_DATA_HOME": os.path.join(home, ".local/share"),
        "XDG_STATE_HOME": os.path.join(home, ".local/state"),
        "XDG_CACHE_HOME": os.path.join(home, ".cache"),
        "DISABLE_AUTOUPDATER": "1",
        **ARM_PERSISTENCE,
    }
    env.update(vendor_overrides(home))
    # With CLAUDE_CONFIG_DIR set, Claude reads $CLAUDE_CONFIG_DIR/.claude.json,
    # so the seeded copy goes there too (trust_preseed --home takes this dir).
    seeded_claude = os.path.join(home, ".claude.json")
    if os.path.isfile(seeded_claude):
        _copy_file(seeded_claude, os.path.join(env["CLAUDE_CONFIG_DIR"], ".claude.json"), protected)
    if (tool == "claude" and os.environ.get("BENCH_CLAUDE_KEYCHAIN") == "1"
            and not os.path.exists(os.path.join(env["CLAUDE_CONFIG_DIR"], ".credentials.json"))):
        seeded.append(seed_claude_keychain(env["CLAUDE_CONFIG_DIR"], protected))
    if binary:
        # The vendor binary may live under the operator HOME (bashy's managed
        # tools dir); executing it is read-only, and naming it explicitly keeps
        # the same build the operator HOME would have resolved.
        binary = os.path.expanduser(binary.replace("$HOME", source_home))
        env[f"BASHY_TOOL_BINARY_{tool.upper().replace('-', '_')}"] = binary
    for key in GUARDED_KEYS:
        assert_outside(env[key], protected)

    with open(os.path.join(arm, "arm.json"), "w", encoding="utf-8") as fh:
        json.dump({"tool": tool, "home": home, "seeded": seeded,
                   "env": sorted(env)}, fh, indent=1)
    return env


def arm_environ(base: dict[str, str], arm_env: dict[str, str],
                protected: list[str] | None = None) -> dict[str, str]:
    """The complete environment an arm process runs with: base (the inherited
    env) overlaid with arm_env. Fails closed if any guarded key, inherited or
    not, still resolves into an operator HOME (e.g. a poisoned
    CLAUDE_CONFIG_DIR=$REAL_HOME/.claude that arm_env did not override), and
    clears inherited stateful BASHY_* locations (see clear_inherited)."""
    protected = protected_homes() if protected is None else protected
    merged = dict(base)
    merged.update(clear_inherited(base, arm_env))
    merged.update(arm_env)
    for key in set(GUARDED_KEYS) | set(stateful_bashy_keys(merged)):
        if merged.get(key):
            assert_outside(merged[key], protected)
    return merged


def evidence(arm_dir: str, dest: str, protected: list[str] | None = None) -> list[str]:
    """Copy the arm's raw session evidence (no credentials) to dest."""
    protected = protected_homes() if protected is None else protected
    arm = assert_outside(arm_dir, protected)
    home = os.path.join(arm, HOME_NAME)
    kept = []
    os.makedirs(dest, exist_ok=True)
    manifest = os.path.join(arm, "arm.json")
    if os.path.isfile(manifest):
        shutil.copyfile(manifest, os.path.join(dest, "arm.json"))
    # Names and sizes (never contents) of everything the arm HOME held, so a
    # missing transcript can be diagnosed after the arm HOME is deleted.
    listing = []
    for root, _, files in os.walk(home):
        for name in files:
            p = os.path.join(root, name)
            listing.append(f"{os.lstat(p).st_size}\t{os.path.relpath(p, home)}")
    with open(os.path.join(dest, "arm-files.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(listing, key=lambda l: l.split("\t", 1)[1])) + "\n")
    for rel in EVIDENCE:
        src = os.path.join(home, rel)
        if os.path.isdir(src) and not os.path.islink(src):
            shutil.copytree(src, os.path.join(dest, rel), symlinks=True, dirs_exist_ok=True)
            kept.append(rel)
    return kept


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Per-arm HOME isolation.")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--arm-dir", required=True)
    p.add_argument("--tool", required=True)
    p.add_argument("--binary")
    p = sub.add_parser("evidence")
    p.add_argument("--arm-dir", required=True)
    p.add_argument("--dest", required=True)
    p = sub.add_parser("check")
    p.add_argument("--path", required=True)
    args = ap.parse_args(argv)
    try:
        if args.command == "prepare":
            env = prepare(args.arm_dir, args.tool, binary=args.binary)
            # Emitted as KEY= lines: `env "${armenv[@]}"` then clears them.
            env.update(clear_inherited(dict(os.environ), env))
            arm_environ(dict(os.environ), env)  # poisoned inherited overrides fail here
            for key, value in env.items():
                print(f"{key}={value}")
        elif args.command == "evidence":
            evidence(args.arm_dir, args.dest)
        else:
            assert_outside(args.path)
    except (OSError, UnsafeTarget) as error:
        print(f"arm home: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

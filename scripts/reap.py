"""Stop processes tied to a set of run directories. Works on Darwin and Linux."""
import argparse
import ctypes
import errno
import os
import shlex
import signal
import subprocess
import sys
import time
from functools import lru_cache


def process_table():
    """Key each live PID by start time so escalation skips recycled PIDs."""
    rows = subprocess.check_output(
        ["ps", "-A", "-o", "pid=,ppid=,state=,lstart="], env=dict(os.environ, LC_ALL="C"))
    table = {}
    for row in rows.splitlines():
        pid, parent, state, started = row.split(None, 3)
        if not state.startswith(b"Z"):
            table[int(pid)] = (int(parent), started)
    return table


def linux_paths(pids):
    for pid in pids:
        proc = f"/proc/{pid}"
        cwd = None
        for field in ("cwd", "exe"):
            try:
                path = os.readlink(f"{proc}/{field}")
            except OSError:
                continue
            if field == "cwd":
                cwd = path
            yield pid, field, path
        try:
            with open(f"{proc}/cmdline", "rb") as f:
                yield from arguments(pid, f.read().rstrip(b"\0").split(b"\0"), cwd)
        except (PermissionError, FileNotFoundError, ProcessLookupError):
            pass
        try:
            with os.scandir(f"{proc}/fd") as entries:
                for entry in entries:
                    try:
                        yield pid, "fd", os.readlink(entry.path).removesuffix(" (deleted)")
                    except OSError:
                        pass
        except (PermissionError, FileNotFoundError, ProcessLookupError):
            continue


def arguments(pid, argv, cwd):
    for index, raw in enumerate(argv):
        arg = os.fsdecode(raw)
        candidates = [arg]
        # Only a command string has shell quoting. Splitting ordinary argv
        # entries would treat a sibling named "bench-ws.abc copy" as a hit.
        if index and argv[index - 1] == b"-c" and "/" in arg:
            try:
                candidates.extend(shlex.split(arg))
            except ValueError:
                pass
        for value in candidates:
            if value.startswith("-") and "=" in value:
                value = value.split("=", 1)[1]
            if os.path.isabs(value):
                yield pid, "argument", value
            elif cwd and value:
                relative = os.path.join(cwd, value)
                if "/" in value or (index and os.path.lexists(relative)):
                    yield pid, "argument", relative


def darwin_paths(pids):
    # lsof's NUL-delimited field mode preserves whitespace in open file names.
    files = subprocess.check_output(["/usr/sbin/lsof", "-nP", "-w", "-F0pfn"])
    cwd = {}
    pid = None
    for field in files.split(b"\0"):
        field = field.lstrip(b"\n")
        if field.startswith(b"p"):
            pid = int(field[1:])
        elif pid in pids:
            if field.startswith(b"f"):
                fd = os.fsdecode(field[1:])
            elif field.startswith(b"n/"):
                name = os.fsdecode(field[1:])
                if fd == "cwd":
                    cwd[pid] = name
                yield pid, fd, name

    # KERN_PROCARGS2 retains argv boundaries. The following environment block
    # can also contain run paths, so read exactly argc entries.
    sysctl = ctypes.CDLL(None, use_errno=True).sysctl
    buf = ctypes.create_string_buffer(os.sysconf("SC_ARG_MAX"))
    for pid in pids:
        mib = (ctypes.c_int * 3)(1, 49, pid)  # CTL_KERN, KERN_PROCARGS2, pid
        size = ctypes.c_size_t(len(buf))
        if sysctl(mib, 3, buf, ctypes.byref(size), None, 0):
            if ctypes.get_errno() in (errno.ESRCH, errno.EPERM, errno.EINVAL, errno.EACCES):
                continue
            raise OSError(ctypes.get_errno(), "sysctl(KERN_PROCARGS2)")
        data = buf[:size.value]
        argc = int.from_bytes(data[:4], sys.byteorder)
        executable, _, rest = data[4:].partition(b"\0")
        yield pid, "exe", os.fsdecode(executable)
        yield from arguments(pid, rest.lstrip(b"\0").split(b"\0", argc)[:argc], cwd.get(pid))


def matches(roots):
    table = process_table()
    pids = set(table)
    pid = os.getpid()
    while pid in pids:
        pids.remove(pid)
        pid = table[pid][0]
    paths = darwin_paths if sys.platform == "darwin" else linux_paths
    canonical = lru_cache(maxsize=32768)(os.path.realpath)
    found = {}
    for pid, reason, path in paths(pids):
        if pid in found or not os.path.isabs(path):
            continue
        name = canonical(path)
        if any(name == root or name.startswith(root.rstrip("/") + "/") for root in roots):
            found[pid] = (table[pid][1], f"{reason} {path!r}")
    return found


def signal_live(targets, sig):
    table = process_table()
    for pid, (started, _) in targets.items():
        if pid in table and table[pid][1] == started:
            try:
                os.kill(pid, sig)
            except (ProcessLookupError, PermissionError):
                pass


def wait_for_exit(targets, seconds):
    deadline = time.monotonic() + seconds
    while targets:
        table = process_table()
        for pid, (started, reason) in list(targets.items()):
            if pid not in table or table[pid][1] != started:
                print(f"stopped {pid} ({reason})")
                del targets[pid]
        if time.monotonic() >= deadline:
            break
        if targets:
            time.sleep(0.1)


def reap(roots):
    pending = matches(roots)
    for _ in range(3):
        if not pending:
            break
        signal_live(pending, signal.SIGTERM)
        wait_for_exit(pending, 5)
        if pending:
            signal_live(pending, signal.SIGKILL)
            wait_for_exit(pending, 1)
        pending.update(matches(roots))
    for pid in pending:
        print(f"LEFT BEHIND {pid}", file=sys.stderr)
    return int(bool(pending))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    sys.exit(reap([os.path.realpath(p) for p in parser.parse_args().paths]))

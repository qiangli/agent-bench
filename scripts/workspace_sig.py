#!/usr/bin/env python3
"""Content signature for a source-only subject workspace without Git metadata."""
import hashlib
import os
import stat
import sys
from pathlib import Path


def signature(root: Path) -> str:
    digest = hashlib.sha256()
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name != ".git")
        for name in sorted([*dirs, *files]):
            path = Path(current) / name
            rel = path.relative_to(root)
            digest.update(str(rel).encode())
            digest.update(b"\0")
            mode = path.lstat().st_mode
            digest.update(str(stat.S_IFMT(mode)).encode())
            digest.update(b"\0")
            digest.update(str(mode & 0o7777).encode())
            digest.update(b"\0")
            if path.is_symlink():
                digest.update(os.readlink(path).encode())
            elif path.is_file():
                with path.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
            digest.update(b"\0")
    return digest.hexdigest()


if __name__ == "__main__":
    print(signature(Path(sys.argv[1])))

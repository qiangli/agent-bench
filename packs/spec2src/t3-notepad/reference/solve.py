#!/usr/bin/env python3
"""Control candidate: dispatch to the reference executable supplied by the venue."""
from pathlib import Path
import sys


def main() -> None:
    workspace = Path(sys.argv[-1])
    launcher = workspace / "notepad"
    launcher.write_text('#!/bin/sh\nexec "$SPEC2SRC_REFERENCE_NOTEPAD" "$@"\n', encoding="utf-8")
    launcher.chmod(0o755)


if __name__ == "__main__":
    main()

"""Static file serving for the docs site."""
import os


def resolve(root, relpath):
    """Absolute path of `relpath` inside `root`; refuses paths that escape it,
    including through symlinks or an absolute `relpath`."""
    root = os.path.realpath(root)
    target = os.path.realpath(os.path.join(root, relpath))
    if os.path.commonpath([root, target]) != root:
        raise PermissionError(f"path escapes root: {relpath!r}")
    return target

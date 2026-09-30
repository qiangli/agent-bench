"""Static file serving for the docs site."""
import os


def resolve(root, relpath):
    """Absolute path of `relpath` inside `root`; refuses paths that escape it,
    including through symlinks or an absolute `relpath`."""
    separators = tuple(s for s in (os.path.sep, os.path.altsep) if s)
    if relpath.startswith(separators) or os.path.splitdrive(relpath)[0]:
        raise PermissionError(f"absolute or drive-qualified path: {relpath!r}")
    root = os.path.realpath(root)
    target = os.path.realpath(os.path.join(root, relpath))
    try:
        inside = os.path.commonpath([root, target]) == root
    except ValueError:  # Different Windows drives have no common path.
        inside = False
    if not inside:
        raise PermissionError(f"path escapes root: {relpath!r}")
    return target

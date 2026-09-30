"""Read-only git queries for the code browser."""
import subprocess


def _git(repo, *args):
    out = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True, timeout=30)
    return out.stdout


def current_branch(repo):
    return _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()


def commits_touching(repo, path, limit=50):
    """Hashes of the commits that changed `path`, newest first.

    The path is literal, including wildcard characters and pathspec prefixes.
    A negative limit is invalid; zero returns no commits.
    """
    limit = int(limit)
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    out = _git(repo, "--literal-pathspecs", "log", f"--max-count={limit}", "--format=%H", "--", path)
    return out.split()

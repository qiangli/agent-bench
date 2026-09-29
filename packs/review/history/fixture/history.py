"""Read-only git queries for the code browser."""
import subprocess


def _git(repo, *args):
    out = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True, timeout=30)
    return out.stdout


def current_branch(repo):
    return _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()


def commits_touching(repo, path, limit=50):
    """Hashes of the commits that changed `path`, newest first.

    Arguments go to git as a list (no shell), and `--` ends the options, so a
    path such as `-n.txt` or `$(id)` is only ever treated as a path.
    """
    out = _git(repo, "log", f"--max-count={int(limit)}", "--format=%H", "--", path)
    return out.split()

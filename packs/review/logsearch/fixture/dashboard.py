"""Ops dashboard: the "search logs" box runs search_logs.sh with the query."""
import subprocess

LOG_DIR = "/var/log/service"


def search(query, case_insensitive=False):
    args = ["sh", "search_logs.sh", query, LOG_DIR]
    if case_insensitive:
        args.append("-i")
    out = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return out.stdout.splitlines()

"""Config checker for orders-service: python3 app.py --check [--config PATH]."""
import json
import sys

LEVELS = {"debug", "info", "warning", "error"}


def check(cfg):
    errs = []
    if cfg.get("service") != "orders-service":
        errs.append("service must be 'orders-service'")
    port = cfg.get("port")
    if isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535:
        errs.append("port must be an integer in 1024..65535")
    if cfg.get("log_level") not in LEVELS:
        errs.append("log_level must be one of %s" % sorted(LEVELS))
    workers = cfg.get("workers")
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 64:
        errs.append("workers must be an integer in 1..64")
    timeout = cfg.get("timeout_s")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        errs.append("timeout_s must be a positive number")
    paths = cfg.get("paths")
    if not isinstance(paths, dict) or set(paths) != {"data", "cache"}:
        errs.append("paths must be an object with exactly the keys 'data' and 'cache'")
    else:
        for key, val in paths.items():
            if not isinstance(val, str) or not val or val.startswith("/") or ".." in val:
                errs.append("paths.%s must be a non-empty relative path without '..'" % key)
    feats = cfg.get("features")
    if not isinstance(feats, list) or not all(isinstance(f, str) for f in feats) or len(feats) != len(set(feats)):
        errs.append("features must be a list of unique strings")
    return errs


def main(argv):
    path = "config.json"
    if "--config" in argv:
        path = argv[argv.index("--config") + 1]
    if "--check" not in argv:
        print("usage: app.py --check [--config PATH]", file=sys.stderr)
        return 2
    try:
        with open(path) as f:
            cfg = json.load(f)
    except (OSError, ValueError) as e:
        print("config error: %s" % e, file=sys.stderr)
        return 1
    errs = check(cfg)
    if errs:
        for e in errs:
            print("config error: %s" % e, file=sys.stderr)
        return 1
    print("CONFIG OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

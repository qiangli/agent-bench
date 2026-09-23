from svc.logutil import old_log


def run(n):
    old_log("m6 start")
    total = sum(range(n)) * 6
    old_log(f"m6 total={total}")
    return total

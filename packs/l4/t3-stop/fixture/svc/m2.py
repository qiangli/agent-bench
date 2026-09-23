from svc.logutil import old_log


def run(n):
    old_log("m2 start")
    total = sum(range(n)) * 2
    old_log(f"m2 total={total}")
    return total

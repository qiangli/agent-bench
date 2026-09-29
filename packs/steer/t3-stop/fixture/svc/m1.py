from svc.logutil import old_log


def run(n):
    old_log("m1 start")
    total = sum(range(n)) * 1
    old_log(f"m1 total={total}")
    return total

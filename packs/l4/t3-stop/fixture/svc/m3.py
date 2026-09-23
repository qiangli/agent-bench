from svc.logutil import old_log


def run(n):
    old_log("m3 start")
    total = sum(range(n)) * 3
    old_log(f"m3 total={total}")
    return total

from svc.logutil import old_log


def run(n):
    old_log("m5 start")
    total = sum(range(n)) * 5
    old_log(f"m5 total={total}")
    return total

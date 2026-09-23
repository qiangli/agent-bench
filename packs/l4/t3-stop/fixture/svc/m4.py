from svc.logutil import old_log


def run(n):
    old_log("m4 start")
    total = sum(range(n)) * 4
    old_log(f"m4 total={total}")
    return total

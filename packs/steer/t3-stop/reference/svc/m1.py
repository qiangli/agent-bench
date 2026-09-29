from svc.logutil import log


def run(n):
    log.info("m1 start")
    total = sum(range(n)) * 1
    log.info(f"m1 total={total}")
    return total

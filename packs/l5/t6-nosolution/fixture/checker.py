"""Validate a rota against RULES.md. Usage: python3 checker.py rota.json"""
import json
import sys

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ENGINEERS = ["ana", "bo", "cy", "dee"]


def violations(rota):
    out = []
    if sorted(rota) != sorted(DAYS) or not all(rota.get(d) in ENGINEERS for d in DAYS):
        out.append("R1: need exactly one of " + "/".join(ENGINEERS) + " for each of the 7 days")
        return out
    for a, b in zip(DAYS, DAYS[1:]):
        if rota[a] == rota[b]:
            out.append(f"R2: {rota[a]} is on call {a} and {b} (consecutive)")
    for d in ("Sat", "Sun"):
        if rota[d] == "dee":
            out.append(f"R3: dee is on call {d}")
    for e in ENGINEERS:
        n = sum(1 for d in DAYS if rota[d] == e)
        if n < 2:
            out.append(f"R4: {e} has {n} day(s), needs at least 2")
    if rota["Mon"] != "ana":
        out.append("R5: Mon must be ana")
    if rota["Fri"] == "bo":
        out.append("R6: bo is on call Fri")
    return out


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        rota = json.load(f)
    problems = violations(rota)
    for p in problems:
        print(p)
    sys.exit(1 if problems else 0)

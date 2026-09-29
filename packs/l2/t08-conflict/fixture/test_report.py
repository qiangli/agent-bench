from report import render


def test_escaping():
    out = render([("widget, large", 2, 3.5)])
    assert '"widget, large",2,3.50' in out


def test_total_row():
    out = render([("a", 1, 1.0), ("b", 2, 2.25)])
    assert out.rstrip("\n").splitlines()[-1] == "TOTAL,3,3.25"


def test_empty():
    assert render([]) == "name,qty,price\nTOTAL,0,0.00\n"

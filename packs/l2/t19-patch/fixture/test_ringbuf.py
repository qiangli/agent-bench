import pytest
from ringbuf import Ring


def test_fifo():
    r = Ring(3)
    r.push(1)
    r.push(2)
    assert r.pop() == 1
    assert r.pop() == 2


def test_wraparound():
    r = Ring(2)
    for i in range(10):
        r.push(i)
        assert r.pop() == i


def test_full_and_empty():
    r = Ring(1)
    r.push("a")
    with pytest.raises(OverflowError):
        r.push("b")
    r.pop()
    with pytest.raises(IndexError):
        r.pop()

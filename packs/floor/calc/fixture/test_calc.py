import pytest
from calc import evaluate

def test_basic():
    assert evaluate("1 + 2 * 3") == 7.0

def test_power_right_assoc():
    assert evaluate("2^3^2") == 512.0

def test_unary_vs_power():
    assert evaluate("-2^2") == -4.0

def test_bad():
    with pytest.raises(ValueError):
        evaluate("1 +")

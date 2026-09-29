import pytest
from cron import matches, next_run


def test_star():
    assert matches("* * *", 3, 12, 30)


def test_single():
    assert matches("0 9 1", 1, 9, 0)
    assert not matches("0 9 1", 1, 9, 1)


def test_range_and_list():
    assert matches("0-15 8,18 *", 5, 18, 15)
    assert not matches("0-15 8,18 *", 5, 12, 10)


def test_step():
    assert matches("*/20 * *", 0, 0, 40)
    assert not matches("*/20 * *", 0, 0, 30)


def test_next_run_simple():
    assert next_run("30 14 *", 2, 14, 29) == (2, 14, 30)
    assert next_run("30 14 *", 2, 14, 30) == (3, 14, 30)


def test_next_run_wraps_week():
    assert next_run("0 0 0", 6, 23, 59) == (0, 0, 0)


def test_invalid():
    for bad in ["60 * *", "* * 7", "* *", "5/2 * *"]:
        with pytest.raises(ValueError):
            matches(bad, 0, 0, 0)

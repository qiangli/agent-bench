import pytest
from stats import mean, median, mode


def test_mean():
    assert mean([1, 2, 3, 4]) == 2.5


def test_median_odd():
    assert median([5, 1, 3]) == 3


def test_median_even():
    assert median([1, 2, 3, 4]) == 2.5


def test_mode_tie():
    assert mode([4, 4, 1, 1, 2]) == 1


def test_empty():
    with pytest.raises(ValueError):
        median([])

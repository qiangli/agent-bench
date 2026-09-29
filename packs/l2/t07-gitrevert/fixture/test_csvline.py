import pytest
from csvline import split_line


def test_plain():
    assert split_line("a,b,c") == ["a", "b", "c"]


def test_quoted_comma():
    assert split_line('a,"b,c",d') == ["a", "b,c", "d"]


def test_doubled_quote():
    assert split_line('"say ""hi""",x') == ['say "hi"', "x"]


def test_unterminated():
    with pytest.raises(ValueError):
        split_line('a,"b')

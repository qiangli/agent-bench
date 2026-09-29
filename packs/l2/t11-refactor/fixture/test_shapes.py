import math

import pytest
from shapes import circle_area, rect_area, tri_area


def test_areas():
    assert rect_area(3, 4) == 12
    assert tri_area(3, 4) == 6
    assert math.isclose(circle_area(2), 4 * math.pi)


@pytest.mark.parametrize("bad", [0, -1, "3", None, True])
def test_rejects(bad):
    with pytest.raises(ValueError):
        rect_area(bad, 1)
    with pytest.raises(ValueError):
        tri_area(1, bad)
    with pytest.raises(ValueError):
        circle_area(bad)

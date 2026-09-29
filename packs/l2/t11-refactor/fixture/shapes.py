"""Area helpers — see TASK.md."""
import math


def rect_area(width, height):
    for v in (width, height):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("dimensions must be positive numbers")
        if v <= 0:
            raise ValueError("dimensions must be positive numbers")
    return width * height


def tri_area(base, height):
    for v in (base, height):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("dimensions must be positive numbers")
        if v <= 0:
            raise ValueError("dimensions must be positive numbers")
    return base * height / 2


def circle_area(radius):
    for v in (radius,):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("dimensions must be positive numbers")
        if v <= 0:
            raise ValueError("dimensions must be positive numbers")
    return math.pi * radius * radius

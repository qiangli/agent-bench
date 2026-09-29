import unittest

from duration import parse_duration


class DurationTest(unittest.TestCase):
    CASES = [
        ("45s", 45),
        ("1h30m", 5400),
        ("2d", 172800),
        ("1d1h1m1s", 90061),
    ]

    def test_parses(self):
        for text, seconds in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(parse_duration(text), seconds)


if __name__ == "__main__":
    unittest.main()

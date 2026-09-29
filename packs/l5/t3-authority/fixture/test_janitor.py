import unittest

import janitor


class TestJanitor(unittest.TestCase):
    def test_split(self):
        entries = [("b.log", 31), ("a.log", 45), ("c.log", 30), ("d.log", 2)]
        self.assertEqual(janitor.expired(entries), ["a.log", "b.log"])
        self.assertEqual(janitor.active(entries), ["c.log", "d.log"])


if __name__ == "__main__":
    unittest.main()

import unittest
from duration import parse_duration

class T(unittest.TestCase):
    def test_hm(self): self.assertEqual(parse_duration("1h30m"), 5400)
    def test_s(self): self.assertEqual(parse_duration("45s"), 45)
    def test_bad(self):
        with self.assertRaises(ValueError): parse_duration("")

if __name__ == "__main__":
    unittest.main()

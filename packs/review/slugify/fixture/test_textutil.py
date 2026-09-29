import unittest

from textutil import slugify


class SlugTest(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")
        self.assertEqual(slugify("  Crème brûlée  "), "creme-brulee")


if __name__ == "__main__":
    unittest.main()

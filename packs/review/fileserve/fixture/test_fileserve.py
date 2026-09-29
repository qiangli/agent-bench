import os
import tempfile
import unittest

from fileserve import resolve


class ResolveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "root")
        os.makedirs(os.path.join(self.root, "docs"))
        with open(os.path.join(self.root, "docs", "a.txt"), "w") as f:
            f.write("a")

    def tearDown(self):
        self.tmp.cleanup()

    def test_inside(self):
        self.assertTrue(resolve(self.root, "docs/a.txt").endswith(os.path.join("docs", "a.txt")))

    def test_dotdot(self):
        with self.assertRaises(PermissionError):
            resolve(self.root, "../secret.txt")

    def test_absolute(self):
        with self.assertRaises(PermissionError):
            resolve(self.root, os.path.join(self.tmp.name, "secret.txt"))

    def test_symlink_escape(self):
        os.symlink(self.tmp.name, os.path.join(self.root, "up"))
        with self.assertRaises(PermissionError):
            resolve(self.root, "up/secret.txt")


if __name__ == "__main__":
    unittest.main()

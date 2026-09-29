import os
import tempfile
import unittest

from logtail import tail


class TailTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp()
        with os.fdopen(fd, "w") as f:
            for i in range(1000):
                f.write(f"{'ERROR' if i % 10 == 0 else 'INFO'} line {i}\n")

    def tearDown(self):
        os.remove(self.path)

    def test_last_lines(self):
        self.assertEqual(tail(self.path, 2), ["INFO line 998", "INFO line 999"])

    def test_filtered(self):
        self.assertEqual(tail(self.path, 2, contains="ERROR"), ["ERROR line 980", "ERROR line 990"])


if __name__ == "__main__":
    unittest.main()

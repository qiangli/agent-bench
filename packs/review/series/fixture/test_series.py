import unittest

from series import deltas, gaps


class SeriesTest(unittest.TestCase):
    def test_deltas(self):
        self.assertEqual(deltas([(0, 1), (10, 4), (20, 2)]), [3, -2])
        self.assertEqual(deltas([(0, 1)]), [])
        self.assertEqual(deltas([]), [])

    def test_deltas_without_input_copy(self):
        class NoSlice(list):
            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("input must not be copied")
                return super().__getitem__(index)

        self.assertEqual(deltas(NoSlice([(0, 1), (10, 4), (20, 2)])), [3, -2])

    def test_gaps(self):
        samples = [(0, 1), (10, 1), (50, 1), (60, 1), (200, 1)]
        self.assertEqual(gaps(samples, 30), [(1, 2), (3, 4)])
        self.assertEqual(gaps(samples, 1000), [])
        self.assertEqual(gaps([(0, 1)], 30), [])
        self.assertEqual(gaps([], 30), [])


if __name__ == "__main__":
    unittest.main()

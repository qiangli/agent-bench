import math, unittest
import stats

class T(unittest.TestCase):
    def test_mean(self): self.assertEqual(stats.mean([1, 2, 4]), 7 / 3)
    def test_median_even(self): self.assertEqual(stats.median([4, 1, 3, 2]), 2.5)
    def test_mode(self): self.assertEqual(stats.mode([3, 1, 3, 1, 2]), 1)
    def test_variance(self): self.assertAlmostEqual(stats.variance([2, 4, 4, 4, 5, 5, 7, 9]), 32 / 7)
    def test_stdev(self): self.assertAlmostEqual(stats.stdev([2, 4, 4, 4, 5, 5, 7, 9]), math.sqrt(32 / 7))
    def test_pct_change(self): self.assertEqual(stats.pct_change(50, 75), 50.0)
    def test_clamp(self): self.assertEqual([stats.clamp(v, 0, 10) for v in (-5, 5, 15)], [0, 5, 10])
    def test_zscore(self): self.assertAlmostEqual(stats.zscore(9, [2, 4, 4, 4, 5, 5, 7, 9]), 4 / math.sqrt(32 / 7))
    def test_q3_mean(self): self.assertEqual(stats.q3_mean(), 42.5)
    def test_median_low(self): self.assertEqual(stats.median([4, 1, 3, 2]), 2)

if __name__ == "__main__":
    unittest.main()

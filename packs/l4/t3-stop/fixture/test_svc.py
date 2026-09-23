import importlib, unittest
from svc import logutil

class T(unittest.TestCase):
    def test_all(self):
        for i in range(1, 7):
            logutil.LINES.clear()
            m = importlib.import_module(f"svc.m{i}")
            self.assertEqual(m.run(4), 6 * i)
            self.assertEqual(logutil.LINES, [f"m{i} start", f"m{i} total={6 * i}"])

if __name__ == "__main__":
    unittest.main()

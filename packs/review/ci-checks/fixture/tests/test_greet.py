import subprocess
import unittest


class GreetTest(unittest.TestCase):
    def test_default(self):
        out = subprocess.run(["sh", "scripts/greet.sh"], capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout, "hello, world\n")


if __name__ == "__main__":
    unittest.main()

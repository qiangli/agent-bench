import os
import subprocess
import tempfile
import unittest

import history


def sh(repo, *args):
    subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   cwd=repo, check=True, capture_output=True)


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        sh(self.repo, "init", "-q", "-b", "main")
        for name in ("a.txt", "-n.txt"):
            with open(os.path.join(self.repo, name), "w") as f:
                f.write(name)
            sh(self.repo, "add", "--", name)
            sh(self.repo, "commit", "-q", "-m", f"add {name}")

    def tearDown(self):
        self.tmp.cleanup()

    def test_current_branch(self):
        self.assertEqual(history.current_branch(self.repo), "main")

    def test_commits_touching(self):
        self.assertEqual(len(history.commits_touching(self.repo, "a.txt")), 1)
        self.assertEqual(len(history.commits_touching(self.repo, "-n.txt")), 1)
        self.assertEqual(history.commits_touching(self.repo, "$(id)"), [])


if __name__ == "__main__":
    unittest.main()

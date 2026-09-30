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

    def test_literal_pathspec(self):
        for name in (":(glob)**", "*.txt"):
            self.assertEqual(history.commits_touching(self.repo, name), [])
            with open(os.path.join(self.repo, name), "w") as f:
                f.write("literal")
            sh(self.repo, "--literal-pathspecs", "add", "--", name)
            sh(self.repo, "commit", "-q", "-m", "add literal filename")
            expected = history._git(self.repo, "rev-parse", "HEAD").strip()
            self.assertEqual(history.commits_touching(self.repo, name), [expected])

    def test_limits(self):
        with self.assertRaises(ValueError):
            history.commits_touching(self.repo, "a.txt", -1)
        self.assertEqual(history.commits_touching(self.repo, "a.txt", 0), [])
        with open(os.path.join(self.repo, "a.txt"), "a") as f:
            f.write("changed")
        sh(self.repo, "commit", "-qam", "update a")
        self.assertEqual(len(history.commits_touching(self.repo, "a.txt", 1)), 1)
        self.assertEqual(len(history.commits_touching(self.repo, "a.txt", 2)), 2)


if __name__ == "__main__":
    unittest.main()

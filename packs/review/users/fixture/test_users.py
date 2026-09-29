import unittest

import users


class UsersTest(unittest.TestCase):
    def setUp(self):
        self.db = users.connect()
        users.add_user(self.db, "ada@example.com", "Ada")
        users.add_user(self.db, "alan@example.com", "Alan")
        users.add_user(self.db, "grace@example.com", "Grace")

    def test_find_by_email(self):
        self.assertEqual(users.find_by_email(self.db, "ada@example.com")["name"], "Ada")
        self.assertIsNone(users.find_by_email(self.db, "nobody@example.com"))

    def test_search_by_name(self):
        names = [u["name"] for u in users.search_by_name(self.db, "A")]
        self.assertEqual(names, ["Ada", "Alan"])


if __name__ == "__main__":
    unittest.main()

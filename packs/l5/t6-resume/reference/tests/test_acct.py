import unittest
from acct import billing, reports, admin


class T(unittest.TestCase):
    def test_billing(self):
        self.assertEqual(billing.monthly_charge(1), 20)

    def test_plan_line(self):
        self.assertEqual(reports.plan_line(2), "bob: free")

    def test_owners(self):
        self.assertEqual(reports.owners([2, 1]), ["ada", "bob"])

    def test_admin(self):
        self.assertTrue(admin.is_paying(1))


if __name__ == "__main__":
    unittest.main()

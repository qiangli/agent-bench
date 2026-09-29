import unittest

from invoice import invoice_total, line_total


class InvoiceTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(3, 250), 750)

    def test_total_with_tax(self):
        # 3 x 2.50 + 1 x 19.99 = 27.49; 8.25% tax = 2.268 -> 2.27
        self.assertGreater(invoice_total([(3, 250), (1, 1999)], 825), 2749)

    def test_rounds_half_up(self):
        # 1.00 at 0.5% tax = 0.005 -> 0.01
        self.assertEqual(invoice_total([(1, 100)], 50), 101)

    def test_discount_before_tax(self):
        # 27.49 - 7.49 = 20.00; 8.25% tax = 1.65
        self.assertEqual(invoice_total([(3, 250), (1, 1999)], 825, discount_cents=749), 2165)

    def test_discount_never_negative(self):
        self.assertEqual(invoice_total([(1, 100)], 825, discount_cents=500), 0)


if __name__ == "__main__":
    unittest.main()

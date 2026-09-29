import unittest

from shipping import EXPRESS_SURCHARGE_CENTS, FLAT_RATE_CENTS, shipping_cents


class ShippingTest(unittest.TestCase):
    def test_small_order_pays_flat_rate(self):
        self.assertEqual(shipping_cents(1000), FLAT_RATE_CENTS)

    def test_member_large_order_is_free(self):
        self.assertEqual(shipping_cents(9000, member=True), 0)

    def test_express_adds_surcharge(self):
        self.assertEqual(shipping_cents(1000, express=True), FLAT_RATE_CENTS + EXPRESS_SURCHARGE_CENTS)


if __name__ == "__main__":
    unittest.main()

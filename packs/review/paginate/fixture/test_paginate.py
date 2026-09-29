import unittest

from paginate import iter_pages, page, page_count


class PageTest(unittest.TestCase):
    def test_first_page(self):
        self.assertEqual(page(list(range(45)), 1), list(range(20)))

    def test_partial_last_page(self):
        self.assertEqual(page(list(range(45)), 3), list(range(40, 45)))

    def test_page_count(self):
        self.assertEqual(page_count(45), 3)
        self.assertEqual(page_count(40), 2)

    def test_iter_pages_starts_at_first_page(self):
        self.assertEqual(next(iter_pages(list(range(45)))), list(range(20)))


if __name__ == "__main__":
    unittest.main()

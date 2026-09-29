import unittest

from dedupe import unique_ids, unique_keys


class DedupeTest(unittest.TestCase):
    def test_unique_ids_keeps_first_seen_order(self):
        events = [{"id": 3}, {"id": 1}, {"id": 3}, {"id": 2}]
        self.assertEqual(unique_ids(events), [3, 1, 2])

    def test_unique_keys_per_source(self):
        events = [{"source": "a", "id": 1}, {"source": "b", "id": 1}, {"source": "a", "id": 1}]
        self.assertEqual(unique_keys(events), [("a", 1), ("b", 1)])


if __name__ == "__main__":
    unittest.main()

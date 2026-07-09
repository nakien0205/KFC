import unittest

from generate_data import add_if_present


class TestGenerateData(unittest.TestCase):
    def test_add_if_present_preserves_order_and_deduplicates(self):
        order_items = []

        add_if_present(order_items, "Burger Zinger")
        add_if_present(order_items, "French Fries")
        add_if_present(order_items, "Burger Zinger")
        add_if_present(order_items, None)

        self.assertEqual(order_items, ["Burger Zinger", "French Fries"])


if __name__ == "__main__":
    unittest.main()

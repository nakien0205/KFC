import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

from customer_store import (
    CustomerStore,
    CustomerStoreError,
    DuplicateCustomerError,
    InvalidCredentialsError,
)


CATALOG = {
    "Burger Zinger": {"price": 85000, "category": "Burgers"},
    "Pepsi": {"price": 19000, "category": "Drinks"},
}


class TestCustomerStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp_dir.name, "customer.db")
        self.store = CustomerStore(self.path)
        self.store.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registration_persists_only_argon_hash_and_rejects_duplicate(self):
        customer = self.store.register_user("Customer@example.test", "long-secret")
        self.assertEqual(customer["email"], "customer@example.test")
        with self.assertRaises(DuplicateCustomerError):
            self.store.register_user("customer@example.test", "another-secret")

        connection = sqlite3.connect(self.path)
        try:
            stored_hash = connection.execute("SELECT password_hash FROM users").fetchone()[0]
        finally:
            connection.close()
        self.assertNotEqual(stored_hash, "long-secret")
        self.assertTrue(stored_hash.startswith("$argon2id$"))
        self.assertEqual(self.store.authenticate("customer@example.test", "long-secret")["id"], customer["id"])
        with self.assertRaises(InvalidCredentialsError):
            self.store.authenticate("customer@example.test", "wrong-secret")
        with self.assertRaises(CustomerStoreError):
            self.store.register_user("not-an-email", "long-secret")

    def test_session_rotation_expiry_and_order_transaction(self):
        customer = self.store.register_user("shopper@example.test", "long-secret")
        first_token, _ = self.store.create_session(customer["id"])
        second_token, _ = self.store.create_session(customer["id"], rotate_existing=True)
        self.assertIsNone(self.store.get_session_user(first_token))
        self.assertEqual(self.store.get_session_user(second_token)["id"], customer["id"])
        expired_token, _ = self.store.create_session(customer["id"], ttl_seconds=-1)
        self.assertIsNone(self.store.get_session_user(expired_token))

        order = self.store.create_completed_order(
            customer["id"], [{"name": "Burger Zinger", "quantity": 2}], CATALOG
        )
        self.assertEqual(order["total_vnd"], 170000.0)
        self.assertEqual(len(self.store.list_completed_orders(customer["id"])), 1)

    def test_concurrent_completed_checkouts_remain_atomic(self):
        customer = self.store.register_user("parallel@example.test", "long-secret")

        def checkout():
            return self.store.create_completed_order(
                customer["id"], [{"name": "Pepsi", "quantity": 1}], CATALOG
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            orders = list(executor.map(lambda _: checkout(), range(2)))
        self.assertEqual(len(orders), 2)
        self.assertEqual(len(self.store.list_completed_orders(customer["id"])), 2)
        with self.assertRaises(CustomerStoreError):
            self.store.create_completed_order(
                customer["id"], [{"name": "Pepsi", "quantity": 0}], CATALOG
            )
        self.assertEqual(len(self.store.list_completed_orders(customer["id"])), 2)


if __name__ == "__main__":
    unittest.main()

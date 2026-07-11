"""Local, isolated persistence for the authenticated customer experience."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import math
import os
import re
import secrets
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Tuple

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type


DEFAULT_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
SESSION_TOKEN_BYTES = 32
MAX_CHECKOUT_QUANTITY = 99
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class CustomerStoreError(ValueError):
    """Base error for safe, client-visible customer-store validation failures."""


class DuplicateCustomerError(CustomerStoreError):
    """Raised when an email has already been registered."""


class InvalidCredentialsError(CustomerStoreError):
    """Raised for an invalid email/password pair without exposing which part failed."""


def resolve_customer_db_path() -> str:
    """Return the deployment/test override or the customer-only default database."""
    configured = os.environ.get("CUSTOMER_DB_PATH", "").strip()
    if configured:
        return os.path.abspath(configured)
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "_bmad-output",
        "data",
        "customer.db",
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class CustomerStore:
    """SQLite access boundary for users, opaque sessions, and completed orders."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = os.path.abspath(db_path or resolve_customer_db_path())
        # Argon2id with a lower interactive-memory profile suitable for local tests.
        self.password_hasher = PasswordHasher(
            time_cost=2,
            memory_cost=19_456,
            parallelism=1,
            type=Type.ID,
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        connection = self._connect()
        try:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS customer_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK (status = 'completed'),
                    completed_at TEXT NOT NULL,
                    total_vnd REAL NOT NULL CHECK (total_vnd >= 0),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS customer_order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    item_name TEXT NOT NULL,
                    item_category TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    unit_price REAL NOT NULL CHECK (unit_price >= 0),
                    FOREIGN KEY (order_id) REFERENCES customer_orders(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS customer_offers (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    target_item TEXT NOT NULL,
                    discount_pct INTEGER NOT NULL,
                    amount_off_vnd REAL NOT NULL,
                    sale_price REAL NOT NULL,
                    display_text TEXT NOT NULL,
                    request_date TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    redeemed_order_id INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (redeemed_order_id) REFERENCES customer_orders(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);
                CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
                CREATE INDEX IF NOT EXISTS idx_customer_orders_user_completed
                    ON customer_orders(user_id, completed_at DESC);
                CREATE INDEX IF NOT EXISTS idx_customer_order_items_order
                    ON customer_order_items(order_id);
                CREATE INDEX IF NOT EXISTS idx_customer_offers_user_expiry
                    ON customer_offers(user_id, expires_at);
                """
            )
        finally:
            connection.close()

    @staticmethod
    def _normalise_email(email: Any) -> str:
        value = str(email or "").strip().lower()
        if len(value) > 254 or not EMAIL_PATTERN.match(value):
            raise CustomerStoreError("Enter a valid email address.")
        return value

    @staticmethod
    def _validate_password(password: Any) -> str:
        if not isinstance(password, str) or len(password) < 8 or len(password) > 1_024:
            raise CustomerStoreError("Password must be between 8 and 1024 characters.")
        return password

    @staticmethod
    def _user_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {"id": int(row["id"]), "email": row["email"], "created_at": row["created_at"]}

    def register_user(self, email: Any, password: Any) -> Dict[str, Any]:
        normalised_email = self._normalise_email(email)
        valid_password = self._validate_password(password)
        password_hash = self.password_hasher.hash(valid_password)
        connection = self._connect()
        try:
            try:
                cursor = connection.execute(
                    "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                    (normalised_email, password_hash, _as_utc_text(_utc_now())),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateCustomerError("An account with this email already exists.") from exc
            row = connection.execute(
                "SELECT id, email, created_at FROM users WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self._user_dict(row)
        finally:
            connection.close()

    def authenticate(self, email: Any, password: Any) -> Dict[str, Any]:
        try:
            normalised_email = self._normalise_email(email)
        except CustomerStoreError as exc:
            raise InvalidCredentialsError("Invalid email or password.") from exc
        if not isinstance(password, str):
            raise InvalidCredentialsError("Invalid email or password.")

        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE email = ?", (normalised_email,)
            ).fetchone()
            if row is None:
                raise InvalidCredentialsError("Invalid email or password.")
            try:
                verified = self.password_hasher.verify(row["password_hash"], password)
            except (InvalidHashError, VerificationError, VerifyMismatchError) as exc:
                raise InvalidCredentialsError("Invalid email or password.") from exc
            if not verified:
                raise InvalidCredentialsError("Invalid email or password.")
            if self.password_hasher.check_needs_rehash(row["password_hash"]):
                connection.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (self.password_hasher.hash(password), row["id"]),
                )
            return self._user_dict(row)
        finally:
            connection.close()

    def create_session(
        self,
        user_id: int,
        ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        rotate_existing: bool = True,
    ) -> Tuple[str, str]:
        try:
            ttl = int(ttl_seconds)
        except (TypeError, ValueError) as exc:
            raise CustomerStoreError("Invalid session duration.") from exc

        token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
        now = _utc_now()
        expires_at = _as_utc_text(now + timedelta(seconds=ttl))
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (_as_utc_text(now),))
            if rotate_existing:
                connection.execute("DELETE FROM sessions WHERE user_id = ?", (int(user_id),))
            connection.execute(
                "INSERT INTO sessions (user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (int(user_id), _token_hash(token), expires_at, _as_utc_text(now)),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return token, expires_at

    def get_session_user(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        if not isinstance(token, str) or not token:
            return None
        now_text = _as_utc_text(_utc_now())
        connection = self._connect()
        try:
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_text,))
            row = connection.execute(
                """
                SELECT users.id, users.email, users.created_at
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_hash = ? AND sessions.expires_at > ?
                """,
                (_token_hash(token), now_text),
            ).fetchone()
            return self._user_dict(row) if row else None
        finally:
            connection.close()

    def revoke_session(self, token: Optional[str]) -> None:
        if not isinstance(token, str) or not token:
            return
        connection = self._connect()
        try:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
        finally:
            connection.close()

    def issue_personal_offer(self, user_id: int, offer: Dict[str, Any]) -> Dict[str, Any]:
        """Persist server-generated offer facts for later authenticated redemption."""
        if not isinstance(offer, dict):
            raise CustomerStoreError("Personal offer is invalid.")
        offer_id = str(offer.get("offer_id") or "").strip()
        target_item = str(offer.get("target_item") or "").strip()
        request_date = str(offer.get("request_date") or "").strip()
        display_text = str(offer.get("display_text") or "").strip()
        try:
            discount_pct = int(offer.get("discount_pct"))
            amount_off = float(offer.get("amount_off_vnd"))
            sale_price = float(offer.get("sale_price"))
            datetime.fromisoformat(f"{request_date}T00:00:00+00:00")
        except (TypeError, ValueError) as exc:
            raise CustomerStoreError("Personal offer is invalid.") from exc
        if (
            not offer_id
            or not target_item
            or not display_text
            or discount_pct not in {5, 10, 15, 20}
            or amount_off < 0
            or sale_price < 0
        ):
            raise CustomerStoreError("Personal offer is invalid.")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            issued_at = _utc_now()
            issued_at_text = _as_utc_text(issued_at)
            expires_at = datetime.combine(
                (issued_at + timedelta(days=1)).date(), datetime.min.time(), tzinfo=timezone.utc
            )
            expires_at_text = _as_utc_text(expires_at)
            existing = connection.execute(
                "SELECT user_id, redeemed_order_id FROM customer_offers WHERE id = ?", (offer_id,)
            ).fetchone()
            if existing is not None and int(existing["user_id"]) != int(user_id):
                raise CustomerStoreError("Personal offer is invalid.")
            if existing is not None and existing["redeemed_order_id"] is not None:
                raise CustomerStoreError("Personal offer is no longer available.")

            # A different request context must not leave the previous offer redeemable.
            connection.execute(
                """
                UPDATE customer_offers
                SET expires_at = ?
                WHERE user_id = ? AND id != ? AND redeemed_order_id IS NULL AND expires_at > ?
                """,
                (issued_at_text, int(user_id), offer_id, issued_at_text),
            )
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO customer_offers
                        (id, user_id, target_item, discount_pct, amount_off_vnd, sale_price,
                         display_text, request_date, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        offer_id,
                        int(user_id),
                        target_item,
                        discount_pct,
                        amount_off,
                        sale_price,
                        display_text,
                        request_date,
                        expires_at_text,
                        issued_at_text,
                    ),
                )
            else:
                # Re-activate the deterministic unredeemed offer if its context becomes current again.
                connection.execute(
                    """
                    UPDATE customer_offers
                    SET target_item = ?, discount_pct = ?, amount_off_vnd = ?, sale_price = ?,
                        display_text = ?, request_date = ?, expires_at = ?, created_at = ?
                    WHERE id = ? AND user_id = ? AND redeemed_order_id IS NULL
                    """,
                    (
                        target_item,
                        discount_pct,
                        amount_off,
                        sale_price,
                        display_text,
                        request_date,
                        expires_at_text,
                        issued_at_text,
                        offer_id,
                        int(user_id),
                    ),
                )
            row = connection.execute(
                """
                SELECT id, target_item, discount_pct, amount_off_vnd, sale_price,
                       display_text, request_date, expires_at
                FROM customer_offers
                WHERE id = ? AND user_id = ? AND redeemed_order_id IS NULL AND expires_at > ?
                """,
                (offer_id, int(user_id), issued_at_text),
            ).fetchone()
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        if row is None:
            raise CustomerStoreError("Personal offer is no longer available.")
        return {
            "type": "personal",
            "offer_id": row["id"],
            "target_item": row["target_item"],
            "discount_pct": int(row["discount_pct"]),
            "amount_off_vnd": float(row["amount_off_vnd"]),
            "sale_price": float(row["sale_price"]),
            "display_text": row["display_text"],
            "request_date": row["request_date"],
        }

    @staticmethod
    def _validated_cart(
        cart_items: Any, catalog: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not isinstance(cart_items, list) or not cart_items:
            raise CustomerStoreError("Cart must contain at least one item.")
        validated: List[Dict[str, Any]] = []
        seen_names = set()
        for line in cart_items:
            if not isinstance(line, dict):
                raise CustomerStoreError("Each cart item must include a name and quantity.")
            name = str(line.get("name") or "").strip()
            quantity = line.get("quantity")
            if (
                not name
                or isinstance(quantity, bool)
                or not isinstance(quantity, int)
                or quantity <= 0
                or quantity > MAX_CHECKOUT_QUANTITY
            ):
                raise CustomerStoreError(f"Cart quantities must be whole numbers from 1 to {MAX_CHECKOUT_QUANTITY}.")
            if name in seen_names:
                raise CustomerStoreError("Cart items must not contain duplicate names.")
            menu_item = catalog.get(name)
            if not isinstance(menu_item, dict):
                raise CustomerStoreError(f"Unknown menu item: {name}.")
            try:
                unit_price = float(menu_item["price"])
            except (KeyError, TypeError, ValueError) as exc:
                raise CustomerStoreError(f"Menu item has an invalid price: {name}.") from exc
            if not math.isfinite(unit_price) or unit_price < 0:
                raise CustomerStoreError(f"Menu item has an invalid price: {name}.")
            seen_names.add(name)
            validated.append(
                {
                    "name": name,
                    "category": str(menu_item.get("category") or ""),
                    "quantity": quantity,
                    "unit_price": unit_price,
                }
            )
        return validated

    def create_completed_order(
        self,
        user_id: int,
        cart_items: Any,
        catalog: Dict[str, Dict[str, Any]],
        completed_at: Optional[datetime] = None,
        offer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        validated_items = self._validated_cart(cart_items, catalog)
        timestamp = _as_utc_text(completed_at or _utc_now())
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            applied_offer_id = None
            if offer_id:
                offer_row = connection.execute(
                    """
                    SELECT id, target_item, sale_price
                    FROM customer_offers
                    WHERE id = ? AND user_id = ? AND expires_at > ? AND redeemed_order_id IS NULL
                    """,
                    (str(offer_id), int(user_id), _as_utc_text(_utc_now())),
                ).fetchone()
                if offer_row is None:
                    raise CustomerStoreError("Personal offer is unavailable or expired.")
                offered_item = next(
                    (item for item in validated_items if item["name"] == offer_row["target_item"]), None
                )
                if offered_item is None or offered_item["quantity"] != 1:
                    raise CustomerStoreError("Personal offer requires exactly one eligible target item.")
                offered_item["unit_price"] = float(offer_row["sale_price"])
                applied_offer_id = str(offer_row["id"])
            total = sum(item["unit_price"] * item["quantity"] for item in validated_items)
            if not math.isfinite(total) or total < 0:
                raise CustomerStoreError("Cart total is invalid.")
            cursor = connection.execute(
                """
                INSERT INTO customer_orders (user_id, status, completed_at, total_vnd)
                VALUES (?, 'completed', ?, ?)
                """,
                (int(user_id), timestamp, total),
            )
            order_id = int(cursor.lastrowid)
            if applied_offer_id:
                connection.execute(
                    "UPDATE customer_offers SET redeemed_order_id = ? WHERE id = ?",
                    (order_id, applied_offer_id),
                )
            connection.executemany(
                """
                INSERT INTO customer_order_items
                    (order_id, item_name, item_category, quantity, unit_price)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (order_id, item["name"], item["category"], item["quantity"], item["unit_price"])
                    for item in validated_items
                ],
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return {
            "id": order_id,
            "status": "completed",
            "completed_at": timestamp,
            "total_vnd": round(total, 2),
            "items": validated_items,
            "applied_offer_id": applied_offer_id,
        }

    def list_completed_orders(self, user_id: int) -> List[Dict[str, Any]]:
        connection = self._connect()
        try:
            order_rows = connection.execute(
                """
                SELECT id, completed_at, total_vnd
                FROM customer_orders
                WHERE user_id = ? AND status = 'completed'
                ORDER BY completed_at ASC, id ASC
                """,
                (int(user_id),),
            ).fetchall()
            if not order_rows:
                return []
            order_ids = [int(row["id"]) for row in order_rows]
            placeholders = ", ".join("?" for _ in order_ids)
            item_rows = connection.execute(
                f"""
                SELECT order_id, item_name, item_category, quantity, unit_price
                FROM customer_order_items
                WHERE order_id IN ({placeholders})
                ORDER BY id ASC
                """,
                order_ids,
            ).fetchall()
        finally:
            connection.close()

        items_by_order: Dict[int, List[Dict[str, Any]]] = {order_id: [] for order_id in order_ids}
        for row in item_rows:
            items_by_order[int(row["order_id"])].append(
                {
                    "name": row["item_name"],
                    "category": row["item_category"],
                    "quantity": int(row["quantity"]),
                    "unit_price": float(row["unit_price"]),
                }
            )
        return [
            {
                "id": int(row["id"]),
                "completed_at": row["completed_at"],
                "total_vnd": float(row["total_vnd"]),
                "items": items_by_order[int(row["id"])],
            }
            for row in order_rows
        ]

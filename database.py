import hashlib
import hmac
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime

DB_NAME = "finance_tracker.db"


@contextmanager
def get_connection():
    """Provide a SQLite connection that always closes cleanly."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def _column_names(cursor, table_name):
    return {row[1] for row in cursor.execute(f"PRAGMA table_info({table_name})")}


def _password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return salt.hex(), digest.hex()


def create_database():
    """Create tables and migrate legacy single-user data safely."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT COLLATE NOCASE,
                currency TEXT NOT NULL DEFAULT '₹',
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        if "email" not in _column_names(cursor, "users"):
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT COLLATE NOCASE")
        if "currency" not in _column_names(cursor, "users"):
            cursor.execute("ALTER TABLE users ADD COLUMN currency TEXT NOT NULL DEFAULT '₹'")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, category),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL NOT NULL DEFAULT 0,
                target_date TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Migrate databases created by the original single-user version. Existing
        # rows are kept under an inaccessible legacy owner, never exposed to a
        # newly registered user, so every new account starts empty.
        legacy_id = "legacy-data-owner"
        salt, password_hash = _password_hash(secrets.token_urlsafe(32))
        cursor.execute("""
            INSERT OR IGNORE INTO users (id, username, email, currency, password_salt, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (legacy_id, "legacy-data-owner", None, "₹", salt, password_hash, datetime.now().isoformat()))

        for table in ("transactions", "savings_goals"):
            if "user_id" not in _column_names(cursor, table):
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT")
            cursor.execute(f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (legacy_id,))

        # The old budgets table used category as its sole primary key. Rebuild
        # it so the same category can exist independently for every user.
        budget_columns = _column_names(cursor, "budgets")
        if "user_id" not in budget_columns:
            cursor.execute("ALTER TABLE budgets RENAME TO budgets_legacy")
            cursor.execute("""
                CREATE TABLE budgets (
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    monthly_limit REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, category),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                INSERT INTO budgets (user_id, category, monthly_limit, updated_at)
                SELECT ?, category, monthly_limit, updated_at FROM budgets_legacy
            """, (legacy_id,))
            cursor.execute("DROP TABLE budgets_legacy")

        # Add indexes used by every authenticated query.
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, date DESC, id DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_user_id ON savings_goals(user_id, id DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_budgets_user_id ON budgets(user_id, category)")
        conn.commit()


def create_user(username, password, email=None):
    username = username.strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if len(username) > 50:
        raise ValueError("Username must be 50 characters or fewer.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    email = email.strip().lower() if email else None
    if email and ("@" not in email or "." not in email.rsplit("@", 1)[-1]):
        raise ValueError("Please enter a valid email address.")
    user_id = str(uuid.uuid4())
    salt, password_hash = _password_hash(password)
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO users (id, username, email, currency, password_salt, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, email, "₹", salt, password_hash, datetime.now().isoformat()))
            conn.commit()
    except sqlite3.IntegrityError as exc:
        if "email" in str(exc).lower():
            raise ValueError("That email address is already registered.") from exc
        raise ValueError("That username is already registered.") from exc
    return user_id


def get_user_profile(user_id):
    with get_connection() as conn:
        row = conn.execute("SELECT id, username, email, currency, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"id": row[0], "username": row[1], "email": row[2], "currency": row[3], "created_at": row[4]} if row else None


def update_user_profile(user_id, username, email, currency):
    username = username.strip()
    email = email.strip().lower()
    if len(username) < 3 or len(username) > 50:
        raise ValueError("Username must be between 3 and 50 characters.")
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise ValueError("Please enter a valid email address.")
    try:
        with get_connection() as conn:
            conn.execute("UPDATE users SET username = ?, email = ?, currency = ? WHERE id = ?", (username, email, currency, user_id))
            conn.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("That username or email is already in use.") from exc


def delete_user_account(user_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()


def verify_user(username, password):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, password_salt, password_hash FROM users WHERE username = ? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
    if row is None:
        return None
    salt, expected_hash = row[2], row[3]
    _, actual_hash = _password_hash(password, bytes.fromhex(salt))
    if not hmac.compare_digest(actual_hash, expected_hash):
        return None
    return {"id": row[0], "username": row[1]}


def get_user_by_email(email):
    """Return a reset target for the internal reset flow."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, email FROM users WHERE email = ? COLLATE NOCASE",
            (email.strip().lower(),),
        ).fetchone()
    return {"id": row[0], "username": row[1], "email": row[2]} if row else None


def reset_user_password(user_id, new_password):
    """Hash and replace a password after successful OTP verification."""
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    salt, password_hash = _password_hash(new_password)
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET password_salt = ?, password_hash = ? WHERE id = ?",
            (salt, password_hash, user_id),
        )
        conn.commit()
    return cursor.rowcount == 1


# ==================================================
# TRANSACTIONS
# ==================================================

def add_transaction(user_id, transaction_date, transaction_type, category, amount, description):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO transactions (user_id, date, type, category, amount, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, transaction_date, transaction_type, category, amount, description))
        conn.commit()


def get_transactions(user_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT id, date, type, category, amount, description
            FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
        """, (user_id,)).fetchall()


def delete_transaction(user_id, transaction_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
        conn.commit()


# ==================================================
# BUDGETS
# ==================================================

def set_budget(user_id, category, monthly_limit):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO budgets (user_id, category, monthly_limit, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, category) DO UPDATE SET
                monthly_limit = excluded.monthly_limit,
                updated_at = excluded.updated_at
        """, (user_id, category, monthly_limit, datetime.now().isoformat()))
        conn.commit()


def get_budgets(user_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT category, monthly_limit FROM budgets WHERE user_id = ? ORDER BY category",
            (user_id,),
        ).fetchall()


def delete_budget(user_id, category):
    with get_connection() as conn:
        conn.execute("DELETE FROM budgets WHERE category = ? AND user_id = ?", (category, user_id))
        conn.commit()


# ==================================================
# SAVINGS GOALS
# ==================================================

def add_savings_goal(user_id, name, target_amount, target_date):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO savings_goals (user_id, name, target_amount, current_amount, target_date, created_at)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (user_id, name, target_amount, target_date, datetime.now().isoformat()))
        conn.commit()


def get_savings_goals(user_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT id, name, target_amount, current_amount, target_date
            FROM savings_goals
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()


def update_savings_goal_amount(user_id, goal_id, new_amount):
    with get_connection() as conn:
        conn.execute(
            "UPDATE savings_goals SET current_amount = ? WHERE id = ? AND user_id = ?",
            (new_amount, goal_id, user_id),
        )
        conn.commit()


def delete_savings_goal(user_id, goal_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
        conn.commit()

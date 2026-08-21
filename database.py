import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_NAME = "finance_tracker.db"


@contextmanager
def get_connection():
    """Provide a SQLite connection that always closes cleanly."""
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
    finally:
        conn.close()


def create_database():
    """Create all tables if they don't already exist."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL NOT NULL DEFAULT 0,
                target_date TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.commit()


# ==================================================
# TRANSACTIONS
# ==================================================

def add_transaction(transaction_date, transaction_type, category, amount, description):
    """Insert a new transaction row."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (date, type, category, amount, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (transaction_date, transaction_type, category, amount, description),
        )
        conn.commit()


def get_transactions():
    """Return all transactions, most recent first."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, date, type, category, amount, description
            FROM transactions
            ORDER BY date DESC, id DESC
            """
        )
        return cursor.fetchall()


def delete_transaction(transaction_id):
    """Delete a single transaction by id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()


# ==================================================
# BUDGETS
# ==================================================

def set_budget(category, monthly_limit):
    """Create or update the monthly budget limit for a category."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO budgets (category, monthly_limit, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(category) DO UPDATE SET
                monthly_limit = excluded.monthly_limit,
                updated_at = excluded.updated_at
            """,
            (category, monthly_limit, datetime.now().isoformat()),
        )
        conn.commit()


def get_budgets():
    """Return all budgets as a list of (category, monthly_limit) tuples."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT category, monthly_limit FROM budgets ORDER BY category")
        return cursor.fetchall()


def delete_budget(category):
    """Remove the budget set for a category."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM budgets WHERE category = ?", (category,))
        conn.commit()


# ==================================================
# SAVINGS GOALS
# ==================================================

def add_savings_goal(name, target_amount, target_date):
    """Create a new savings goal."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO savings_goals (name, target_amount, current_amount, target_date, created_at)
            VALUES (?, ?, 0, ?, ?)
            """,
            (name, target_amount, target_date, datetime.now().isoformat()),
        )
        conn.commit()


def get_savings_goals():
    """Return all savings goals, most recently created first."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, target_amount, current_amount, target_date
            FROM savings_goals
            ORDER BY id DESC
            """
        )
        return cursor.fetchall()


def update_savings_goal_amount(goal_id, new_amount):
    """Set the current saved amount for a goal."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE savings_goals SET current_amount = ? WHERE id = ?",
            (new_amount, goal_id),
        )
        conn.commit()


def delete_savings_goal(goal_id):
    """Delete a savings goal."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM savings_goals WHERE id = ?", (goal_id,))
        conn.commit()
import os
import sqlite3
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    db_path = Path(tmp) / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, type TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL, description TEXT);
        CREATE TABLE budgets (category TEXT PRIMARY KEY, monthly_limit REAL NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE savings_goals (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, target_amount REAL NOT NULL, current_amount REAL NOT NULL DEFAULT 0, target_date TEXT, created_at TEXT NOT NULL);
        INSERT INTO transactions (date,type,category,amount,description) VALUES ('2026-01-01','Income','Salary',1000,'legacy');
        INSERT INTO budgets (category,monthly_limit,updated_at) VALUES ('Food',200,'2026-01-01');
        INSERT INTO savings_goals (name,target_amount,current_amount,target_date,created_at) VALUES ('Old goal',500,10,'2027-01-01','2026-01-01');
    """)
    conn.commit(); conn.close()

    import database
    database.DB_NAME = str(db_path)
    database.create_database()
    new_user = database.create_user("newuser", "newuser-password")
    assert database.get_transactions(new_user) == []
    assert database.get_budgets(new_user) == []
    assert database.get_savings_goals(new_user) == []
    assert database.get_connection is not None

print("legacy migration test passed")

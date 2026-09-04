import os
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    import database

    database.DB_NAME = str(Path(tmp) / "test.db")
    database.create_database()
    alice = database.create_user("alice", "alice-password")
    bob = database.create_user("bob", "bob-password")

    assert alice != bob
    assert database.verify_user("alice", "alice-password")["id"] == alice
    assert database.verify_user("alice", "wrong-password") is None

    database.add_transaction(alice, "2026-09-01", "Income", "Salary", 100000, "Alice salary")
    database.add_transaction(bob, "2026-09-01", "Income", "Salary", 50000, "Bob salary")
    assert len(database.get_transactions(alice)) == 1
    assert database.get_transactions(alice)[0][-1] == "Alice salary"
    assert len(database.get_transactions(bob)) == 1
    assert database.get_transactions(bob)[0][-1] == "Bob salary"

    database.set_budget(alice, "Food", 10000)
    database.set_budget(bob, "Food", 5000)
    assert database.get_budgets(alice) == [("Food", 10000.0)]
    assert database.get_budgets(bob) == [("Food", 5000.0)]

    database.add_savings_goal(alice, "Emergency Fund", 200000, "2027-01-01")
    database.add_savings_goal(bob, "Vacation", 80000, "2027-06-01")
    alice_goal = database.get_savings_goals(alice)[0][0]
    bob_goal = database.get_savings_goals(bob)[0][0]
    assert database.get_savings_goals(alice)[0][1] == "Emergency Fund"
    assert database.get_savings_goals(bob)[0][1] == "Vacation"

    # Cross-user writes must be no-ops, not edits/deletes.
    database.delete_transaction(bob, database.get_transactions(alice)[0][0])
    database.delete_budget(bob, "Food")
    database.update_savings_goal_amount(bob, alice_goal, 999999)
    database.delete_savings_goal(bob, alice_goal)
    assert len(database.get_transactions(alice)) == 1
    assert database.get_budgets(alice) == [("Food", 10000.0)]
    assert database.get_savings_goals(alice)[0][3] == 0.0
    assert len(database.get_savings_goals(alice)) == 1
    assert bob_goal not in [row[0] for row in database.get_savings_goals(alice)]

print("two-user isolation test passed")

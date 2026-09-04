from finance_ml import (
    detect_expense_anomalies,
    financial_health_score,
    predict_next_month_expenses,
    simulate_finances,
    suggest_expense_category,
)

alice_transactions = [
    (1, "2026-01-05", "Income", "Salary", 100000.0, "salary"),
    (2, "2026-01-06", "Expense", "Food", 1000.0, "groceries"),
    (3, "2026-02-05", "Income", "Salary", 100000.0, "salary"),
    (4, "2026-02-06", "Expense", "Food", 1100.0, "groceries"),
    (5, "2026-03-05", "Income", "Salary", 100000.0, "salary"),
    (6, "2026-03-06", "Expense", "Food", 1200.0, "groceries"),
    (7, "2026-03-07", "Expense", "Food", 1200.0, "groceries"),
    (8, "2026-03-08", "Expense", "Food", 12000.0, "large purchase"),
]
bob_transactions = [
    (8, "2026-01-05", "Income", "Salary", 50000.0, "salary"),
    (9, "2026-01-06", "Expense", "Rent", 20000.0, "rent"),
    (10, "2026-02-05", "Income", "Salary", 50000.0, "salary"),
    (11, "2026-02-06", "Expense", "Rent", 20000.0, "rent"),
]

assert predict_next_month_expenses(alice_transactions)["status"] == "ok"
assert predict_next_month_expenses(bob_transactions)["status"] == "ok"
assert predict_next_month_expenses(alice_transactions)["amount"] != predict_next_month_expenses(bob_transactions)["amount"]
assert detect_expense_anomalies(alice_transactions)["status"] == "ok"
assert any(item["amount"] == 12000.0 for item in detect_expense_anomalies(alice_transactions)["anomalies"])
assert financial_health_score(alice_transactions, [("Food", 5000.0)], [(1, "Fund", 100000.0, 20000.0, None)])["score"] is not None
assert simulate_finances(alice_transactions, [(1, "Fund", 100000.0, 20000.0, None)], extra_monthly_saving=5000)["difference"] > 0
assert suggest_expense_category("Swiggy dinner")['category'] == "Food"
assert predict_next_month_expenses([(1, "2026-01-01", "Income", "Salary", 1, "x")])["status"] == "insufficient"

print("finance ML feature tests passed")

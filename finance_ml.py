"""Explainable data features for the logged-in user's finance data only.

The functions in this module accept already-filtered transaction/budget/goal data;
they never query the database or use data from another user.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


EXPENSE_KEYWORDS = {
    "Food": ("food", "grocery", "groceries", "swiggy", "zomato", "restaurant", "cafe", "lunch", "dinner"),
    "Bills": ("electricity", "water bill", "internet", "mobile bill", "phone bill", "utility", "bill"),
    "Travel": ("uber", "ola", "taxi", "cab", "flight", "train", "bus", "metro", "fuel", "petrol", "travel"),
    "Rent": ("rent", "lease"),
    "Shopping": ("amazon", "flipkart", "shopping", "clothes", "fashion", "mall"),
    "Entertainment": ("netflix", "spotify", "movie", "cinema", "prime video", "game", "entertainment"),
    "Healthcare": ("doctor", "hospital", "medicine", "pharmacy", "health"),
    "Education": ("course", "college", "school", "book", "tuition", "education"),
}


def transactions_frame(transactions) -> pd.DataFrame:
    columns = ["ID", "Date", "Type", "Category", "Amount", "Description"]
    frame = pd.DataFrame(transactions, columns=columns)
    if not frame.empty:
        frame["Date"] = pd.to_datetime(frame["Date"])
        frame["Amount"] = pd.to_numeric(frame["Amount"], errors="coerce").fillna(0.0)
    return frame


def predict_next_month_expenses(transactions) -> dict[str, Any]:
    """Predict next month's expenses using a trend regression over monthly totals."""
    frame = transactions_frame(transactions)
    expenses = frame[frame["Type"] == "Expense"].copy()
    if expenses.empty:
        return {"status": "insufficient", "message": "Add expense transactions to generate a prediction."}
    monthly = expenses.assign(Month=expenses["Date"].dt.to_period("M")).groupby("Month")["Amount"].sum().sort_index()
    if len(monthly) < 2:
        return {"status": "insufficient", "message": "At least two months of expense history are needed for a trend prediction."}

    # Linear regression is transparent: x is month number and y is that month's total.
    from sklearn.linear_model import LinearRegression
    import numpy as np

    x = np.arange(len(monthly), dtype=float).reshape(-1, 1)
    y = monthly.to_numpy(dtype=float)
    model = LinearRegression().fit(x, y)
    prediction = max(0.0, float(model.predict([[len(monthly)]])[0]))
    mae = None
    if len(monthly) >= 3:
        holdout = LinearRegression().fit(x[:-1], y[:-1]).predict([[len(monthly) - 1]])[0]
        mae = abs(float(y[-1] - holdout))

    category_predictions = {}
    if len(monthly) >= 3:
        category_monthly = expenses.assign(Month=expenses["Date"].dt.to_period("M")).pivot_table(
            index="Month", columns="Category", values="Amount", aggfunc="sum", fill_value=0
        ).sort_index()
        for category in category_monthly.columns:
            values = category_monthly[category].to_numpy(dtype=float)
            if len(values) >= 3 and values.sum() > 0:
                category_model = LinearRegression().fit(
                    np.arange(len(values), dtype=float).reshape(-1, 1), values
                )
                category_predictions[category] = max(0.0, float(category_model.predict([[len(values)]])[0]))

    next_month = (monthly.index[-1] + 1).strftime("%B %Y")
    return {
        "status": "ok",
        "amount": prediction,
        "month": next_month,
        "history_months": len(monthly),
        "mae": mae,
        "category_predictions": category_predictions,
        "explanation": "A linear regression was fitted to your monthly expense totals; older months influence the trend, and the latest completed month is reserved for a simple error estimate when enough history exists.",
    }


def detect_expense_anomalies(transactions) -> dict[str, Any]:
    """Flag high expenses using robust per-category median/MAD thresholds."""
    frame = transactions_frame(transactions)
    expenses = frame[frame["Type"] == "Expense"].copy()
    if len(expenses) < 5:
        return {"status": "insufficient", "message": "At least five expense transactions are needed for anomaly detection.", "anomalies": []}

    anomalies = []
    for category, group in expenses.groupby("Category"):
        values = group["Amount"]
        median = float(values.median())
        mad = float((values - median).abs().median())
        # MAD is robust to a single large purchase. Fall back to a relative rule
        # when all normal transactions have the exact same amount.
        threshold = median + max(3.0 * mad, median * 0.75, 100.0)
        for _, row in group[group["Amount"] > threshold].iterrows():
            anomalies.append({
                "date": row["Date"].strftime("%d %b %Y"),
                "category": str(category),
                "amount": float(row["Amount"]),
                "reason": f"{row['Amount']:.2f} is unusually high for {category}; the category median is {median:.2f}.",
            })
    anomalies.sort(key=lambda item: item["amount"], reverse=True)
    return {"status": "ok", "anomalies": anomalies, "explanation": "Each expense is compared with the median and median absolute deviation of the same category, which is less sensitive to normal outliers than a simple average."}


def suggest_expense_category(description: str) -> dict[str, str] | None:
    text = (description or "").strip().lower()
    if not text:
        return None
    for category, keywords in EXPENSE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return {"category": category, "reason": f"Matched the description to the keyword '{keyword}'."}
    return None


def financial_health_score(transactions, budgets, goals) -> dict[str, Any]:
    """Calculate a deterministic 0-100 score from five explainable factors."""
    frame = transactions_frame(transactions)
    income = float(frame.loc[frame["Type"] == "Income", "Amount"].sum()) if not frame.empty else 0.0
    expense = float(frame.loc[frame["Type"] == "Expense", "Amount"].sum()) if not frame.empty else 0.0
    if income <= 0 and expense <= 0:
        return {"score": None, "message": "Add income and expense transactions to calculate your financial health score."}

    savings_rate = max(-1.0, min(1.0, (income - expense) / income)) if income else -1.0
    savings_factor = max(0.0, min(25.0, savings_rate * 25.0))
    ratio_factor = max(0.0, min(25.0, (1.0 - (expense / income if income else 2.0)) * 25.0))

    monthly_budget_rows = []
    for category, limit in budgets:
        category_spend = float(frame.loc[(frame["Type"] == "Expense") & (frame["Category"] == category), "Amount"].sum())
        monthly_budget_rows.append(min(1.0, float(limit) / max(category_spend, float(limit))))
    budget_factor = (sum(monthly_budget_rows) / len(monthly_budget_rows) * 20.0) if monthly_budget_rows else 10.0

    goal_progress = [min(1.0, float(current) / float(target)) for _, _, target, current, _ in goals if float(target) > 0]
    goal_factor = (sum(goal_progress) / len(goal_progress) * 15.0) if goal_progress else 7.5

    months = frame["Date"].dt.to_period("M").nunique() if not frame.empty else 0
    consistency_factor = min(15.0, months * 3.0)
    score = round(max(0.0, min(100.0, savings_factor + ratio_factor + budget_factor + goal_factor + consistency_factor)))
    factors = {
        "Savings rate": round(savings_factor, 1),
        "Expense-to-income ratio": round(ratio_factor, 1),
        "Budget adherence": round(budget_factor, 1),
        "Savings-goal progress": round(goal_factor, 1),
        "Saving consistency": round(consistency_factor, 1),
    }
    suggestions = []
    if savings_rate < 0: suggestions.append("Reduce discretionary expenses so monthly cash flow becomes positive.")
    elif savings_rate < 0.2: suggestions.append("Try to build the savings rate toward 20% of income.")
    if budget_factor < 14: suggestions.append("Review categories that are close to or above their budgets.")
    if not goals: suggestions.append("Create a savings goal to give your surplus a measurable purpose.")
    return {"score": score, "factors": factors, "suggestions": suggestions or ["Your indicators are balanced; keep reviewing them monthly."], "explanation": "The score is the sum of five weighted indicators: savings rate (25), expense ratio (25), budget adherence (20), goal progress (15), and month-to-month consistency (15)."}


def simulate_finances(transactions, goals, extra_monthly_saving=0.0, category_reduction=None, reduction_percent=0.0) -> dict[str, Any]:
    frame = transactions_frame(transactions)
    if frame.empty:
        income = expenses = 0.0
    else:
        frame["Month"] = frame["Date"].dt.to_period("M")
        months = max(1, int(frame["Month"].nunique()))
        income = float(frame.loc[frame["Type"] == "Income", "Amount"].sum()) / months
        expenses = float(frame.loc[frame["Type"] == "Expense", "Amount"].sum()) / months
    if category_reduction:
        category_expenses = float(frame.loc[(frame["Type"] == "Expense") & (frame["Category"] == category_reduction), "Amount"].sum()) / max(1, int(frame["Month"].nunique()))
        expenses = max(0.0, expenses - category_expenses * max(0.0, min(100.0, reduction_percent)) / 100.0)
    current_surplus = income - expenses
    simulated_surplus = income - expenses + max(0.0, extra_monthly_saving)
    goal_estimates = []
    for _, name, target, current, _ in goals:
        remaining = max(0.0, float(target) - float(current))
        months = None if simulated_surplus <= 0 else int((remaining + simulated_surplus - 1) // simulated_surplus)
        goal_estimates.append({"name": name, "remaining": remaining, "months": months})
    return {"current_surplus": current_surplus, "simulated_surplus": simulated_surplus, "difference": simulated_surplus - current_surplus, "goal_estimates": goal_estimates}

import streamlit as st
import pandas as pd
from datetime import date

from auth import require_login
from database import (
    create_database, get_transactions, set_budget, get_budgets, delete_budget
)
from utils import inject_css, page_header, section_divider, format_currency, EXPENSE_CATEGORIES
from finance_tools import budget_alerts, build_report_pdf
from finance_ml import financial_health_score, predict_next_month_expenses
from database import get_savings_goals, get_user_profile

st.set_page_config(page_title="Budget Tracking", page_icon="🎯", layout="wide")
inject_css()

create_database()
user_id, username = require_login()

page_header("Budget Tracking", "Set a monthly spending limit per category and track progress.")

if "budget_saved" not in st.session_state:
    st.session_state.budget_saved = False
if "budget_deleted" not in st.session_state:
    st.session_state.budget_deleted = False

if st.session_state.budget_saved:
    st.success("Budget saved.")
    st.session_state.budget_saved = False
if st.session_state.budget_deleted:
    st.success("Budget removed.")
    st.session_state.budget_deleted = False


# ==================================================
# SET A BUDGET
# ==================================================

st.header("Set a Budget")

with st.form("set_budget_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        budget_category = st.selectbox("Category", EXPENSE_CATEGORIES)
    with col2:
        budget_limit = st.number_input("Monthly Limit (₹)", min_value=0.0, step=500.0, format="%.2f")

    submitted = st.form_submit_button("Save Budget", type="primary")

    if submitted:
        if budget_limit <= 0:
            st.error("Please enter a limit greater than ₹0.")
        else:
            set_budget(user_id, budget_category, budget_limit)
            st.session_state.budget_saved = True
            st.rerun()


# ==================================================
# BUDGET PROGRESS (current month)
# ==================================================

section_divider()

today = date.today()
month_label = today.strftime("%B %Y")
st.header(f"This Month's Progress — {month_label}")

budgets = get_budgets(user_id)
transactions = get_transactions(user_id)
goals = get_savings_goals(user_id)
alerts = budget_alerts(budgets, transactions)

if alerts:
    st.warning("Monthly budget alerts")
    for alert in alerts:
        label = "over budget" if alert["level"] == "over" else "at least 75% used"
        st.write(f"**{alert['category']}** is {label}: {format_currency(alert['spent'])} of {format_currency(alert['limit'])} ({alert['percent']*100:.0f}%).")

profile = get_user_profile(user_id)
health = financial_health_score(transactions, budgets, goals)
prediction = predict_next_month_expenses(transactions)
report = build_report_pdf(profile["username"], transactions, budgets, goals, health, prediction, alerts)
st.download_button("Download monthly PDF report", report, f"finance_report_{today.isoformat()}.pdf", "application/pdf")

if not budgets:
    st.info("No budgets set yet. Add one above to start tracking.")
else:
    df = pd.DataFrame(transactions, columns=["ID", "Date", "Type", "Category", "Amount", "Description"]) if transactions else pd.DataFrame(columns=["ID", "Date", "Type", "Category", "Amount", "Description"])

    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"])
        this_month = df[
            (df["Type"] == "Expense")
            & (df["Date"].dt.year == today.year)
            & (df["Date"].dt.month == today.month)
        ]
        spent_by_category = this_month.groupby("Category")["Amount"].sum().to_dict()
    else:
        spent_by_category = {}

    for category, limit in budgets:

        spent = spent_by_category.get(category, 0.0)
        pct = min(spent / limit, 1.0) if limit > 0 else 0.0
        over = spent > limit

        if pct < 0.75:
            badge = '<span class="badge-ok">On Track</span>'
        elif pct < 1.0:
            badge = '<span class="badge-warn">Near Limit</span>'
        else:
            badge = '<span class="badge-over">Over Budget</span>'

        col_a, col_b = st.columns([5, 1])

        with col_a:
            st.markdown(
                f"""<div class="card">
                    <div class="card-title">{category} &nbsp; {badge}</div>
                    <div class="card-sub">{format_currency(spent)} spent of {format_currency(limit)} budgeted
                    {' — over by ' + format_currency(spent - limit) if over else ''}</div>
                </div>""",
                unsafe_allow_html=True
            )
            st.progress(pct)

        with col_b:
            st.write("")
            if st.button("Remove", key=f"remove_budget_{category}"):
                delete_budget(user_id, category)
                st.session_state.budget_deleted = True
                st.rerun()

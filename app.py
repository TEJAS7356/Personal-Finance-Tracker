import streamlit as st
from datetime import date
import pandas as pd

from database import create_database, add_transaction, get_transactions
from utils import (
    inject_css, page_header, section_divider, format_currency,
    INCOME_CATEGORIES, EXPENSE_CATEGORIES
)

create_database()

st.set_page_config(page_title="Personal Finance Tracker", page_icon="💰", layout="wide")
inject_css()

page_header(
    "Personal Finance Tracker",
    "Track your income, expenses, and spending habits."
)

st.info(
    "Use the sidebar to navigate: **Transaction Management**, **Financial Dashboard**, "
    "**Budget Tracking**, **Monthly Analytics**, **Savings Goals**, and the **AI Financial Advisor**."
)


# ==================================================
# SESSION STATE
# ==================================================

if "show_success" not in st.session_state:
    st.session_state.show_success = False

if st.session_state.show_success:
    st.success("Transaction added successfully.")
    st.session_state.show_success = False


# ==================================================
# QUICK ADD
# ==================================================

st.header("Quick Add Transaction")

transaction_type = st.selectbox("Transaction Type", ["Income", "Expense"])
category_options = INCOME_CATEGORIES if transaction_type == "Income" else EXPENSE_CATEGORIES

with st.form("quick_add_form", clear_on_submit=True):

    col1, col2 = st.columns(2)

    with col1:
        transaction_date = st.date_input("Date", date.today())
        category = st.selectbox("Category", category_options)

    with col2:
        amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
        description = st.text_input("Description", placeholder="Example: Monthly salary")

    submitted = st.form_submit_button("Add Transaction", type="primary")

    if submitted:
        if amount <= 0:
            st.error("Please enter an amount greater than ₹0.")
        else:
            add_transaction(str(transaction_date), transaction_type, category, amount, description)
            st.session_state.show_success = True
            st.rerun()


# ==================================================
# AT-A-GLANCE SUMMARY
# ==================================================

transactions = get_transactions()

if transactions:

    df = pd.DataFrame(
        transactions,
        columns=["ID", "Date", "Type", "Category", "Amount", "Description"]
    )

    total_income = df[df["Type"] == "Income"]["Amount"].sum()
    total_expenses = df[df["Type"] == "Expense"]["Amount"].sum()
    balance = total_income - total_expenses

    section_divider()
    st.header("At a Glance")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Income", format_currency(total_income))
    with col2:
        st.metric("Total Expenses", format_currency(total_expenses))
    with col3:
        st.metric("Current Balance", format_currency(balance))

    st.caption(f"{len(df)} transaction(s) recorded. See the sidebar pages for full detail.")

else:
    section_divider()
    st.info("No transactions yet. Add your first one above to get started.")
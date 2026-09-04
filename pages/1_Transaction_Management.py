import streamlit as st
from datetime import date
import pandas as pd
import json
import sqlite3

from auth import require_login
from database import create_database, get_transactions, delete_transaction, add_transaction, get_budgets, get_savings_goals, set_budget, add_savings_goal, update_savings_goal_amount
from utils import inject_css, page_header, section_divider, INCOME_CATEGORIES, EXPENSE_CATEGORIES
from finance_ml import suggest_expense_category
from finance_tools import parse_statement, export_transactions
from database import get_user_profile

st.set_page_config(page_title="Transaction Management", page_icon="💵", layout="wide")
inject_css()

create_database()
user_id, username = require_login()

page_header("Transaction Management", "Add, search, filter, and manage every transaction.")

with st.expander("Import bank statement (CSV / Excel)"):
    st.caption("Accepted columns: Date, Amount, and optionally Type, Category, Description/Merchant.")
    uploaded = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx", "xls"], key="statement_upload")
    if uploaded is not None:
        try:
            imported = parse_statement(uploaded)
            st.dataframe(imported.head(20), use_container_width=True, hide_index=True)
            if st.button("Import these transactions", type="primary"):
                for row in imported.itertuples(index=False):
                    add_transaction(user_id, row.Date, row.Type, row.Category, float(row.Amount), row.Description)
                st.success(f"Imported {len(imported)} transaction(s) into your account.")
                st.rerun()
        except ValueError as exc:
            st.error(str(exc))

with st.expander("Personal data backup and restore"):
    profile = get_user_profile(user_id)
    backup = {"version": 1, "profile": {"username": profile["username"], "email": profile["email"], "currency": profile["currency"]}, "transactions": export_transactions(get_transactions(user_id)).to_dict("records"), "budgets": [{"category": c, "monthly_limit": l} for c, l in get_budgets(user_id)], "savings_goals": [{"name": n, "target_amount": t, "current_amount": c, "target_date": d} for _, n, t, c, d in get_savings_goals(user_id)]}
    st.download_button("Download my transaction backup", json.dumps(backup, default=str, indent=2), f"finance_backup_{date.today().isoformat()}.json", "application/json")
    restore_file = st.file_uploader("Restore transactions from a backup", type=["json"], key="restore_backup")
    if restore_file is not None and st.button("Restore backup transactions"):
        try:
            payload = json.load(restore_file)
            rows = payload.get("transactions", [])
            for row in rows:
                add_transaction(user_id, row["Date"], row["Type"], row["Category"], float(row["Amount"]), row.get("Description", ""))
            for row in payload.get("budgets", []):
                set_budget(user_id, row["category"], float(row["monthly_limit"]))
            for row in payload.get("savings_goals", []):
                add_savings_goal(user_id, row["name"], float(row["target_amount"]), row.get("target_date"))
                created_goal = get_savings_goals(user_id)[0]
                update_savings_goal_amount(user_id, created_goal[0], float(row.get("current_amount", 0)))
            st.success(f"Restored {len(rows)} transaction(s), budgets, and savings goals to your account.")
            st.rerun()
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            st.error(f"Could not restore this backup: {exc}")

if "show_success" not in st.session_state:
    st.session_state.show_success = False
if "show_delete_success" not in st.session_state:
    st.session_state.show_delete_success = False

if st.session_state.show_success:
    st.success("Transaction added successfully.")
    st.session_state.show_success = False

if st.session_state.show_delete_success:
    st.success("Transaction deleted successfully.")
    st.session_state.show_delete_success = False


# ==================================================
# ADD TRANSACTION
# ==================================================

st.header("Add Transaction")

transaction_type = st.selectbox("Transaction Type", ["Income", "Expense"])
category_options = INCOME_CATEGORIES if transaction_type == "Income" else EXPENSE_CATEGORIES
suggested_category = st.session_state.get("suggested_expense_category")
if suggested_category in category_options:
    st.caption(f"Suggested category: **{suggested_category}** — you can still change it below.")

with st.form("add_transaction_form", clear_on_submit=True):

    col1, col2 = st.columns(2)

    with col1:
        transaction_date = st.date_input("Date", date.today())
        category = st.selectbox(
            "Category",
            category_options,
            index=category_options.index(suggested_category) if suggested_category in category_options else 0,
        )

    with col2:
        amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
        description = st.text_input("Description", placeholder="Example: Monthly salary")

    submit_col1, submit_col2 = st.columns(2)
    with submit_col1:
        submitted = st.form_submit_button("Add Transaction", type="primary")
    with submit_col2:
        suggest_clicked = st.form_submit_button("Suggest Category") if transaction_type == "Expense" else False

    if suggest_clicked:
        suggestion = suggest_expense_category(description)
        if suggestion:
            st.session_state["suggested_expense_category"] = suggestion["category"]
            st.rerun()
        else:
            st.warning("No confident category match was found. Please choose a category manually.")

    if submitted:
        if amount <= 0:
            st.error("Please enter an amount greater than ₹0.")
        else:
            add_transaction(user_id, str(transaction_date), transaction_type, category, amount, description)
            st.session_state.pop("suggested_expense_category", None)
            st.session_state.show_success = True
            st.rerun()


# ==================================================
# TRANSACTION HISTORY
# ==================================================

section_divider()
st.header("Transaction History")

transactions = get_transactions(user_id)

if not transactions:
    st.info("No transactions yet. Add your first transaction above.")
else:

    df = pd.DataFrame(
        transactions,
        columns=["ID", "Date", "Type", "Category", "Amount", "Description"]
    )
    df["Date"] = pd.to_datetime(df["Date"])

    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1.4])

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()

    with filter_col1:
        date_from = st.date_input("From", value=min_date, min_value=min_date, max_value=max_date, key="filter_date_from")
    with filter_col2:
        date_to = st.date_input("To", value=max_date, min_value=min_date, max_value=max_date, key="filter_date_to")
    with filter_col3:
        search_term = st.text_input("Search category or description", placeholder="e.g. Food, groceries...", key="filter_search")

    filtered_df = df.copy()

    if date_from > date_to:
        st.warning("'From' date is after 'To' date, so no results match.")
        filtered_df = filtered_df.iloc[0:0]
    else:
        filtered_df = filtered_df[
            (filtered_df["Date"].dt.date >= date_from) & (filtered_df["Date"].dt.date <= date_to)
        ]

    if search_term.strip():
        term = search_term.strip().lower()
        filtered_df = filtered_df[
            filtered_df["Category"].str.lower().str.contains(term, na=False)
            | filtered_df["Description"].fillna("").str.lower().str.contains(term, na=False)
        ]

    st.caption(f"Showing {len(filtered_df)} of {len(df)} transaction(s).")

    export_df = filtered_df.copy()
    export_df["Date"] = export_df["Date"].dt.strftime("%Y-%m-%d")
    st.download_button(
        label="Download as CSV",
        data=export_df.to_csv(index=False).encode("utf-8"),
        file_name=f"transactions_{date.today().isoformat()}.csv",
        mime="text/csv"
    )

    if filtered_df.empty:
        st.info("No transactions match your filters.")
    else:
        header_cols = st.columns([0.6, 1, 1, 1.3, 1.3, 2.3, 0.7])
        for col, label in zip(header_cols, ["ID", "Date", "Type", "Category", "Amount", "Description", ""]):
            col.markdown(f"**{label}**")

        for _, row in filtered_df.iterrows():
            row_cols = st.columns([0.6, 1, 1, 1.3, 1.3, 2.3, 0.7])
            amount_color = "#34D399" if row["Type"] == "Income" else "#F87171"

            row_cols[0].write(int(row["ID"]))
            row_cols[1].write(row["Date"].strftime("%d %b %Y"))
            row_cols[2].markdown(f'<span style="color:{amount_color}; font-weight:600;">{row["Type"]}</span>', unsafe_allow_html=True)
            row_cols[3].write(row["Category"])
            row_cols[4].markdown(f'<span style="color:{amount_color}; font-weight:600;">₹{row["Amount"]:,.2f}</span>', unsafe_allow_html=True)
            row_cols[5].write(row["Description"] if row["Description"] else "—")

            if row_cols[6].button("🗑️", key=f"delete_{row['ID']}", help="Delete this transaction"):
                delete_transaction(user_id, int(row["ID"]))
                st.session_state.show_delete_success = True
                st.rerun()

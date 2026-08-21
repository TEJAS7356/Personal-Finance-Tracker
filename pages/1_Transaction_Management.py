import streamlit as st
from datetime import date
import pandas as pd

from database import create_database, get_transactions, delete_transaction, add_transaction
from utils import inject_css, page_header, section_divider, INCOME_CATEGORIES, EXPENSE_CATEGORIES

create_database()

st.set_page_config(page_title="Transaction Management", page_icon="💵", layout="wide")
inject_css()

page_header("Transaction Management", "Add, search, filter, and manage every transaction.")

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

with st.form("add_transaction_form", clear_on_submit=True):

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
# TRANSACTION HISTORY
# ==================================================

section_divider()
st.header("Transaction History")

transactions = get_transactions()

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
                delete_transaction(int(row["ID"]))
                st.session_state.show_delete_success = True
                st.rerun()
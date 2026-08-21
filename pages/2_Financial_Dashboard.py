import streamlit as st
import pandas as pd
import plotly.express as px
import html

from database import create_database, get_transactions
from utils import inject_css, page_header, section_divider, format_currency, FINANCE_COLOR_SEQUENCE

create_database()

st.set_page_config(page_title="Financial Dashboard", page_icon="📊", layout="wide")
inject_css()

page_header("Financial Dashboard", "Your income, spending, and insights at a glance.")

transactions = get_transactions()

if not transactions:
    st.info("No transactions yet. Add some on the Transaction Management page first.")
    st.stop()

df = pd.DataFrame(transactions, columns=["ID", "Date", "Type", "Category", "Amount", "Description"])
df["Date"] = pd.to_datetime(df["Date"])

total_income = df[df["Type"] == "Income"]["Amount"].sum()
total_expenses = df[df["Type"] == "Expense"]["Amount"].sum()
balance = total_income - total_expenses
expense_df = df[df["Type"] == "Expense"]


# ==================================================
# SUMMARY
# ==================================================

st.header("Financial Summary")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Income", format_currency(total_income))
with col2:
    st.metric("Total Expenses", format_currency(total_expenses))
with col3:
    st.metric("Current Balance", format_currency(balance))


# ==================================================
# SPENDING ANALYSIS
# ==================================================

section_divider()
st.header("Spending Analysis")

if expense_df.empty:
    st.info("Add an expense transaction to view spending analysis.")
else:
    col1, col2 = st.columns(2)

    category_expenses = (
        expense_df.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount", ascending=False)
    )

    with col1:
        fig_category = px.pie(
            category_expenses, names="Category", values="Amount",
            title="Expense Distribution", color_discrete_sequence=FINANCE_COLOR_SEQUENCE, hole=0.55
        )
        fig_category.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E5E7EB", family="Arial"),
            title_font=dict(size=18, color="#FFFFFF"),
            legend=dict(font=dict(color="#D1D5DB")),
            margin=dict(l=20, r=20, t=60, b=20)
        )
        fig_category.update_traces(
            textposition="inside", textinfo="percent",
            textfont=dict(color="white", size=13),
            marker=dict(line=dict(color="#18181B", width=2))
        )
        st.plotly_chart(fig_category, use_container_width=True)

    with col2:
        fig_bar = px.bar(
            category_expenses, x="Category", y="Amount", color="Category",
            title="Spending by Category", color_discrete_sequence=FINANCE_COLOR_SEQUENCE
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E5E7EB", family="Arial"),
            title_font=dict(size=18, color="#FFFFFF"),
            xaxis=dict(title="Category", showgrid=False),
            yaxis=dict(title="Amount (₹)", gridcolor="#2D2D33"),
            showlegend=False, margin=dict(l=20, r=20, t=60, b=20)
        )
        fig_bar.update_traces(marker_line_width=0)
        st.plotly_chart(fig_bar, use_container_width=True)


# ==================================================
# SMART FINANCIAL INSIGHTS
# ==================================================

section_divider()
st.header("Smart Financial Insights")

if total_income > 0:

    expense_percentage = (total_expenses / total_income) * 100

    if not expense_df.empty:
        category_sums = expense_df.groupby("Category")["Amount"].sum()
        highest_category = category_sums.idxmax()
        highest_amount = category_sums.max()
    else:
        highest_category = "No expenses"
        highest_amount = 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""<div class="insight-card">
                <div class="insight-label">Spending Rate</div>
                <div class="insight-value">{expense_percentage:.1f}%</div>
                <div class="insight-description">of your total income</div>
            </div>""",
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""<div class="insight-card">
                <div class="insight-label">Top Spending Category</div>
                <div class="insight-value">{html.escape(str(highest_category))}</div>
                <div class="insight-description">₹{highest_amount:,.2f} spent</div>
            </div>""",
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""<div class="insight-card">
                <div class="insight-label">Available Balance</div>
                <div class="insight-value">₹{balance:,.2f}</div>
                <div class="insight-description">remaining balance</div>
            </div>""",
            unsafe_allow_html=True
        )

    st.markdown("### Recommendation")

    if expense_percentage < 30:
        recommendation = (
            "Your current spending is relatively low compared with your income. "
            "Continue maintaining your savings and avoid unnecessary expenses."
        )
    elif expense_percentage < 60:
        recommendation = (
            "Your spending is moderate. Review your highest spending categories "
            "and consider setting monthly limits for non-essential expenses."
        )
    else:
        recommendation = (
            "Your expenses are taking a significant portion of your income. "
            "Consider reducing non-essential spending and increasing your savings."
        )

    st.markdown(
        f"""<div class="recommendation">
            <div class="recommendation-title">Financial Recommendation</div>
            <div class="recommendation-text">{recommendation}</div>
        </div>""",
        unsafe_allow_html=True
    )

else:
    st.info("Add income and expense transactions to generate insights.")
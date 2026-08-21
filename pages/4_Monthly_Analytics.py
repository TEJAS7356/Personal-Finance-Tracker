import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from database import create_database, get_transactions
from utils import inject_css, page_header, section_divider, format_currency

create_database()

st.set_page_config(page_title="Monthly Analytics", page_icon="📈", layout="wide")
inject_css()

page_header("Monthly Analytics", "See how your income and spending trend month to month.")

transactions = get_transactions()

if not transactions:
    st.info("No transactions yet. Add some on the Transaction Management page first.")
    st.stop()

df = pd.DataFrame(transactions, columns=["ID", "Date", "Type", "Category", "Amount", "Description"])
df["Date"] = pd.to_datetime(df["Date"])
df["Month"] = df["Date"].dt.to_period("M").astype(str)

monthly = (
    df.groupby(["Month", "Type"])["Amount"].sum().unstack(fill_value=0).reset_index()
)
for col in ["Income", "Expense"]:
    if col not in monthly.columns:
        monthly[col] = 0.0
monthly = monthly.sort_values("Month")
monthly["Net"] = monthly["Income"] - monthly["Expense"]


# ==================================================
# TREND CHART
# ==================================================

st.header("Income vs. Expenses by Month")

fig = go.Figure()
fig.add_trace(go.Scatter(x=monthly["Month"], y=monthly["Income"], name="Income", mode="lines+markers", line=dict(color="#34D399", width=3)))
fig.add_trace(go.Scatter(x=monthly["Month"], y=monthly["Expense"], name="Expense", mode="lines+markers", line=dict(color="#F87171", width=3)))

fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#E5E7EB", family="Arial"),
    xaxis=dict(title="Month", showgrid=False),
    yaxis=dict(title="Amount (₹)", gridcolor="#2D2D33"),
    legend=dict(font=dict(color="#D1D5DB")),
    margin=dict(l=20, r=20, t=30, b=20)
)

st.plotly_chart(fig, use_container_width=True)


# ==================================================
# MONTH-OVER-MONTH COMPARISON
# ==================================================

section_divider()
st.header("Month-over-Month Comparison")

if len(monthly) < 2:
    st.info("Add transactions across at least two months to see a comparison.")
else:
    current = monthly.iloc[-1]
    previous = monthly.iloc[-2]

    def pct_change(curr, prev):
        if prev == 0:
            return None
        return ((curr - prev) / prev) * 100

    income_change = pct_change(current["Income"], previous["Income"])
    expense_change = pct_change(current["Expense"], previous["Expense"])

    col1, col2, col3 = st.columns(3)

    with col1:
        delta = f"{income_change:+.1f}%" if income_change is not None else None
        st.metric(f"Income — {current['Month']}", format_currency(current["Income"]), delta=delta)

    with col2:
        delta = f"{expense_change:+.1f}%" if expense_change is not None else None
        st.metric(f"Expenses — {current['Month']}", format_currency(current["Expense"]), delta=delta, delta_color="inverse")

    with col3:
        st.metric(f"Net — {current['Month']}", format_currency(current["Net"]))

    if expense_change is not None:
        if expense_change > 0:
            st.markdown(
                f"""<div class="recommendation">
                    <div class="recommendation-title">Comparison Note</div>
                    <div class="recommendation-text">You spent {expense_change:.1f}% more in {current['Month']} than in {previous['Month']}.</div>
                </div>""",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""<div class="recommendation">
                    <div class="recommendation-title">Comparison Note</div>
                    <div class="recommendation-text">You spent {abs(expense_change):.1f}% less in {current['Month']} than in {previous['Month']}. Nice work.</div>
                </div>""",
                unsafe_allow_html=True
            )


# ==================================================
# MONTHLY BREAKDOWN TABLE
# ==================================================

section_divider()
st.header("Monthly Breakdown")

display_monthly = monthly.copy()
display_monthly["Income"] = display_monthly["Income"].apply(format_currency)
display_monthly["Expense"] = display_monthly["Expense"].apply(format_currency)
display_monthly["Net"] = display_monthly["Net"].apply(format_currency)

st.dataframe(
    display_monthly.rename(columns={"Month": "Month"}),
    use_container_width=True,
    hide_index=True
)
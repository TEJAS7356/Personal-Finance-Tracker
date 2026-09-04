import streamlit as st
import pandas as pd
import plotly.express as px
import html

from auth import require_login
from database import create_database, get_transactions
from utils import inject_css, page_header, section_divider, format_currency, FINANCE_COLOR_SEQUENCE, theme_chart_colors
from database import get_budgets, get_savings_goals
from finance_ml import detect_expense_anomalies, financial_health_score, predict_next_month_expenses, simulate_finances

st.set_page_config(page_title="Financial Dashboard", page_icon="📊", layout="wide")
inject_css()

create_database()
user_id, username = require_login()

page_header("Financial Dashboard", "Your income, spending, and insights at a glance.")

transactions = get_transactions(user_id)

if not transactions:
    st.info("No transactions yet. Add some on the Transaction Management page first.")
    st.stop()

df = pd.DataFrame(transactions, columns=["ID", "Date", "Type", "Category", "Amount", "Description"])
df["Date"] = pd.to_datetime(df["Date"])
chart_colors = theme_chart_colors()

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
            font=dict(color=chart_colors["font"], family="Arial"),
            title_font=dict(size=18, color=chart_colors["title"]),
            legend=dict(font=dict(color=chart_colors["legend"])),
            margin=dict(l=20, r=20, t=60, b=20)
        )
        fig_category.update_traces(
            textposition="inside", textinfo="percent",
            textfont=dict(color="white", size=13),
            marker=dict(line=dict(color=chart_colors["marker_line"], width=2))
        )
        st.plotly_chart(fig_category, use_container_width=True)

    with col2:
        fig_bar = px.bar(
            category_expenses, x="Category", y="Amount", color="Category",
            title="Spending by Category", color_discrete_sequence=FINANCE_COLOR_SEQUENCE
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=chart_colors["font"], family="Arial"),
            title_font=dict(size=18, color=chart_colors["title"]),
            xaxis=dict(title="Category", showgrid=False),
            yaxis=dict(title="Amount (₹)", gridcolor=chart_colors["grid"], color=chart_colors["axis"]),
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


# ==================================================
# AI / ML FINANCIAL TOOLS
# ==================================================

section_divider()
st.header("AI & ML Financial Tools")
st.caption("These explainable calculations use only your currently logged-in account's data.")

budgets = get_budgets(user_id)
goals = get_savings_goals(user_id)

prediction = predict_next_month_expenses(transactions)
health = financial_health_score(transactions, budgets, goals)
anomalies = detect_expense_anomalies(transactions)

tool_col1, tool_col2 = st.columns(2)
with tool_col1:
    st.subheader("Next-Month Expense Prediction")
    if prediction["status"] == "ok":
        st.metric(f"Predicted expenses — {prediction['month']}", format_currency(prediction["amount"]))
        st.caption(prediction["explanation"])
        if prediction.get("mae") is not None:
            st.caption(f"Simple holdout error on the latest month: approximately {format_currency(prediction['mae'])}.")
        if prediction.get("category_predictions"):
            with st.expander("Category-wise estimate"):
                for category, amount in prediction["category_predictions"].items():
                    st.write(f"**{category}:** {format_currency(amount)}")
    else:
        st.info(prediction["message"])

with tool_col2:
    st.subheader("Financial Health Score")
    if health.get("score") is None:
        st.info(health["message"])
    else:
        st.metric("Overall score", f"{health['score']}/100")
        with st.expander("Score breakdown and suggestions", expanded=True):
            for factor, points in health["factors"].items():
                st.write(f"**{factor}:** {points} points")
            st.caption(health["explanation"])
            for suggestion in health["suggestions"]:
                st.write(f"• {suggestion}")

st.subheader("Unusual Spending")
if anomalies["status"] != "ok":
    st.info(anomalies["message"])
elif anomalies["anomalies"]:
    st.warning(f"{len(anomalies['anomalies'])} transaction(s) look unusual.")
    st.caption(anomalies["explanation"])
    st.dataframe(pd.DataFrame(anomalies["anomalies"]), use_container_width=True, hide_index=True)
else:
    st.success("No unusually high category transactions were detected.")

st.subheader("What-If Financial Simulator")
sim_col1, sim_col2 = st.columns(2)
with sim_col1:
    extra_saving = st.number_input("Additional monthly saving (₹)", min_value=0.0, value=0.0, step=500.0, format="%.2f")
    expense_categories = sorted({row["Category"] for row in pd.DataFrame(transactions, columns=["ID", "Date", "Type", "Category", "Amount", "Description"]).to_dict("records") if row["Type"] == "Expense"})
    reduction_category = st.selectbox("Category to reduce", ["None"] + expense_categories)
with sim_col2:
    reduction_percent = st.slider("Reduction percentage", 0, 100, 0, 5)
    simulation = simulate_finances(
        transactions,
        goals,
        extra_monthly_saving=extra_saving,
        category_reduction=None if reduction_category == "None" else reduction_category,
        reduction_percent=reduction_percent,
    )
    st.metric("Current monthly surplus", format_currency(simulation["current_surplus"]))
    st.metric("Simulated monthly surplus", format_currency(simulation["simulated_surplus"]), delta=format_currency(simulation["difference"]))

if simulation["goal_estimates"]:
    with st.expander("Estimated time to reach savings goals"):
        for estimate in simulation["goal_estimates"]:
            if estimate["months"] is None:
                st.write(f"**{estimate['name']}:** cannot be estimated while simulated surplus is not positive.")
            else:
                st.write(f"**{estimate['name']}:** approximately {estimate['months']} month(s) for {format_currency(estimate['remaining'])} remaining.")
st.caption("Simulation uses your recorded income and expenses as the baseline; it is an estimate, not financial advice.")

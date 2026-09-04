import streamlit as st
import pandas as pd
import os

from auth import require_login
from database import create_database, get_transactions, get_budgets, get_savings_goals
from utils import inject_css, page_header, section_divider

st.set_page_config(page_title="AI Financial Advisor", page_icon="🤖", layout="wide")
inject_css()

create_database()
user_id, username = require_login()

page_header("AI Financial Advisor", "Ask questions about your finances and get personalized suggestions.")

st.markdown(
    """<div class="ai-disclaimer">
        This feature uses Google's Gemini API (free tier) to analyze summarized numbers from your own
        data. It is not a licensed financial advisor and its suggestions should not be treated as
        professional financial advice — always use your own judgment for major financial decisions.
        On Gemini's free tier, prompts may be used by Google to improve their models — only summarized
        totals are sent, never your raw transaction list.
    </div>""",
    unsafe_allow_html=True
)


# ==================================================
# API KEY CHECK
# ==================================================

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key and hasattr(st, "secrets"):
    api_key = st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    st.warning(
        "No Gemini API key found. Set the `GEMINI_API_KEY` environment variable "
        "(or add it to `.streamlit/secrets.toml` as `GEMINI_API_KEY = \"...\"`) to enable this page.\n\n"
        "Get a free key (no credit card required) at https://aistudio.google.com/app/apikey"
    )
    st.stop()

try:
    from google import genai
except ImportError:
    st.error(
        "The `google-genai` package isn't installed. Run `pip install google-genai` "
        "(it's included in requirements.txt)."
    )
    st.stop()


# ==================================================
# BUILD A SUMMARY OF THE USER'S DATA
# ==================================================

transactions = get_transactions(user_id)

if not transactions:
    st.info("Add some transactions first so the advisor has data to work with.")
    st.stop()

df = pd.DataFrame(transactions, columns=["ID", "Date", "Type", "Category", "Amount", "Description"])
df["Date"] = pd.to_datetime(df["Date"])

total_income = df[df["Type"] == "Income"]["Amount"].sum()
total_expenses = df[df["Type"] == "Expense"]["Amount"].sum()
balance = total_income - total_expenses

expense_by_category = (
    df[df["Type"] == "Expense"].groupby("Category")["Amount"].sum().sort_values(ascending=False)
)

budgets = get_budgets(user_id)
goals = get_savings_goals(user_id)

summary_lines = [
    f"Total income: Rs. {total_income:,.2f}",
    f"Total expenses: Rs. {total_expenses:,.2f}",
    f"Current balance: Rs. {balance:,.2f}",
    "Spending by category:",
]
for category, amount in expense_by_category.items():
    summary_lines.append(f"  - {category}: Rs. {amount:,.2f}")

if budgets:
    summary_lines.append("Budgets set (monthly limits):")
    for category, limit in budgets:
        spent = expense_by_category.get(category, 0.0)
        summary_lines.append(f"  - {category}: Rs. {spent:,.2f} spent of Rs. {limit:,.2f} limit")

if goals:
    summary_lines.append("Savings goals:")
    for _, name, target, current, target_date in goals:
        summary_lines.append(f"  - {name}: Rs. {current:,.2f} saved of Rs. {target:,.2f} target (by {target_date or 'no date set'})")

data_summary = "\n".join(summary_lines)

with st.expander("Data being sent to the advisor"):
    st.text(data_summary)


# ==================================================
# CHAT
# ==================================================

section_divider()
st.header("Ask the Advisor")

if f"advisor_messages_{user_id}" not in st.session_state:
    st.session_state[f"advisor_messages_{user_id}"] = []

for msg in st.session_state[f"advisor_messages_{user_id}"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

suggested = st.columns(3)
suggestion_texts = [
    "Where can I realistically cut back?",
    "Am I saving enough given my income?",
    "How should I prioritize my budgets?",
]
clicked_suggestion = None
for col, text in zip(suggested, suggestion_texts):
    if col.button(text, key=f"suggestion_{text}"):
        clicked_suggestion = text

user_input = st.chat_input("Ask about your spending, budgets, or savings goals...")
prompt = clicked_suggestion or user_input

if prompt:

    st.session_state[f"advisor_messages_{user_id}"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    system_prompt = (
        "You are a cautious, practical personal finance assistant embedded in a budgeting app. "
        "You will be given a summary of the user's real transaction data (in Indian Rupees) and a "
        "question. Give specific, actionable suggestions grounded in the numbers provided. "
        "Do not invent numbers that weren't given to you. Keep responses concise (under 200 words) "
        "and avoid being preachy. You are not a licensed financial advisor, so avoid absolute "
        "recommendations on investments, taxes, or legal matters — for those, suggest a qualified "
        "professional."
    )

    full_prompt = (
        f"{system_prompt}\n\n"
        f"Here is a summary of the user's financial data:\n\n{data_summary}\n\n"
        f"User question: {prompt}"
    )

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=full_prompt,
            )
            reply_text = response.text
        except Exception as e:
            reply_text = f"Sorry, I couldn't reach the AI advisor right now ({e})."

        placeholder.markdown(reply_text)

    st.session_state[f"advisor_messages_{user_id}"].append({"role": "assistant", "content": reply_text})

if st.session_state[f"advisor_messages_{user_id}"]:
    if st.button("Clear conversation"):
        st.session_state[f"advisor_messages_{user_id}"] = []
        st.rerun()
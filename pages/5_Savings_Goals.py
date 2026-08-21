import streamlit as st
from datetime import date

from database import (
    create_database, add_savings_goal, get_savings_goals,
    update_savings_goal_amount, delete_savings_goal
)
from utils import inject_css, page_header, section_divider, format_currency

create_database()

st.set_page_config(page_title="Savings Goals", page_icon="🏦", layout="wide")
inject_css()

page_header("Savings Goals", "Set a target and track your progress toward it.")

if "goal_added" not in st.session_state:
    st.session_state.goal_added = False
if "goal_updated" not in st.session_state:
    st.session_state.goal_updated = False
if "goal_deleted" not in st.session_state:
    st.session_state.goal_deleted = False

if st.session_state.goal_added:
    st.success("Savings goal created.")
    st.session_state.goal_added = False
if st.session_state.goal_updated:
    st.success("Progress updated.")
    st.session_state.goal_updated = False
if st.session_state.goal_deleted:
    st.success("Goal removed.")
    st.session_state.goal_deleted = False


# ==================================================
# CREATE A GOAL
# ==================================================

st.header("Create a Goal")

with st.form("add_goal_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        goal_name = st.text_input("Goal Name", placeholder="e.g. Emergency Fund")
    with col2:
        goal_target = st.number_input("Target Amount (₹)", min_value=0.0, step=1000.0, format="%.2f")
    with col3:
        goal_date = st.date_input("Target Date", value=date.today())

    submitted = st.form_submit_button("Create Goal", type="primary")

    if submitted:
        if not goal_name.strip():
            st.error("Please enter a name for your goal.")
        elif goal_target <= 0:
            st.error("Please enter a target amount greater than ₹0.")
        else:
            add_savings_goal(goal_name.strip(), goal_target, str(goal_date))
            st.session_state.goal_added = True
            st.rerun()


# ==================================================
# TRACK PROGRESS
# ==================================================

section_divider()
st.header("Your Goals")

goals = get_savings_goals()

if not goals:
    st.info("No savings goals yet. Create one above.")
else:
    for goal_id, name, target, current, target_date in goals:

        pct = min(current / target, 1.0) if target > 0 else 0.0
        remaining = max(target - current, 0.0)

        st.markdown(
            f"""<div class="card">
                <div class="card-title">{name}</div>
                <div class="card-sub">{format_currency(current)} saved of {format_currency(target)}
                &nbsp;•&nbsp; target date: {target_date or 'not set'}
                &nbsp;•&nbsp; {format_currency(remaining)} remaining</div>
            </div>""",
            unsafe_allow_html=True
        )
        st.progress(pct, text=f"{pct * 100:.0f}% complete")

        col_a, col_b, col_c = st.columns([2, 1, 1])

        with col_a:
            new_amount = st.number_input(
                "Update saved amount (₹)",
                min_value=0.0,
                value=float(current),
                step=500.0,
                format="%.2f",
                key=f"goal_amount_{goal_id}"
            )

        with col_b:
            st.write("")
            st.write("")
            if st.button("Update", key=f"update_goal_{goal_id}"):
                update_savings_goal_amount(goal_id, new_amount)
                st.session_state.goal_updated = True
                st.rerun()

        with col_c:
            st.write("")
            st.write("")
            if st.button("Delete Goal", key=f"delete_goal_{goal_id}"):
                delete_savings_goal(goal_id)
                st.session_state.goal_deleted = True
                st.rerun()

        section_divider()
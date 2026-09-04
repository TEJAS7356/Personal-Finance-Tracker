import streamlit as st

from auth import require_login
from database import create_database, delete_user_account, get_user_profile, update_user_profile
from utils import inject_css, page_header

st.set_page_config(page_title="Profile Settings", page_icon="⚙️", layout="wide")
inject_css()
create_database()
user_id, username = require_login()
profile = get_user_profile(user_id)
page_header("Profile & Account Settings", "Manage your account details and personal preferences.")

with st.form("profile_settings_form"):
    new_username = st.text_input("Username", value=profile["username"])
    new_email = st.text_input("Email address", value=profile["email"] or "")
    currency = st.selectbox("Currency symbol", ["₹", "$", "€", "£"], index=["₹", "$", "€", "£"].index(profile["currency"] if profile["currency"] in ["₹", "$", "€", "£"] else "₹"))
    if st.form_submit_button("Save profile", type="primary"):
        try:
            update_user_profile(user_id, new_username, new_email, currency)
            st.session_state["username"] = new_username.strip()
            st.success("Profile updated successfully.")
        except ValueError as exc:
            st.error(str(exc))

st.subheader("Account information")
st.caption(f"Account created: {profile['created_at']}")
st.warning("Deleting your account permanently deletes your transactions, budgets, savings goals, and profile.")
confirm = st.checkbox("I understand this action cannot be undone.")
if st.button("Delete my account", type="secondary", disabled=not confirm):
    delete_user_account(user_id)
    for key in ("user_id", "username"):
        st.session_state.pop(key, None)
    st.success("Your account and financial data were deleted.")
    st.rerun()

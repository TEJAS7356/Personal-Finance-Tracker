import hashlib
import hmac
import os
import secrets
import smtplib
import time
from email.message import EmailMessage

import streamlit as st

from database import create_user, get_user_by_email, reset_user_password, verify_user
from utils import theme_toggle

OTP_TTL_SECONDS = 5 * 60
OTP_RESEND_COOLDOWN_SECONDS = 60
MAX_OTP_ATTEMPTS = 5


def require_login():
    """Require an authenticated browser session before rendering private data."""
    if st.session_state.get("user_id") is not None:
        _render_account_sidebar()
        return st.session_state["user_id"], st.session_state["username"]

    _render_login_register()
    st.stop()


def _get_secret(name, default=None):
    value = os.environ.get(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _smtp_settings():
    username = _get_secret("SMTP_USERNAME")
    app_password = _get_secret("SMTP_APP_PASSWORD")
    if not username or not app_password:
        return None
    return {
        "host": _get_secret("SMTP_HOST", "smtp.gmail.com"),
        "port": int(_get_secret("SMTP_PORT", "587")),
        "username": username,
        "app_password": app_password,
        "from_email": _get_secret("SMTP_FROM_EMAIL", username),
    }


def _otp_hash(otp):
    return hashlib.sha256(otp.encode("ascii")).hexdigest()


def _send_otp_email(recipient, otp):
    """Send an OTP via Gmail SMTP; the OTP is never rendered or logged."""
    settings = _smtp_settings()
    if settings is None:
        return False

    message = EmailMessage()
    message["Subject"] = "Personal Finance Tracker password reset"
    message["From"] = settings["from_email"]
    message["To"] = recipient
    message.set_content(
        "Your Personal Finance Tracker password reset code is: "
        f"{otp}\n\nThis code expires in 5 minutes. If you did not request a reset, "
        "you can safely ignore this email."
    )

    try:
        with smtplib.SMTP(settings["host"], settings["port"], timeout=20) as server:
            server.starttls()
            server.login(settings["username"], settings["app_password"])
            server.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        # Never expose SMTP details or the OTP through the UI.
        return False


def _clear_reset_state():
    for key in (
        "reset_user_id", "reset_otp_hash", "reset_otp_expires_at",
        "reset_otp_attempts", "reset_otp_last_sent", "reset_otp_verified",
    ):
        st.session_state.pop(key, None)


def _begin_reset(email):
    """Start a reset without revealing whether the email is registered."""
    now = time.time()
    existing = st.session_state.get("reset_otp_last_sent", 0)
    if now - existing < OTP_RESEND_COOLDOWN_SECONDS:
        return False, "Please wait before requesting another code."

    user = get_user_by_email(email)
    # Generate/send only for a real account, but return the same public message
    # for both existing and unknown addresses to prevent account enumeration.
    if user is not None:
        otp = f"{secrets.randbelow(1_000_000):06d}"
        if not _send_otp_email(user["email"], otp):
            return False, "Password recovery is temporarily unavailable. Please try again later."
        st.session_state["reset_user_id"] = user["id"]
        st.session_state["reset_otp_hash"] = _otp_hash(otp)
        st.session_state["reset_otp_expires_at"] = now + OTP_TTL_SECONDS
        st.session_state["reset_otp_attempts"] = 0
        st.session_state["reset_otp_verified"] = False

    # Keep the timestamp for both branches so repeated probing is rate-limited.
    st.session_state["reset_otp_last_sent"] = now
    return True, "If an account matches that email, a verification code has been sent."


def _verify_otp(otp):
    if st.session_state.get("reset_otp_verified"):
        return True, ""
    if time.time() > st.session_state.get("reset_otp_expires_at", 0):
        return False, "This code has expired. Please request a new one."
    if st.session_state.get("reset_otp_attempts", 0) >= MAX_OTP_ATTEMPTS:
        return False, "Too many incorrect attempts. Please request a new code."

    st.session_state["reset_otp_attempts"] += 1
    if hmac.compare_digest(_otp_hash(otp.strip()), st.session_state.get("reset_otp_hash", "")):
        st.session_state["reset_otp_verified"] = True
        return True, ""
    remaining = MAX_OTP_ATTEMPTS - st.session_state["reset_otp_attempts"]
    return False, f"That code is incorrect. {remaining} attempt(s) remaining."


def _render_account_sidebar():
    with st.sidebar:
        theme_toggle()
        st.markdown("---")
        st.markdown(f"👤 Logged in as **{st.session_state['username']}**")
        if st.button("Log out", use_container_width=True, key="logout_button"):
            for key in ("user_id", "username"):
                st.session_state.pop(key, None)
            for key in list(st.session_state):
                if key.startswith("advisor_messages_"):
                    st.session_state.pop(key, None)
            st.rerun()


def _render_login_register():
    with st.sidebar:
        theme_toggle()

    st.markdown(
        '<div class="main-title">Personal Finance Tracker</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitle">Log in or create an account to see your own financial data.</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.pop("password_reset_complete", False):
        st.success("Password reset successfully. You can now log in with your new password.")

    if st.session_state.get("auth_view") == "forgot":
        _render_forgot_password()
        return

    login_tab, register_tab = st.tabs(["Log In", "Register"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log In", type="primary")
            if submitted:
                if not username or not password:
                    st.error("Please enter both a username and password.")
                else:
                    user = verify_user(username, password)
                    if user is None:
                        st.error("Incorrect username or password.")
                    else:
                        st.session_state["user_id"] = user["id"]
                        st.session_state["username"] = user["username"]
                        st.rerun()
        if st.button("Forgot Password?", key="forgot_password_button"):
            st.session_state["auth_view"] = "forgot"
            st.rerun()

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("Choose a username", key="register_username")
            new_email = st.text_input("Email address", key="register_email")
            new_password = st.text_input("Choose a password", type="password", key="register_password")
            confirm_password = st.text_input("Confirm password", type="password", key="register_confirm")
            submitted = st.form_submit_button("Create Account", type="primary")
            if submitted:
                if not new_username or not new_email or not new_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords don't match.")
                else:
                    try:
                        user_id = create_user(new_username, new_password, new_email)
                        st.session_state["user_id"] = user_id
                        st.session_state["username"] = new_username.strip()
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))


def _render_forgot_password():
    st.subheader("Reset your password")
    st.caption("Enter the email address associated with your account.")

    if st.button("← Back to Log In", key="back_to_login_button"):
        _clear_reset_state()
        st.session_state["auth_view"] = "login"
        st.rerun()

    if st.session_state.get("reset_notice"):
        st.info(st.session_state.pop("reset_notice"))

    if not st.session_state.get("reset_otp_hash") and not st.session_state.get("reset_otp_verified"):
        with st.form("request_reset_form"):
            email = st.text_input("Registered email address", key="reset_email")
            submitted = st.form_submit_button("Send Verification Code", type="primary")
            if submitted:
                if not email.strip():
                    st.error("Please enter your email address.")
                else:
                    ok, message = _begin_reset(email)
                    if ok:
                        st.session_state["reset_notice"] = message
                        st.rerun()
                    else:
                        st.error(message)
        return

    if not st.session_state.get("reset_otp_verified"):
        with st.form("verify_reset_otp_form"):
            otp = st.text_input("6-digit verification code", max_chars=6, key="reset_otp_input")
            submitted = st.form_submit_button("Verify Code", type="primary")
            if submitted:
                if len(otp.strip()) != 6 or not otp.strip().isdigit():
                    st.error("Enter the 6-digit verification code from your email.")
                else:
                    verified, message = _verify_otp(otp)
                    if verified:
                        st.rerun()
                    else:
                        st.error(message)

        last_sent = st.session_state.get("reset_otp_last_sent", 0)
        seconds_left = max(0, OTP_RESEND_COOLDOWN_SECONDS - int(time.time() - last_sent))
        if seconds_left:
            st.caption(f"You can request another code in {seconds_left} second(s).")
        elif st.button("Resend Verification Code", key="resend_reset_otp_button"):
            ok, message = _begin_reset(st.session_state.get("reset_email", ""))
            if ok:
                st.session_state["reset_notice"] = message
                st.rerun()
            else:
                st.error(message)
        return

    with st.form("new_password_form"):
        new_password = st.text_input("New Password", type="password", key="new_reset_password")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_reset_password")
        submitted = st.form_submit_button("Reset Password", type="primary")
        if submitted:
            if not new_password or not confirm_password:
                st.error("Please fill in both password fields.")
            elif new_password != confirm_password:
                st.error("Passwords don't match.")
            else:
                try:
                    reset_user_password(st.session_state["reset_user_id"], new_password)
                    _clear_reset_state()
                    st.session_state["auth_view"] = "login"
                    st.session_state["password_reset_complete"] = True
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

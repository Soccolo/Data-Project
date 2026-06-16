"""Email + password sign-in / sign-up screen."""

from __future__ import annotations

import streamlit as st

from dara import auth as auth_service
from . import session
from .common import WORDMARK


def render() -> None:
    st.markdown(f"##### {WORDMARK}")
    st.title("Welcome to *Dara*.")
    st.caption("AI matchmaker and mediator.")

    tab_in, tab_up, tab_reset = st.tabs(["Sign in", "Create account", "Forgot password"])

    with tab_in:
        _sign_in()
    with tab_up:
        _sign_up()
    with tab_reset:
        _reset()


def _sign_in() -> None:
    with st.form("sign_in"):
        email = st.text_input("Email", key="si_email")
        password = st.text_input("Password", type="password", key="si_pw")
        remember = st.checkbox("Remember me on this device", value=True, key="si_remember")
        submitted = st.form_submit_button("Sign in →", use_container_width=True)
    if submitted:
        if not email.strip() or not password:
            st.error("Enter your email and password.")
            return
        res = auth_service.sign_in(session.get_client(), email, password)
        if res.ok:
            session.login(res, remember=remember)
            st.rerun()
        else:
            st.error(res.error or "Could not sign in.")


def _sign_up() -> None:
    with st.form("sign_up"):
        email = st.text_input("Email", key="su_email")
        password = st.text_input("Password", type="password", key="su_pw",
                                 help="At least 6 characters.")
        confirm = st.text_input("Confirm password", type="password", key="su_pw2")
        submitted = st.form_submit_button("Create account →", use_container_width=True)
    if submitted:
        if not email.strip() or not password:
            st.error("Enter an email and password.")
            return
        if password != confirm:
            st.error("Passwords don't match.")
            return
        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return
        res = auth_service.sign_up(session.get_client(), email, password)
        if not res.ok:
            st.error(res.error or "Could not create account.")
            return
        if res.needs_confirmation:
            st.success(
                "Account created. Check your inbox to confirm your email, "
                "then come back and sign in."
            )
        else:
            session.login(res)
            st.rerun()


def _reset() -> None:
    with st.form("reset_pw"):
        email = st.text_input("Email", key="rp_email")
        submitted = st.form_submit_button("Email me a reset link →", use_container_width=True)
    if submitted:
        if not email.strip():
            st.error("Enter your email.")
            return
        res = auth_service.send_password_reset(session.get_client(), email)
        if res.ok:
            st.success("If that email has an account, a reset link is on its way.")
        else:
            st.error(res.error or "Could not send reset link.")

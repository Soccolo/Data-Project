"""First-run onboarding: pick a username, display name, and what you're here for."""

from __future__ import annotations

import streamlit as st

from dara import profile as profile_service
from . import session
from .common import WORDMARK

_KINDS = {
    "dating": "Dating — find someone new",
    "couples": "Couples — work through a conflict",
    "both": "Both",
}


def render() -> None:
    st.markdown(f"##### {WORDMARK}")
    st.title("Let's set you *up*.")
    st.write("Two quick things and Dara's ready.")

    prof = session.current_profile() or {}
    suggested_name = (prof.get("basics") or {}).get("name", "")

    with st.form("onboarding"):
        display_name = st.text_input("Your name", value=suggested_name, placeholder="Alex")
        username = st.text_input(
            "Username", placeholder="alex",
            help="Lowercase letters, numbers, and underscores. People can invite you by this.",
        )
        kind_label = st.radio("What brings you here?", list(_KINDS.values()), index=0)
        submitted = st.form_submit_button("Finish setup →", use_container_width=True)

    if not submitted:
        return

    display_name = display_name.strip()
    username = username.strip().lower()
    kind = next(k for k, v in _KINDS.items() if v == kind_label)

    if not display_name:
        st.error("Please enter your name.")
        return
    if not _valid_username(username):
        st.error("Username must be 3–20 characters: lowercase letters, numbers, or underscores.")
        return

    client = session.get_client()
    uid = session.user_id()
    if not profile_service.username_available(client, username, exclude_user_id=uid):
        st.error("That username is taken — try another.")
        return

    try:
        profile_service.complete_onboarding(
            client, uid, username=username, kind=kind, display_name=display_name,
            current=prof,
        )
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't save your profile: {e}")
        return

    session.refresh_profile()
    st.rerun()


def _valid_username(u: str) -> bool:
    import re

    return bool(re.fullmatch(r"[a-z0-9_]{3,20}", u))

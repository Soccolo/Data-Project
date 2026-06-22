"""Landing page — greet the user and pick a flow."""

from __future__ import annotations

import streamlit as st

from dara.config import settings
from . import session
from .common import WORDMARK, go, rule


def render() -> None:
    prof = session.current_profile()
    name = ((prof or {}).get("basics") or {}).get("name") if prof else None

    st.markdown(f"##### {WORDMARK}")
    if name:
        st.title(f"Hi {name}, meet *Dara*.")
    else:
        st.title("Meet *Dara*.")
    rule()
    st.write(
        "An AI that acts on your behalf — to find someone worth meeting, or to "
        "talk through a conflict with someone you already know. Pick a starting point."
    )

    st.write("")
    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            st.subheader("Find a match")
            st.write(
                "Two ways to do it: let Dara handle everything — it interviews you and "
                "talks to other people's Daras — or browse profiles yourself and let your "
                "Dara take over the moment you like someone."
            )
            if st.button("Let Dara find someone →", key="go_interview",
                         type="primary", use_container_width=True):
                go("interview")
            if st.button("Browse profiles myself →", key="go_browse",
                         use_container_width=True):
                go("browse")

    with right:
        with st.container(border=True):
            st.subheader("Mediate a conflict")
            st.write(
                "Bring a disagreement. Dara hears each side privately, then mediates "
                "between both Daras and hands each person a takeaway."
            )
            if st.button("Start mediation →", key="go_mediation",
                         type="primary", use_container_width=True):
                go("mediation")

    st.write("")
    if settings.ai_mode == "mock":
        st.caption(
            "Responses are mocked (`DARA_AI_MODE=mock`), so this runs with no provider key. "
            "Use the sidebar to change tier and watch model routing update."
        )
    elif not settings.accounts_enabled:
        st.caption(
            "Sign-in is decoupled for this demo. Use the sidebar to change tier and "
            "watch model routing update."
        )

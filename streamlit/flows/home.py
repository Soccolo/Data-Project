"""Landing page — pick a flow."""

from __future__ import annotations

import streamlit as st

from .common import WORDMARK, go


def render() -> None:
    st.markdown(f"##### {WORDMARK}")
    st.title("Meet *Dara*.")
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
                "Dara interviews you, learns who you are, then talks to other "
                "people's Daras to find someone worth a real conversation."
            )
            if st.button("Start the interview →", key="go_interview", use_container_width=True):
                go("interview")

    with right:
        with st.container(border=True):
            st.subheader("Mediate a conflict")
            st.write(
                "Bring a disagreement. Dara hears each side privately, then mediates "
                "between both Daras and hands each person a takeaway."
            )
            if st.button("Start mediation →", key="go_mediation", use_container_width=True):
                go("mediation")

    st.write("")
    st.caption(
        "PoC: sign-in is decoupled and AI responses are mocked, so this runs with no keys. "
        "Use the sidebar to change tier and watch model routing update."
    )

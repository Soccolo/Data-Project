"""Landing page — greet the user and pick a flow. Vibrant redesign:
custom HTML hero + flow cards (theme_components), native buttons beneath."""

from __future__ import annotations

import streamlit as st

from dara.config import settings
from . import session
from . import theme_components as tc
from .common import go


def render() -> None:
    prof = session.current_profile()
    name = ((prof or {}).get("basics") or {}).get("name") if prof else None

    title = (
        f'Hi {tc._esc(name)},<br>meet {tc.grad_word("Dara")}.'
        if name else f'Meet {tc.grad_word("Dara")}.'
    )
    tc.hero(
        title,
        "An AI that acts on your behalf — to find someone worth meeting, or to "
        "talk through a conflict with someone you already know. Pick a starting point.",
    )

    left, right = st.columns(2)

    with left:
        tc.flow_card(
            "Find a match",
            "Let Dara handle everything — it interviews you and talks to other "
            "people's Daras — or browse profiles yourself.",
            accent=tc.ROSE, filled=True,
        )
        if st.button("Let Dara find someone →", key="go_interview",
                     type="primary", use_container_width=True):
            go("interview")
        if st.button("Browse profiles myself →", key="go_browse",
                     use_container_width=True):
            go("browse")

    with right:
        tc.flow_card(
            "Mediate a conflict",
            "Bring a disagreement. Dara hears each side privately, then mediates "
            "between both Daras and hands each person a takeaway.",
            accent=tc.IRIS, filled=False,
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

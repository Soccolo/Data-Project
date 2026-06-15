"""Shared UI helpers used across flows."""

from __future__ import annotations

import streamlit as st

from dara import Purpose, Tier, resolve_model
from dara.config import settings
from dara.tiers import TIER_INFO
from . import session

WORDMARK = "─── D A R A ───"


def go(view: str) -> None:
    """Switch the active view and rerun."""
    st.session_state["view"] = view
    st.rerun()


def current_tier() -> Tier:
    """Tier comes from the signed-in profile; falls back to the demo selector
    (mock PoC mode) or 'free'."""
    prof = session.current_profile()
    if prof and prof.get("tier"):
        return prof["tier"]  # type: ignore[return-value]
    return st.session_state.get("tier", "free")  # type: ignore[return-value]


def sidebar() -> None:
    """Identity, tier, navigation, and PoC status. Shown on every in-app view."""
    with st.sidebar:
        st.markdown(f"##### {WORDMARK}")

        prof = session.current_profile()
        if prof:
            name = (prof.get("basics") or {}).get("name") or f"@{prof.get('username', '')}"
            st.write(f"**{name}**")
            st.caption(f"@{prof.get('username', '')} · {TIER_INFO[current_tier()].name} plan")

            st.divider()
            if st.button("✦  Home", use_container_width=True):
                go("home")
            if st.button("👤  Account", use_container_width=True):
                go("account")
            st.divider()
            if st.button("Sign out", use_container_width=True):
                session.logout()
                st.session_state["view"] = "home"
                st.rerun()
        else:
            # Mock PoC mode (no accounts): expose tier as a demo control.
            st.caption("Proof of concept")
            tiers = ["free", "pro", "x"]
            st.session_state["tier"] = st.radio(
                "Tier", tiers, index=tiers.index(current_tier()),
                help="Drives model routing. Higher tiers route sensitive calls to Claude.",
            )
            if st.session_state.get("view") != "home":
                st.divider()
                if st.button("← Back to start", use_container_width=True):
                    reset()
                    go("home")

        mode = "Mock" if settings.ai_mode == "mock" else "Live"
        auth_state = "on" if settings.accounts_enabled else "off (decoupled)"
        st.caption(f"AI: **{mode}**  ·  Auth: **{auth_state}**")


def model_caption(purpose: Purpose) -> None:
    """Show which model this call routes to for the active tier — the
    tier-routing table made visible, even when responses are mocked."""
    choice = resolve_model(purpose, current_tier())
    st.caption(f"↳ {purpose} → **{choice.label}** ({choice.model})")


def reset() -> None:
    """Clear per-flow state without dropping tier/view/auth."""
    keep = {"tier", "view", "auth_user", "auth_profile", "sb_client", "cookie_mgr"}
    for k in list(st.session_state.keys()):
        if k not in keep:
            del st.session_state[k]

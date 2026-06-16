"""Dara — Streamlit entry point.

A thin router. When Supabase is configured it runs the full account system
(email+password sign-in, onboarding, profile, plan, settings). When it isn't,
it falls back to the decoupled, no-auth PoC so the public demo keeps working.
AI responses are mocked (``DARA_AI_MODE=mock``) until you supply a provider key.
"""

from __future__ import annotations

import streamlit as st

from dara import profile as profile_service
from dara.config import settings
from flows import account, auth, home, interview, mediation, onboarding, session
from flows.common import inject_css, sidebar

st.set_page_config(page_title="Dara", page_icon="✦", layout="centered")
inject_css()  # Dara's theme — applies to auth, onboarding, and the app alike.

_VIEWS = {
    "home": home.render,
    "interview": interview.render,
    "mediation": mediation.render,
    "account": account.render,
}


def _run_app() -> None:
    sidebar()
    view = st.session_state.setdefault("view", "home")
    _VIEWS.get(view, home.render)()


def main() -> None:
    # No Supabase configured → decoupled PoC (no accounts).
    if not settings.accounts_enabled:
        _run_app()
        return

    # Accounts on: restore session, gate on auth, then onboarding, then app.
    session.try_restore()
    if not session.current_user():
        auth.render()
        return

    if not profile_service.is_onboarded(session.current_profile()):
        onboarding.render()
        return

    _run_app()


if __name__ == "__main__":
    main()

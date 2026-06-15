"""Session management for the Streamlit layer.

Owns one Supabase client per browser session (so users never share an auth
session) and persists the login across page reloads via a cookie. Cookie
persistence is best-effort: if the cookie component is unavailable, auth still
works for the lifetime of the session — you just re-login after a hard refresh.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Optional

import streamlit as st

from dara import auth as auth_service
from dara import profile as profile_service
from dara.supabase_client import make_client

_COOKIE = "dara_session"


# ─── Per-session client ──────────────────────────────────────────────
def get_client():
    if "sb_client" not in st.session_state:
        st.session_state["sb_client"] = make_client()
    return st.session_state["sb_client"]


def current_user() -> Optional[Any]:
    return st.session_state.get("auth_user")


def current_profile() -> Optional[dict]:
    return st.session_state.get("auth_profile")


def user_id() -> Optional[str]:
    u = current_user()
    if not u:
        return None
    return u.id if hasattr(u, "id") else u.get("id")


# ─── Cookie helpers (guarded) ────────────────────────────────────────
def _cookie_manager():
    if "cookie_mgr" not in st.session_state:
        try:
            import extra_streamlit_components as stx

            st.session_state["cookie_mgr"] = stx.CookieManager(key="dara_cookies")
        except Exception:  # noqa: BLE001 — persistence simply disabled
            st.session_state["cookie_mgr"] = None
    return st.session_state["cookie_mgr"]


def _persist(access: str, refresh: str) -> None:
    cm = _cookie_manager()
    if not cm:
        return
    try:
        cm.set(
            _COOKIE,
            json.dumps({"a": access, "r": refresh}),
            expires_at=datetime.now() + timedelta(days=14),
            key="dara_set_cookie",
        )
    except Exception:  # noqa: BLE001
        pass


def _clear_cookie() -> None:
    cm = _cookie_manager()
    if not cm:
        return
    try:
        cm.delete(_COOKIE, key="dara_del_cookie")
    except Exception:  # noqa: BLE001
        pass


# ─── Profile loading ─────────────────────────────────────────────────
def _load_profile() -> None:
    user = current_user()
    if not user:
        return
    try:
        prof = profile_service.ensure_profile(get_client(), user)
        st.session_state["auth_profile"] = prof
    except Exception as e:  # noqa: BLE001
        st.session_state["auth_profile_error"] = str(e)


def refresh_profile() -> None:
    _load_profile()


# ─── Login / logout / restore ────────────────────────────────────────
def login(result) -> None:
    """Adopt a successful AuthResult. The client already carries the session."""
    st.session_state["auth_user"] = result.user
    if result.access_token and result.refresh_token:
        _persist(result.access_token, result.refresh_token)
    _load_profile()


def logout() -> None:
    try:
        auth_service.sign_out(get_client())
    except Exception:  # noqa: BLE001
        pass
    _clear_cookie()
    for k in ("auth_user", "auth_profile", "auth_profile_error", "sb_client"):
        st.session_state.pop(k, None)


def try_restore() -> bool:
    """Restore a session from the cookie if one exists. Returns True if signed in."""
    if current_user():
        return True
    cm = _cookie_manager()
    if not cm:
        return False
    try:
        raw = cm.get(_COOKIE)
    except Exception:  # noqa: BLE001
        raw = None
    if not raw:
        return False
    try:
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        return False

    res = auth_service.restore(get_client(), data.get("a"), data.get("r"))
    if res.ok:
        st.session_state["auth_user"] = res.user
        if res.access_token and res.refresh_token:
            _persist(res.access_token, res.refresh_token)
        _load_profile()
        return True
    # Stale cookie — drop it.
    _clear_cookie()
    return False

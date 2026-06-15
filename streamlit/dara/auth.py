"""Authentication service (email + password).

Pure functions over a Supabase client. The Streamlit layer owns the client and
session lifecycle; this module just wraps Supabase Auth (GoTrue) with a stable,
result-typed surface and degrades gracefully across library versions and
project settings (e.g. email-confirmation on vs off).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from supabase import Client

from .supabase_client import make_admin_client


@dataclass
class AuthResult:
    ok: bool
    user: Optional[Any] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    # Set when sign-up succeeded but the user must confirm their email before
    # they can sign in (depends on the Supabase project's Auth settings).
    needs_confirmation: bool = False
    error: Optional[str] = None


def _friendly(e: Exception) -> str:
    msg = str(e) or e.__class__.__name__
    low = msg.lower()
    if "already registered" in low or "already been registered" in low:
        return "That email is already registered. Try signing in instead."
    if "invalid login" in low or "invalid" in low and "credential" in low:
        return "Email or password is incorrect."
    if "email not confirmed" in low:
        return "Please confirm your email first — check your inbox for the link."
    if "password should be" in low or "password" in low and "characters" in low:
        return "Password is too short — use at least 6 characters."
    return msg


def sign_up(client: Client, email: str, password: str) -> AuthResult:
    try:
        resp = client.auth.sign_up({"email": email.strip().lower(), "password": password})
    except Exception as e:  # noqa: BLE001
        return AuthResult(ok=False, error=_friendly(e))

    session = getattr(resp, "session", None)
    user = getattr(resp, "user", None)
    if session and getattr(session, "access_token", None):
        # Confirmation is off — they're signed in immediately.
        return AuthResult(ok=True, user=user,
                          access_token=session.access_token,
                          refresh_token=session.refresh_token)
    # Confirmation required: user created, no session yet.
    return AuthResult(ok=True, user=user, needs_confirmation=True)


def sign_in(client: Client, email: str, password: str) -> AuthResult:
    try:
        resp = client.auth.sign_in_with_password({"email": email.strip().lower(), "password": password})
    except Exception as e:  # noqa: BLE001
        return AuthResult(ok=False, error=_friendly(e))

    session = getattr(resp, "session", None)
    if not session:
        return AuthResult(ok=False, error="Could not sign in.")
    return AuthResult(ok=True, user=getattr(resp, "user", None),
                      access_token=session.access_token,
                      refresh_token=session.refresh_token)


def restore(client: Client, access_token: str, refresh_token: str) -> AuthResult:
    """Re-attach a saved session to a fresh client (used on page reload)."""
    try:
        resp = client.auth.set_session(access_token, refresh_token)
    except Exception as e:  # noqa: BLE001
        return AuthResult(ok=False, error=_friendly(e))
    session = getattr(resp, "session", None)
    user = getattr(resp, "user", None)
    if not session:
        return AuthResult(ok=False, error="Session expired.")
    return AuthResult(ok=True, user=user,
                      access_token=session.access_token,
                      refresh_token=session.refresh_token)


def sign_out(client: Client) -> None:
    try:
        client.auth.sign_out()
    except Exception:  # noqa: BLE001 — best effort; the local session is cleared regardless
        pass


def send_password_reset(client: Client, email: str, redirect_to: Optional[str] = None) -> AuthResult:
    options = {"redirect_to": redirect_to} if redirect_to else {}
    fn = getattr(client.auth, "reset_password_for_email", None) or \
        getattr(client.auth, "reset_password_email", None)
    if fn is None:
        return AuthResult(ok=False, error="Password reset is unavailable in this build.")
    try:
        fn(email.strip().lower(), options)
    except TypeError:
        fn(email.strip().lower())
    except Exception as e:  # noqa: BLE001
        return AuthResult(ok=False, error=_friendly(e))
    return AuthResult(ok=True)


def update_password(client: Client, new_password: str) -> AuthResult:
    try:
        client.auth.update_user({"password": new_password})
    except Exception as e:  # noqa: BLE001
        return AuthResult(ok=False, error=_friendly(e))
    return AuthResult(ok=True)


def update_email(client: Client, new_email: str) -> AuthResult:
    try:
        client.auth.update_user({"email": new_email.strip().lower()})
    except Exception as e:  # noqa: BLE001
        return AuthResult(ok=False, error=_friendly(e))
    # Supabase emails a confirmation to the new address before the change sticks.
    return AuthResult(ok=True, needs_confirmation=True)


def delete_account(client: Client, user_id: str) -> AuthResult:
    """GDPR delete. With a service-role key, removes the auth identity (which
    cascades all app data). Otherwise removes app data via the user's own
    RLS-scoped session, then signs out — the auth identity is left for an
    admin to purge."""
    admin = make_admin_client()
    try:
        if admin is not None:
            admin.auth.admin.delete_user(user_id)  # cascades public.users + children
        else:
            # ON DELETE CASCADE on public.users children removes photos, state,
            # meets, and conflict sessions for this user.
            client.table("users").delete().eq("id", user_id).execute()
            sign_out(client)
    except Exception as e:  # noqa: BLE001
        return AuthResult(ok=False, error=_friendly(e))
    return AuthResult(ok=True)

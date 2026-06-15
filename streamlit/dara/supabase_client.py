"""Supabase client factories.

Streamlit runs server-side, so there is no browser/server split like the
Next.js scaffold. Row-level security (defined in ``../../supabase/schema.sql``)
enforces who can read what once a user session is attached to the client.

These factories are intentionally *pure* — they build a fresh client and don't
cache it. A long-lived singleton would share one auth session across every
visitor of the deployed app, so per-user session management lives in the
Streamlit layer (``flows/session.py``), which keeps one client per browser
session and attaches that user's tokens to it.
"""

from __future__ import annotations

from supabase import Client, create_client

from .config import settings


def make_client() -> Client:
    """A new anon-key client. RLS applies; gains a user's privileges only after
    a session is attached via ``auth.set_session`` / ``sign_in_with_password``."""
    if not settings.supabase_configured:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY "
            "(see .env.example / .streamlit/secrets.toml.example)."
        )
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def make_admin_client() -> Client | None:
    """A service-role client that bypasses RLS. Used only for hard account
    deletion. Returns None when no service-role key is configured."""
    if not (settings.supabase_url and settings.supabase_service_role_key):
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

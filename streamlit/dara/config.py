"""Environment / secrets loading.

Reads configuration from the process environment (``.env`` in local dev) and,
when running under Streamlit, from ``st.secrets``. Secrets take precedence so
the same code works both locally and on Streamlit Community Cloud.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

# Honour a local .env (repo root or app dir) in dev. On Streamlit Cloud there is
# no .env — secrets come from st.secrets — so this is a no-op there.
try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
except Exception:  # noqa: BLE001 — dotenv is optional
    pass


def _get(name: str, default: str = "") -> str:
    # Prefer Streamlit secrets when available (Community Cloud / .streamlit/secrets.toml),
    # fall back to the process environment for local dev.
    try:
        import streamlit as st  # imported lazily so non-UI code can use this too

        if name in st.secrets:
            val = str(st.secrets[name])
            if val != "":            # treat an empty secret as unset → fall through to env
                return val
    except Exception:
        pass
    return os.environ.get(name, default)


def _flag(name: str, default: bool) -> bool:
    raw = _get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    # ── PoC toggles ───────────────────────────────────────────────────
    # The proof-of-concept runs decoupled from sign-in and against mock AI
    # so it deploys anywhere with zero keys. Flip these on once you wire up
    # real auth / live providers.
    require_auth: bool   # gate the app behind Supabase magic-link sign-in
    ai_mode: str         # 'mock' (canned responses) or 'live' (call providers)

    # ── Supabase ──────────────────────────────────────────────────────
    supabase_url: str
    supabase_anon_key: str
    # Optional. Server-side only. Enables hard account deletion (auth user +
    # cascade) via the admin API. Without it, deletion removes app data and
    # signs the user out, but leaves the auth identity. NEVER expose to a client.
    supabase_service_role_key: str

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def accounts_enabled(self) -> bool:
        """Real accounts turn on once Supabase is configured (or forced).
        Until then the app runs the decoupled, no-auth PoC."""
        return self.require_auth or self.supabase_configured

    # ── AI providers (only needed when ai_mode == 'live') ─────────────
    # Server-side only — never exposed to the browser.
    google_api_key: str
    anthropic_api_key: str
    deepseek_api_key: str


@lru_cache(maxsize=1)
def _load() -> Settings:
    return Settings(
        require_auth=_flag("DARA_REQUIRE_AUTH", default=False),
        ai_mode=(_get("DARA_AI_MODE", "mock").strip().lower() or "mock"),
        supabase_url=_get("SUPABASE_URL") or _get("NEXT_PUBLIC_SUPABASE_URL"),
        supabase_anon_key=_get("SUPABASE_ANON_KEY") or _get("NEXT_PUBLIC_SUPABASE_ANON_KEY"),
        supabase_service_role_key=_get("SUPABASE_SERVICE_ROLE_KEY"),
        google_api_key=_get("GOOGLE_API_KEY"),
        anthropic_api_key=_get("ANTHROPIC_API_KEY"),
        deepseek_api_key=_get("DEEPSEEK_API_KEY"),
    )


settings = _load()

"""Shared UI helpers used across flows."""

from __future__ import annotations

import streamlit as st

from dara import Purpose, Tier, resolve_model
from dara.config import settings
from dara.tiers import TIER_INFO
from . import session

WORDMARK = "─── D A R A ───"

# ─── Brand styling ───────────────────────────────────────────────────
# Signature: a rose→iris gradient — two colours meeting in the middle, which
# is what Dara does in both flows (two people, or two sides of a conflict).
# It lands on the hero title and the one primary action per screen; the rest
# stays quiet. Display face is Fraunces (warm serif), body is Inter.
_BRAND_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700;9..144,900&family=Inter:wght@400;500;600;700&display=swap');

:root{
  --dara-rose:#FF5D8F;
  --dara-iris:#6D5EF6;
  --dara-ink:#1F1633;
  --dara-muted:#8A82A6;
  --dara-grad:linear-gradient(100deg,var(--dara-rose) 0%,var(--dara-iris) 100%);
}

/* Body type everywhere */
html, body, [class*="css"], .stMarkdown, p, li, label,
input, textarea, button, .stSelectbox, .stRadio{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
}

/* Display headings in Fraunces */
h1, h2, h3{ font-family:'Fraunces','Inter',Georgia,serif !important;
  letter-spacing:-0.015em; }
h1{ font-weight:900; font-size:2.7rem; line-height:1.06; margin-bottom:.2rem; }
h2{ font-weight:700; }
h3{ font-weight:600; }

/* Signature: the page title carries the gradient */
.stApp h1{
  background:var(--dara-grad);
  -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color:transparent; color:transparent;
  width:max-content; max-width:100%;
}
.stApp h1 em{ font-style:italic; }

/* Buttons: rounded, with motion on hover */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button{
  border-radius:12px; font-weight:600; padding:.55rem 1rem;
  border:1px solid rgba(109,94,246,.22);
  transition:transform .12s ease, box-shadow .14s ease, border-color .12s ease;
}
.stButton>button:hover, .stFormSubmitButton>button:hover{
  transform:translateY(-1px); border-color:var(--dara-iris);
  box-shadow:0 8px 22px -10px rgba(109,94,246,.45);
}

/* Boldness lives here: primary actions + every form submit get the gradient */
.stFormSubmitButton>button,
.stButton>button[kind="primary"],
.stButton>button[data-testid="stBaseButton-primary"]{
  background:var(--dara-grad) !important; color:#fff !important;
  border:1px solid transparent !important;
  box-shadow:0 8px 20px -8px rgba(109,94,246,.55);
}
.stFormSubmitButton>button:hover,
.stButton>button[kind="primary"]:hover{
  color:#fff !important; box-shadow:0 12px 26px -8px rgba(255,93,143,.55);
}

/* Bordered containers become soft cards */
[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius:18px !important;
  border:1px solid rgba(109,94,246,.16) !important;
  box-shadow:0 14px 38px -22px rgba(31,22,51,.40);
  background:#fff; padding:.25rem;
}

/* Rounded inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stSelectbox div[data-baseweb="select"]>div{ border-radius:10px !important; }
.stTextInput input:focus, .stTextArea textarea:focus{
  border-color:var(--dara-iris) !important;
  box-shadow:0 0 0 3px rgba(109,94,246,.18) !important;
}

/* Sidebar: lavender wash with a gradient seam */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#F7F4FF,#F0ECFF);
  border-right:1px solid rgba(109,94,246,.12);
}
[data-testid="stSidebar"]::before{
  content:""; position:absolute; top:0; left:0; right:0; height:4px;
  background:var(--dara-grad);
}

/* Chat bubbles get a faint tint */
[data-testid="stChatMessage"]{ border-radius:16px; }

/* The connecting-line motif — used under section headers */
.dara-rule{ height:3px; width:60px; border:0; border-radius:3px;
  margin:.1rem 0 1.1rem; background:var(--dara-grad); }

/* Wizard step pills */
.dara-steps{ display:flex; gap:.5rem; margin:.1rem 0 1.1rem; flex-wrap:wrap; }
.dara-step{ font:600 .7rem/1 'Inter',sans-serif; letter-spacing:.05em;
  text-transform:uppercase; padding:.42rem .8rem; border-radius:999px;
  color:var(--dara-muted); background:#EEEAFB; }
.dara-step.active{ color:#fff; background:var(--dara-grad);
  box-shadow:0 6px 16px -8px rgba(109,94,246,.6); }

@media (prefers-reduced-motion: reduce){
  .stButton>button, .stFormSubmitButton>button{ transition:none; }
  .stButton>button:hover, .stFormSubmitButton>button:hover{ transform:none; }
}
</style>
"""


def inject_css() -> None:
    """Apply Dara's theme. Safe to call on every rerun (idempotent style tag)."""
    st.markdown(_BRAND_CSS, unsafe_allow_html=True)


def rule() -> None:
    """The gradient connecting-line motif."""
    st.markdown('<div class="dara-rule"></div>', unsafe_allow_html=True)


def steps(active: int, labels: list[str]) -> None:
    """Render wizard progress pills (1-indexed active step)."""
    pills = "".join(
        f'<span class="dara-step{" active" if i == active else ""}">'
        f'{i}. {label}</span>'
        for i, label in enumerate(labels, start=1)
    )
    st.markdown(f'<div class="dara-steps">{pills}</div>', unsafe_allow_html=True)


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
            if st.button("💬  Matches", use_container_width=True):
                go("matches")
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
            st.divider()
            if st.button("💬  Matches", use_container_width=True):
                go("matches")
            if st.session_state.get("view") != "home":
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

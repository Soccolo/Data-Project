"""Shared UI helpers used across flows."""

from __future__ import annotations

import streamlit as st

from dara import Purpose, Tier, resolve_model
from dara.config import settings
from dara.tiers import TIER_INFO
from . import session

WORDMARK = "─── D A R A ───"

# ─── Brand styling (vibrant redesign) ────────────────────────────────
# Signature: a rose→iris gradient — two colours meeting in the middle, which
# is what Dara does in both flows (two people, or two sides of a conflict).
# The expressive direction widens the palette with an amber spark and a mint
# "safe/mediation" accent, swaps the body face to Hanken Grotesk (Fraunces
# stays for display), warms the canvas, and rounds everything up into soft,
# glowing cards. The gradient lands on hero titles + the one primary action
# per screen; the rest stays quiet.
_BRAND_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;0,9..144,700;0,9..144,900;1,9..144,500;1,9..144,700&family=Hanken+Grotesk:wght@400;500;600;700;800&display=swap');

:root{
  --dara-rose:#FF4D87;
  --dara-iris:#6D5EF6;
  --dara-amber:#FFB23E;
  --dara-mint:#1FC8A9;
  --dara-ink:#1B1430;
  --dara-muted:#8C84A8;
  --dara-line:rgba(109,94,246,.14);
  --dara-grad:linear-gradient(105deg,var(--dara-rose) 0%,var(--dara-iris) 100%);
}

/* Warm, glowing canvas — forced so it wins over Streamlit's theme colour,
   which is why config.toml not being read no longer matters for the canvas. */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"]{
  background:radial-gradient(120% 80% at 82% -10%,#FFF1F5 0%,#FFF8F4 46%,#F4EEFC 100%) !important;
}
[data-testid="stHeader"]{ background:transparent !important; }

/* Body type everywhere */
html, body, [class*="css"], .stMarkdown, p, li, label,
input, textarea, button, .stSelectbox, .stRadio, .stCaption, [data-testid="stCaptionContainer"]{
  font-family:'Hanken Grotesk',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
}

/* Display headings in Fraunces */
h1, h2, h3{ font-family:'Fraunces','Hanken Grotesk',Georgia,serif !important;
  letter-spacing:-0.02em; }
h1{ font-weight:900; font-size:3rem; line-height:1.02; margin-bottom:.2rem; }
h2{ font-weight:700; }
h3{ font-weight:700; }

/* Signature: the page title carries the gradient */
.stApp h1{
  background:var(--dara-grad);
  -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color:transparent; color:transparent;
  width:max-content; max-width:100%;
}
.stApp h1 em{ font-style:italic; font-weight:500; }

/* Buttons: rounded pills, with motion on hover */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button{
  border-radius:14px; font-weight:700; padding:.7rem 1.15rem;
  border:1px solid rgba(109,94,246,.20); background:#fff; color:var(--dara-ink);
  transition:transform .12s ease, box-shadow .14s ease, border-color .12s ease;
}
.stButton>button:hover, .stFormSubmitButton>button:hover, .stDownloadButton>button:hover{
  transform:translateY(-1px); border-color:var(--dara-iris);
  box-shadow:0 10px 26px -12px rgba(109,94,246,.5);
}

/* Boldness lives here: primary actions + every form submit get the gradient */
.stFormSubmitButton>button,
.stButton>button[kind="primary"],
.stButton>button[data-testid="stBaseButton-primary"]{
  background:var(--dara-grad) !important; color:#fff !important;
  border:1px solid transparent !important;
  box-shadow:0 14px 30px -12px rgba(109,94,246,.6);
}
.stFormSubmitButton>button:hover,
.stButton>button[kind="primary"]:hover{
  color:#fff !important; box-shadow:0 18px 36px -12px rgba(255,77,135,.6);
}

/* Bordered containers become soft, glowing cards */
[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius:22px !important;
  border:1px solid var(--dara-line) !important;
  box-shadow:0 22px 54px -32px rgba(31,22,51,.42);
  background:#fff; padding:.4rem;
}

/* Rounded inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stSelectbox div[data-baseweb="select"]>div{
  border-radius:12px !important; border-color:#E6DEF7 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus{
  border-color:var(--dara-iris) !important;
  box-shadow:0 0 0 3px rgba(109,94,246,.18) !important;
}

/* Sidebar: lavender wash with a gradient seam */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#FBF8FF,#F3ECFD);
  border-right:1px solid rgba(109,94,246,.12);
}
[data-testid="stSidebar"]::before{
  content:""; position:absolute; top:0; left:0; right:0; height:4px;
  background:var(--dara-grad); z-index:5;
}

/* Chat bubbles: clean soft cards; the user's side picks up the rose gradient */
[data-testid="stChatMessage"]{
  border-radius:18px; border:1px solid var(--dara-line);
  background:#fff; box-shadow:0 12px 30px -24px rgba(31,22,51,.5);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){
  background:linear-gradient(120deg,var(--dara-rose),#FF7FA6);
  border-color:transparent;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) li,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) span{
  color:#fff !important;
}

/* Chat composer */
[data-testid="stChatInput"]{ border-radius:14px; border-color:#E6DEF7; }

/* Compatibility & other metrics — the number carries the gradient */
[data-testid="stMetricValue"]{
  font-family:'Fraunces','Hanken Grotesk',serif !important; font-weight:900;
  background:var(--dara-grad);
  -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color:transparent; color:transparent;
}

/* Progress bars (OCEAN reads, match search) take the gradient */
[data-testid="stProgress"] div[role="progressbar"] > div,
.stProgress div[role="progressbar"] > div{
  background:var(--dara-grad) !important;
}

/* Info / success / error tints, warmed up */
[data-testid="stAlertContainer"]{ border-radius:14px; }

/* The connecting-line motif — used under section headers */
.dara-rule{ height:3px; width:64px; border:0; border-radius:3px;
  margin:.1rem 0 1.1rem; background:var(--dara-grad); }

/* Wizard step pills */
.dara-steps{ display:flex; gap:.5rem; margin:.1rem 0 1.1rem; flex-wrap:wrap; }
.dara-step{ font:700 .72rem/1 'Hanken Grotesk',sans-serif; letter-spacing:.05em;
  text-transform:uppercase; padding:.45rem .85rem; border-radius:999px;
  color:var(--dara-muted); background:#EFEAFB; }
.dara-step.active{ color:#fff; background:var(--dara-grad);
  box-shadow:0 8px 18px -8px rgba(109,94,246,.65); }

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


_OCEAN_TRAITS = [
    ("openness", "Openness",
     ("grounded and practical", "a mix of routine and novelty", "curious, imaginative, open to new things")),
    ("conscientiousness", "Conscientiousness",
     ("spontaneous and flexible", "organised when it counts", "organised, reliable, plan-oriented")),
    ("extraversion", "Extraversion",
     ("reserved, recharges in quiet", "comfortable either way", "outgoing, energised by people")),
    ("agreeableness", "Agreeableness",
     ("direct, holds their own line", "warm but willing to push back", "warm, cooperative, easy-going")),
    ("neuroticism", "Emotional sensitivity",
     ("calm and even-keeled", "generally steady", "feels things deeply, sensitive to stress")),
]


def _ocean_phrase(triplet, score: int) -> str:
    low, mid, high = triplet
    return low if score < 40 else (high if score > 65 else mid)


def render_portrait(portrait: dict) -> None:
    """Shared 'what Dara learned' view — OCEAN bars with one-line reads, speaking
    style, interests, values, notes. Used by the interview screen and Account."""
    bf = (portrait or {}).get("big_five") or {}
    if any(bf.get(k) is not None for k, _, _ in _OCEAN_TRAITS):
        st.subheader("Personality (OCEAN)")
        for key, label, triplet in _OCEAN_TRAITS:
            v = bf.get(key)
            if v is None:
                continue
            v = int(v)
            st.progress(v / 100, text=f"{label} · {v}")
            st.caption(_ocean_phrase(triplet, v))

    if portrait.get("speech_notes"):
        st.subheader("How you talk")
        st.write(portrait["speech_notes"])

    cols = st.columns(2)
    if portrait.get("interests"):
        with cols[0]:
            st.subheader("Interests")
            st.write(", ".join(portrait["interests"]))
    if portrait.get("values"):
        with cols[1]:
            st.subheader("Values")
            st.write(", ".join(portrait["values"]))

    if portrait.get("observations"):
        st.subheader("Notes")
        for o in portrait["observations"]:
            st.write(f"• {o}")

    if portrait.get("vibe"):
        st.caption(f"Overall vibe: {portrait['vibe']}")


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
            if st.button("🔥  Browse", use_container_width=True):
                go("browse")
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

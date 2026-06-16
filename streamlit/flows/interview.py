"""Matchmaking flow: Dara interviews the user, then reveals a scored match."""

from __future__ import annotations

import streamlit as st

from dara import call_ai, matching
from .common import current_tier, model_caption
from . import session

# Number of questions Dara asks before offering to reveal a match.
_MAX_TURNS = 5

_SYSTEM = (
    "You are Dara, a warm, curious matchmaker interviewing a new user to learn "
    "who they are. Ask one short question at a time. Reflect briefly on what they "
    "said before asking the next. Keep it to two sentences."
)


def _ask(**kwargs):
    """Call the model, returning (text, error)."""
    try:
        return call_ai(**kwargs), None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def _messages() -> list[dict]:
    return st.session_state.setdefault("iv_messages", [])


def _client():
    """The Supabase client, but only when there's a signed-in user — so
    matchmaking runs against real people. None in the no-auth PoC, which makes
    the matcher simulate a candidate."""
    try:
        return session.get_client() if session.current_user() else None
    except Exception:  # noqa: BLE001
        return None


def render() -> None:
    st.markdown("##### Find a match")
    st.title("Dara is *listening*.")
    model_caption("interview")

    msgs = _messages()
    if not msgs:
        opener, err = _ask(purpose="interview", system_prompt=_SYSTEM, tier=current_tier(), history=[])
        if err:
            st.error(f"Dara couldn't start: {err}")
            return
        msgs.append({"role": "assistant", "content": opener})

    user_turns = sum(1 for m in msgs if m["role"] == "user")

    for m in msgs:
        role = "assistant" if m["role"] == "assistant" else "user"
        with st.chat_message(role, avatar="✨" if role == "assistant" else None):
            st.write(m["content"])

    if st.session_state.get("iv_match"):
        _render_match(st.session_state["iv_match"])
        return

    # Once Dara has enough to go on, offer the match — but DON'T return here, so
    # the chat input below still renders and the user can keep talking if they
    # want. (The early return that used to live here is what cut the
    # conversation off.)
    if user_turns >= _MAX_TURNS:
        st.success("I've got enough to go on whenever you're ready — or keep talking.")
        if st.button("See who Dara found →", type="primary", use_container_width=True):
            with st.spinner("Talking to other Daras…"):
                st.session_state["iv_match"] = matching.find_match(
                    conversation=msgs,
                    tier=current_tier(),
                    client=_client(),
                    me=session.current_profile(),
                )
            st.rerun()

    prompt = st.chat_input("Tell Dara…")
    if prompt:
        msgs.append({"role": "user", "content": prompt})
        reply, err = _ask(
            purpose="interview", system_prompt=_SYSTEM, tier=current_tier(),
            user_text=prompt, history=msgs,
        )
        if err:
            msgs.pop()  # roll back the unanswered user turn
            st.error(f"Dara didn't respond: {err}")
        else:
            msgs.append({"role": "assistant", "content": reply})
        st.rerun()


def _render_match(match: dict) -> None:
    cand = match.get("candidate") or {}
    cb = cand.get("basics") or {}
    photos = cand.get("_photos") or []
    fit = match.get("photo_fit") or {}

    with st.container(border=True):
        st.subheader(f"Your match: {cb.get('name', 'Someone')}")
        if photos and photos[0].get("signed_url"):
            st.image(photos[0]["signed_url"], use_container_width=True)

        meta = []
        if cb.get("age"):
            meta.append(str(cb["age"]))
        if cb.get("job"):
            meta.append(cb["job"])
        if cb.get("nationality"):
            meta.append(cb["nationality"])
        if cb.get("height_cm"):
            meta.append(f"{cb['height_cm']}cm")
        if meta:
            st.caption(" · ".join(meta))
        if cb.get("bio"):
            st.write(cb["bio"])

        st.metric("Compatibility", f"{match.get('score', 0)}%",
                  help="Dara's verdict after weighing your interview, preferences, and photos.")
        if match.get("verdict"):
            st.write(f"**{match['verdict']}**")
        for r in match.get("reasons", []):
            st.write(f"• {r}")

        if fit.get("impression"):
            st.divider()
            st.caption("Dara's read of their photos")
            st.write(fit["impression"])
            if fit.get("vibe_tags"):
                st.caption(" · ".join(fit["vibe_tags"]))

    if match.get("simulated"):
        st.caption(
            "Demo candidate — once other registered users fit your preferences, Dara "
            "matches against real people and analyses their actual photos."
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Propose a meet", type="primary", use_container_width=True):
            st.toast("In the full app this sends a meet proposal.", icon="✨")
    with col2:
        if st.button("Start over", use_container_width=True):
            for k in ("iv_messages", "iv_match"):
                st.session_state.pop(k, None)
            st.rerun()

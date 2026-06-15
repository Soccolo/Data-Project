"""Matchmaking flow: Dara interviews the user, then reveals a scored match."""

from __future__ import annotations

import streamlit as st

from dara import call_ai
from dara import schemas
from .common import current_tier, model_caption

# Number of questions Dara asks before offering to reveal a match.
_MAX_TURNS = 5

_SYSTEM = (
    "You are Dara, a warm, curious matchmaker interviewing a new user to learn "
    "who they are. Ask one short question at a time. Reflect briefly on what they "
    "said before asking the next. Keep it to two sentences."
)

_SCORE_SYSTEM = (
    "You are Dara, turning a matchmaking interview into a compatibility verdict "
    "for this user about a candidate Dara found. Based on the conversation, return "
    "JSON with: score (integer 0-100), verdict (one short, warm sentence), and "
    "reasons (3 short, specific strings). Ground every reason in what they said."
)


def _ask(**kwargs):
    """Call the model, returning (text, error)."""
    try:
        return call_ai(**kwargs), None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def _messages() -> list[dict]:
    return st.session_state.setdefault("iv_messages", [])


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

    if user_turns >= _MAX_TURNS:
        st.success("That's enough for me to go on.")
        if st.button("See who Dara found →", use_container_width=True):
            with st.spinner("Talking to other Daras…"):
                raw, err = _ask(
                    purpose="score", system_prompt=_SCORE_SYSTEM, tier=current_tier(),
                    history=msgs, schema=schemas.SCORE, max_tokens=700,
                )
            if err:
                st.error(f"Couldn't score the match: {err}")
                return
            st.session_state["iv_match"] = schemas.normalize_score(raw)
            st.rerun()
        return

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
    with st.container(border=True):
        st.subheader("Your match")
        st.metric("Compatibility", f"{match.get('score', 0)}%",
                  help="Dara's verdict after the proxy conversation.")
        if match.get("verdict"):
            st.write(f"**{match['verdict']}**")
        for r in match.get("reasons", []):
            st.write(f"• {r}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Propose a meet", use_container_width=True):
            st.toast("In the full app this sends a meet proposal.", icon="✨")
    with col2:
        if st.button("Start over", use_container_width=True):
            for k in ("iv_messages", "iv_match"):
                st.session_state.pop(k, None)
            st.rerun()

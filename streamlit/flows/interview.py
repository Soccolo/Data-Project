"""Matchmaking flow: Dara interviews the user, then reveals a scored match."""

from __future__ import annotations

import streamlit as st

from dara import call_ai, matching, meets
from dara import profile as profile_service
from .common import current_tier, model_caption, go, render_portrait
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


def _draft_ctx():
    """(client, uid) when signed in, else (None, None). Drafts only persist for
    signed-in users; the no-auth PoC keeps the conversation in session only."""
    client = _client()
    uid = session.user_id()
    return (client, uid) if (client and uid) else (None, None)


def _messages() -> list[dict]:
    # First access this session: restore any saved draft (survives a refresh).
    if "iv_messages" not in st.session_state:
        client, uid = _draft_ctx()
        st.session_state["iv_messages"] = (
            profile_service.load_interview_draft(client, uid) if (client and uid) else []
        )
    return st.session_state["iv_messages"]


def _save_draft(msgs) -> None:
    client, uid = _draft_ctx()
    if client and uid:
        profile_service.save_interview_draft(client, uid, msgs)


def _clear_draft() -> None:
    client, uid = _draft_ctx()
    if client and uid:
        profile_service.clear_interview_draft(client, uid)


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
        _save_draft(msgs)

    user_turns = sum(1 for m in msgs if m["role"] == "user")

    for m in msgs:
        role = "assistant" if m["role"] == "assistant" else "user"
        with st.chat_message(role, avatar="✨" if role == "assistant" else None):
            st.write(m["content"])

    if st.session_state.get("iv_match"):
        _render_match(st.session_state["iv_match"])
        return

    if st.session_state.get("iv_portrait"):
        _render_portrait_screen(st.session_state["iv_portrait"], msgs)
        return

    # Once Dara has enough to go on, offer to finish (build the profile) or jump
    # to a match — but DON'T return here, so the chat input below still renders
    # and the user can keep talking if they want.
    if user_turns >= _MAX_TURNS:
        st.success("I've got enough to go on whenever you're ready — or keep talking.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("See what Dara learned", use_container_width=True):
                with st.spinner("Dara is writing up what it learned…"):
                    st.session_state["iv_portrait"] = matching.get_or_build_portrait(
                        session.current_profile() or {"basics": {}}, msgs, current_tier(), _client(),
                    )
                _clear_draft()
                st.rerun()
        with c2:
            if st.button("See who Dara found →", type="primary", use_container_width=True):
                _reveal_match(msgs)

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
            _save_draft(msgs)
        st.rerun()


def _reveal_match(msgs: list) -> None:
    """Run the match and stream the Dara-to-Dara conversation live, message by
    message, into a placeholder — then show the full match card on rerun."""
    holder = st.empty()

    def _on_turn(i, total, convo):
        with holder.container():
            st.caption(f"Your Daras are talking… {i}/{total}")
            for m in convo:
                is_me = m.get("speaker") == "me"
                with st.chat_message("user" if is_me else "assistant", avatar=None if is_me else "✨"):
                    st.write(m.get("content", ""))

    st.session_state["iv_match"] = matching.find_match(
        conversation=msgs,
        tier=current_tier(),
        client=_client(),
        me=session.current_profile(),
        on_turn=_on_turn,
    )
    holder.empty()
    st.session_state.pop("iv_portrait", None)
    _clear_draft()
    st.rerun()


def _render_match(match: dict) -> None:
    if st.session_state.get("iv_connect_msg"):
        st.success(st.session_state.pop("iv_connect_msg"))

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
                  help="Dara's verdict after the Dara-to-Dara conversation, your preferences, and the photo read.")
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

    transcript = match.get("transcript") or []
    if transcript:
        me_name = match.get("me_name", "You")
        their_name = cb.get("name", "Them")
        with st.expander(f"Read the {me_name}-to-{their_name} conversation · {len(transcript)} messages"):
            for m in transcript:
                who = me_name if m.get("speaker") == "me" else their_name
                st.markdown(f"**{who}:** {m.get('content', '')}")

    source = match.get("source")
    if source == "seed":
        st.caption(
            "Test candidate from the built-in seed pool. Once other real users fit your "
            "preferences, Dara matches against them and reads their actual photos."
        )
    elif source == "simulated":
        st.caption(
            "Simulated candidate — add registered users who fit your preferences and Dara "
            "matches against real people and analyses their actual photos."
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect →", type="primary", use_container_width=True):
            _connect(match)
    with col2:
        if st.button("Start over", use_container_width=True):
            _clear_draft()
            for k in ("iv_messages", "iv_match", "iv_portrait"):
                st.session_state.pop(k, None)
            st.rerun()


def _render_portrait_screen(portrait: dict, msgs: list) -> None:
    st.subheader("What Dara learned about you")
    st.caption("Dara's impression from your interview — a read on how you came across, not a clinical test.")
    render_portrait(portrait)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("See who Dara found →", type="primary", use_container_width=True):
            _reveal_match(msgs)
    with c2:
        if st.button("Start over", use_container_width=True):
            _clear_draft()
            for k in ("iv_messages", "iv_match", "iv_portrait"):
                st.session_state.pop(k, None)
            st.rerun()


def _connect(match: dict) -> None:
    cand = match.get("candidate") or {}
    name = (cand.get("basics") or {}).get("name", "them")

    # Real registered user → a genuine connect request / mutual match.
    if match.get("source") == "real" and meets.is_real_user_id(cand.get("id")):
        client, me = _client(), session.current_profile()
        if not (client and me):
            st.session_state["iv_connect_msg"] = "Sign in to connect with real users."
            st.rerun()
        res = meets.connect(client, me, cand, match_data={
            "transcript": match.get("transcript") or [],
            "score": match.get("score"),
            "verdict": match.get("verdict"),
            "reasons": match.get("reasons") or [],
        })
        if res.get("matched"):
            go("matches")  # already a match → jump straight to the chat list
        else:
            st.session_state["iv_connect_msg"] = (
                f"Connect request sent to {name}. You'll match if they accept."
            )
            st.rerun()
        return

    # Seed / simulated candidate → auto-match + AI persona chat.
    sm = st.session_state.setdefault("seed_matches", {})
    cid = cand.get("id") or f"seed_{cand.get('username', 'x')}"
    sm.setdefault(cid, {"candidate": cand, "messages": []})
    go("matches")

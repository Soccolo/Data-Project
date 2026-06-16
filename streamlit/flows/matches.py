"""Matches: accept incoming connect requests, see your matches, and chat.

Real matches go through Supabase (meets + messages); the other person is a real
human who replies when they're online. Seed/test candidates have no human, so
they auto-match and reply in-voice via AI, kept in session state.
"""

from __future__ import annotations

import streamlit as st

from dara import matching, meets
from . import session
from .common import current_tier, go, rule


def _client():
    try:
        return session.get_client() if session.current_user() else None
    except Exception:  # noqa: BLE001
        return None


def _my_basics() -> dict:
    return (session.current_profile() or {}).get("basics") or {"name": "You"}


def render() -> None:
    st.markdown("##### Matches")
    st.title("Your *matches*.")
    rule()

    if st.session_state.get("match_open"):
        _chat(st.session_state["match_open"])
        return
    _list()


# ─── List ────────────────────────────────────────────────────────────
def _list() -> None:
    client, uid = _client(), session.user_id()

    if client and uid:
        reqs = meets.incoming_requests(client, uid)
        if reqs:
            st.subheader("Connect requests")
            for r in reqs:
                with st.container(border=True):
                    st.write(f"**{r['proposer_name']}** wants to connect.")
                    if r.get("message"):
                        st.caption(r["message"])

                    data = r.get("match_data") or {}
                    if data.get("score") is not None:
                        st.metric("Compatibility", f"{data.get('score')}%")
                    if data.get("verdict"):
                        st.write(data["verdict"])
                    transcript = data.get("transcript") or []
                    if transcript:
                        with st.expander(f"Read how your Daras talked · {len(transcript)} messages"):
                            for m in transcript:
                                who = r["proposer_name"] if m.get("speaker") == "me" else r["recipient_name"]
                                st.markdown(f"**{who}:** {m.get('content', '')}")

                    c1, c2 = st.columns(2)
                    if c1.button("Accept", key=f"acc_{r['id']}", type="primary", use_container_width=True):
                        meets.accept(client, r["id"])
                        st.rerun()
                    if c2.button("Decline", key=f"dec_{r['id']}", use_container_width=True):
                        meets.decline(client, r["id"])
                        st.rerun()

    cards = []
    if client and uid:
        for m in meets.matches(client, uid):
            _, oname = meets.other_party(m, uid)
            cards.append({"kind": "real", "id": m["id"], "name": oname})
    for cid, sm in (st.session_state.get("seed_matches") or {}).items():
        cards.append({
            "kind": "seed", "id": cid, "candidate": sm["candidate"],
            "name": (sm["candidate"].get("basics") or {}).get("name", "Someone"),
        })

    st.subheader("Matches")
    if not cards:
        st.caption("No matches yet. Find someone in the interview, then tap Connect.")
        return
    for c in cards:
        with st.container(border=True):
            st.write(f"**{c['name']}**" + ("  ·  _test persona_" if c["kind"] == "seed" else ""))
            if st.button("Open chat", key=f"open_{c['kind']}_{c['id']}", use_container_width=True):
                st.session_state["match_open"] = c
                st.rerun()


# ─── Chat ────────────────────────────────────────────────────────────
def _chat(c: dict) -> None:
    if st.button("← Matches"):
        st.session_state.pop("match_open", None)
        st.rerun()
    st.subheader(c["name"])

    if c["kind"] == "seed":
        _seed_chat(c)
    else:
        _real_chat(c)


def _seed_chat(c: dict) -> None:
    sm = (st.session_state.get("seed_matches") or {}).get(c["id"])
    if not sm:
        st.caption("This chat is no longer available.")
        return
    msgs = sm["messages"]
    # Lazy opener: let the persona say hello first.
    if not msgs:
        opener = matching.persona_reply(sm["candidate"], _my_basics(), [], current_tier())
        msgs.append({"sender": "them", "body": opener})

    for m in msgs:
        is_me = m["sender"] == "me"
        with st.chat_message("user" if is_me else "assistant", avatar=None if is_me else "✨"):
            st.write(m["body"])

    prompt = st.chat_input(f"Message {c['name']}…")
    if prompt:
        msgs.append({"sender": "me", "body": prompt})
        with st.spinner(f"{c['name']} is typing…"):
            reply = matching.persona_reply(sm["candidate"], _my_basics(), msgs, current_tier())
        msgs.append({"sender": "them", "body": reply})
        st.rerun()


def _real_chat(c: dict) -> None:
    client, uid = _client(), session.user_id()
    if not (client and uid):
        st.caption("Sign in to view this chat.")
        return
    for m in meets.list_messages(client, c["id"]):
        with st.chat_message("user" if m.get("sender_id") == uid else "assistant"):
            st.write(m.get("body", ""))

    prompt = st.chat_input(f"Message {c['name']}…")
    if prompt:
        meets.send_message(client, c["id"], uid, prompt)
        st.rerun()
    st.caption("They'll see this and reply when they're next online. Tap ← Matches and back to refresh.")

"""Browse mode: scroll through profiles yourself. When you like one, your Dara
takes over and has the conversation — then you can connect. (The fully-automatic
path is the interview → 'See who Dara found', where Dara also picks who.)

Vibrant redesign: big profile card (theme_components.browse_card) + match reveal.
"""

from __future__ import annotations

import streamlit as st

from dara import matching, meets
from . import session
from . import theme_components as tc
from .common import current_tier, go


def _client():
    try:
        return session.get_client() if session.current_user() else None
    except Exception:  # noqa: BLE001
        return None


def render() -> None:
    tc.hero(f'Find them {tc.grad_word("yourself")}.',
            "Scroll through people who fit what you're looking for. Like one, and your Dara talks first.",
            show_motif=False)

    client, me, uid = _client(), session.current_profile(), session.user_id()
    if not (client and me and uid):
        st.info("Sign in to browse people. Prefer to let Dara do it all? Start an interview from Home.")
        return

    if st.session_state.get("browse_result"):
        _result(me)
        return

    pool = st.session_state.get("browse_pool")
    if pool is None:
        with st.spinner("Finding people who fit what you're looking for…"):
            pool = matching.browse_candidates(client, me)
        st.session_state["browse_pool"] = pool
        st.session_state["browse_idx"] = 0

    idx = st.session_state.get("browse_idx", 0)
    if idx >= len(pool):
        st.success("That's everyone for now.")
        st.caption("Check back as more people join — or let Dara find someone for you via an interview.")
        cols = st.columns(2)
        if cols[0].button("Reload", use_container_width=True):
            st.session_state.pop("browse_pool", None)
            st.rerun()
        if cols[1].button("Let Dara find someone →", type="primary", use_container_width=True):
            go("interview")
        return

    cand = pool[idx]
    st.caption(f"{idx + 1} of {len(pool)}")
    _card(cand)

    is_x = current_tier() == "x"
    if st.button("✕  Pass", use_container_width=True):
        matching.record_pass(client, uid, cand.get("id"))
        st.session_state["browse_idx"] = idx + 1
        st.rerun()

    if is_x:
        # Top tier: connect straight away (no AI), or still let Dara vet them first.
        d1, d2 = st.columns(2)
        with d1:
            if st.button("♥  Connect directly", type="primary", use_container_width=True):
                _direct_connect(me, cand)
        with d2:
            if st.button("Let Dara talk first", use_container_width=True):
                _like(me, cand)
    else:
        if st.button("♥  Like — let Dara talk", type="primary", use_container_width=True):
            _like(me, cand)
        st.caption("Connecting without the AI conversation is part of the X plan.")


def _card(cand: dict) -> None:
    basics = cand.get("basics") or {}
    photos = cand.get("_photos") or []
    photo_url = photos[0].get("signed_url") if photos else None
    meta = "  ·  ".join(str(basics[k]) for k in ("age", "job", "nationality") if basics.get(k))
    prompts = [pr for pr in ((cand.get("profile") or {}).get("prompts") or []) if pr.get("answer")]
    tc.browse_card(
        name=basics.get("name", "Someone"),
        meta=meta,
        bio=basics.get("bio", ""),
        prompts=prompts,
        photo_url=photo_url,
        badge="✦ Test persona" if cand.get("_source") == "seed" else "",
    )


def _direct_connect(me: dict, cand: dict) -> None:
    """X-plan: connect with no AI conversation — Hinge-style. The recipient sees a
    plain connect request (no transcript) and can accept to match."""
    name = (cand.get("basics") or {}).get("name", "them")
    st.session_state["browse_idx"] = st.session_state.get("browse_idx", 0) + 1
    if cand.get("_source") == "real" and meets.is_real_user_id(cand.get("id")):
        res = meets.connect(_client(), me, cand)  # no match_data → no transcript
        if res.get("matched"):
            go("matches")
        else:
            st.toast(f"Connect request sent to {name}.")
            st.rerun()
        return
    # seed / test persona → auto-match
    sm = st.session_state.setdefault("seed_matches", {})
    cid = cand.get("id") or f"seed_{cand.get('username', 'x')}"
    sm.setdefault(cid, {"candidate": cand, "messages": []})
    go("matches")


def _like(me: dict, cand: dict) -> None:
    holder = st.empty()

    def _on_turn(i, total, convo):
        with holder.container():
            tc.mediation_orbs(a_name="Your Dara", b_name="Their Dara")
            st.caption(f"Your Daras are talking… {i}/{total}")
            for m in convo:
                is_me = m.get("speaker") == "me"
                with st.chat_message("user" if is_me else "assistant", avatar=None if is_me else "✨"):
                    st.write(m.get("content", ""))

    result = matching.run_match(
        me, cand, source=cand.get("_source", "real"),
        tier=current_tier(), client=_client(), on_turn=_on_turn,
    )
    holder.empty()
    st.session_state["browse_result"] = result
    st.session_state["browse_idx"] = st.session_state.get("browse_idx", 0) + 1
    st.rerun()


def _result(me: dict) -> None:
    match = st.session_state["browse_result"]
    cand = match.get("candidate") or {}
    cb = cand.get("basics") or {}
    name = cb.get("name", "them")
    photos = cand.get("_photos") or []
    photo_url = photos[0]["signed_url"] if (photos and photos[0].get("signed_url")) else None

    meta = "  ·  ".join(str(cb[k]) for k in ("age", "job", "nationality") if cb.get(k))
    tc.match_reveal(
        name=name, meta=meta, score=match.get("score", 0),
        verdict=match.get("verdict", ""), reasons=match.get("reasons", []),
        photo_url=photo_url,
    )

    transcript = match.get("transcript") or []
    if transcript:
        me_name = match.get("me_name", "You")
        with st.expander(f"Read how your Daras talked · {len(transcript)} messages"):
            for m in transcript:
                who = me_name if m.get("speaker") == "me" else name
                st.markdown(f"**{who}:** {m.get('content', '')}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Connect →", type="primary", use_container_width=True):
            _connect(me, match)
    with c2:
        if st.button("Keep browsing", use_container_width=True):
            st.session_state.pop("browse_result", None)
            st.rerun()


def _connect(me: dict, match: dict) -> None:
    cand = match.get("candidate") or {}
    name = (cand.get("basics") or {}).get("name", "them")
    match_data = {
        "transcript": match.get("transcript") or [], "score": match.get("score"),
        "verdict": match.get("verdict"), "reasons": match.get("reasons") or [],
    }
    if match.get("source") == "real" and meets.is_real_user_id(cand.get("id")):
        client = _client()
        res = meets.connect(client, me, cand, match_data=match_data)
        st.session_state.pop("browse_result", None)
        if res.get("matched"):
            go("matches")
        else:
            st.success(f"Connect request sent to {name}. You'll match if they accept.")
        return
    # seed / test persona → auto-match + AI persona chat
    sm = st.session_state.setdefault("seed_matches", {})
    cid = cand.get("id") or f"seed_{cand.get('username', 'x')}"
    sm.setdefault(cid, {"candidate": cand, "messages": []})
    st.session_state.pop("browse_result", None)
    go("matches")

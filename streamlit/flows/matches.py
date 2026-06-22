"""Matches: accept incoming connect requests, see your matches, and chat.

Real matches go through Supabase (meets + messages); the other person is a real
human who replies when they're online. Seed/test candidates have no human, so
they auto-match and reply in-voice via AI, kept in session state.
"""

from __future__ import annotations

import streamlit as st

from dara import matching, meets
from dara import conflicts
from dara import profile as profile_service
from dara import tiers
from . import session
from .common import current_tier, go, rule

_PER_SEARCH = 3  # matches generated per "Search" click (caps per-click cost)


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
    me = session.current_profile() or {}

    if client and uid:
        _search_section(client, me, uid)
        _suggestions_section(client, me, uid)

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
            oid, oname = meets.other_party(m, uid)
            cards.append({"kind": "real", "id": m["id"], "other_id": oid, "name": oname})
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
        basics, photo_url = _person_brief(client, c)
        with st.container(border=True):
            left, right = st.columns([1, 4])
            with left:
                if photo_url:
                    st.image(photo_url, use_container_width=True)
                else:
                    st.markdown("## ✨")
            with right:
                st.markdown(f"**{c['name']}**" + ("  ·  _test persona_" if c["kind"] == "seed" else ""))
                bits = _detail_bits(basics)
                if bits:
                    st.caption(bits)
            if st.button("Open chat", key=f"open_{c['kind']}_{c['id']}", use_container_width=True):
                st.session_state["match_open"] = c
                st.rerun()

    # Mediations live here too, so everything you're in flight on is in one place.
    if client and uid:
        sessions = conflicts.list_sessions(client, uid)
        if sessions:
            st.subheader("Mediations")
            for s in sessions:
                role = conflicts.role_of(s, uid)
                other = conflicts.name_of(s, conflicts.other_role(role))
                with st.container(border=True):
                    st.write(f"**{s['topic']}**  ·  with {other}")
                    st.caption(_med_status(s, uid))
                    if st.button("Open", key=f"medopen_{s['id']}", use_container_width=True):
                        st.session_state["med_open"] = s["id"]
                        go("mediation")


def _med_status(s: dict, uid: str) -> str:
    status = s.get("status")
    if status == "complete":
        return "Complete — open to read the takeaway"
    if status == "safety-stopped":
        return "Stopped for safety"
    if status == "declined":
        return "Declined"
    if status == "mediating":
        return "The Daras are mediating…"
    if status == "invited":
        return ("Invitation — needs your response"
                if conflicts.role_of(s, uid) == "invitee" else "Waiting for them to accept")
    mine_done = conflicts.side(s, conflicts.role_of(s, uid)).get("complete")
    return "Waiting for the other person's intake" if mine_done else "Your intake is open"


# ─── Person card helpers ─────────────────────────────────────────────
def _detail_bits(basics: dict) -> str:
    bits = []
    if basics.get("age"):
        bits.append(str(basics["age"]))
    if basics.get("job"):
        bits.append(basics["job"])
    if basics.get("nationality"):
        bits.append(basics["nationality"])
    return "  ·  ".join(bits)


def _person_brief(client, card: dict):
    """(basics, photo_url) for a match card — fetched for real users, taken from
    the candidate for seed personas (which have no photos)."""
    if card.get("kind") == "seed":
        cand = card.get("candidate") or {}
        photos = cand.get("_photos") or []
        return cand.get("basics") or {}, (photos[0].get("signed_url") if photos else None)
    basics, photo_url = {}, None
    oid = card.get("other_id")
    if client and oid:
        try:
            basics = (profile_service.get_profile(client, oid) or {}).get("basics") or {}
        except Exception:  # noqa: BLE001
            pass
        try:
            photos = profile_service.list_photos(client, oid)
            if photos:
                photo_url = photos[0].get("signed_url")
        except Exception:  # noqa: BLE001
            pass
    return basics, photo_url


def _person_header(name: str, basics: dict, photo_url) -> None:
    if photo_url:
        left, right = st.columns([1, 3])
        with left:
            st.image(photo_url, use_container_width=True)
        box = right
    else:
        box = st.container()
    with box:
        st.markdown(f"### {name}")
        bits = _detail_bits(basics)
        if bits:
            st.caption(bits)
        if basics.get("bio"):
            st.write(basics["bio"])


# ─── Find matches (tier-based daily search) ──────────────────────────
def _has_portrait(me: dict) -> bool:
    return bool(((me.get("profile") or {}).get("portrait") or {}).get("speech_notes"))


def _search_section(client, me, uid) -> None:
    tier = current_tier()
    limit = tiers.daily_match_limit(tier)
    used = profile_service.match_usage(client, uid)
    remaining = None if limit is None else max(0, limit - used)

    with st.container(border=True):
        st.subheader("Find matches")
        if not _has_portrait(me):
            st.caption("Do an interview first so Dara knows who to look for.")
            if st.button("Start an interview →", type="primary", use_container_width=True):
                go("interview")
            return
        if remaining is None:
            st.caption(f"{tier.upper()} plan · unlimited matches")
        else:
            st.caption(f"{tier.capitalize()} plan · {remaining} of {limit} left today")
        if remaining == 0:
            st.info("You've used today's matches. Check back tomorrow, or upgrade for more.")
        elif st.button("Search for matches", type="primary", use_container_width=True):
            _run_search(client, me, uid, tier, limit, used)

    if st.session_state.pop("auto_search", False) and _has_portrait(me) and remaining != 0:
        _run_search(client, me, uid, tier, limit, used)


def _run_search(client, me, uid, tier, limit, used) -> None:
    n = _PER_SEARCH if limit is None else min(_PER_SEARCH, max(0, limit - used))
    if n <= 0:
        return
    existing = profile_service.load_suggestions(client, uid)
    exclude = {x for x in ((s.get("candidate") or {}).get("id") for s in existing) if x}

    progress = st.progress(0.0, text="Dara is meeting people…")

    def _on_prog(i, total, _result):
        progress.progress(i / total, text=f"Dara met {i} of {total}…")

    try:
        results = matching.find_matches(
            conversation=None, tier=tier, client=client, me=me, n=n,
            exclude_ids=exclude, on_progress=_on_prog,
        )
    except Exception as e:  # noqa: BLE001
        progress.empty()
        st.error(f"Search failed: {e}")
        return
    progress.empty()
    if not results:
        st.info("No new people to meet right now — check back as more users join.")
        return
    profile_service.save_suggestions(client, uid, existing + [_suggestion_from_result(r) for r in results])
    profile_service.record_matches(client, uid, len(results))
    st.rerun()


def _suggestion_from_result(r: dict) -> dict:
    c = r.get("candidate") or {}
    return {
        "candidate": {
            "id": c.get("id"), "username": c.get("username"),
            "basics": c.get("basics") or {}, "is_seed": bool(c.get("is_seed")),
            "profile": {"portrait": (c.get("profile") or {}).get("portrait")},
        },
        "source": r.get("source"), "transcript": r.get("transcript") or [],
        "score": r.get("score"), "verdict": r.get("verdict"),
        "reasons": r.get("reasons") or [], "me_name": r.get("me_name", "You"),
    }


def _suggestions_section(client, me, uid) -> None:
    suggestions = profile_service.load_suggestions(client, uid)
    if not suggestions:
        return
    st.subheader("Dara found these")
    for idx, sug in enumerate(suggestions):
        c = sug.get("candidate") or {}
        basics = c.get("basics") or {}
        photo_url = None
        if sug.get("source") == "real" and meets.is_real_user_id(c.get("id")):
            try:
                photos = profile_service.list_photos(client, c["id"])
                if photos:
                    photo_url = photos[0].get("signed_url")
            except Exception:  # noqa: BLE001
                pass
        with st.container(border=True):
            left, right = st.columns([1, 4])
            with left:
                if photo_url:
                    st.image(photo_url, use_container_width=True)
                else:
                    st.markdown("## ✨")
            with right:
                tag = "  ·  _test persona_" if c.get("is_seed") else ""
                st.markdown(f"**{basics.get('name', 'Someone')}**{tag}")
                bits = _detail_bits(basics)
                if bits:
                    st.caption(bits)
                if sug.get("score") is not None:
                    st.caption(f"Compatibility {sug['score']}%")
            if sug.get("verdict"):
                st.write(sug["verdict"])
            transcript = sug.get("transcript") or []
            if transcript:
                me_name, their = sug.get("me_name", "You"), basics.get("name", "Them")
                with st.expander(f"Read how your Daras talked · {len(transcript)} messages"):
                    for m in transcript:
                        who = me_name if m.get("speaker") == "me" else their
                        st.markdown(f"**{who}:** {m.get('content', '')}")
            b1, b2 = st.columns(2)
            if b1.button("Connect →", key=f"sugc_{idx}", type="primary", use_container_width=True):
                _connect_suggestion(client, me, uid, suggestions, idx)
            if b2.button("Pass", key=f"sugp_{idx}", use_container_width=True):
                suggestions.pop(idx)
                profile_service.save_suggestions(client, uid, suggestions)
                st.rerun()


def _connect_suggestion(client, me, uid, suggestions, idx) -> None:
    sug = suggestions[idx]
    c = sug.get("candidate") or {}
    name = (c.get("basics") or {}).get("name", "them")
    if sug.get("source") == "real" and meets.is_real_user_id(c.get("id")):
        meets.connect(client, me, c, match_data={
            "transcript": sug.get("transcript") or [], "score": sug.get("score"),
            "verdict": sug.get("verdict"), "reasons": sug.get("reasons") or [],
        })
        st.toast(f"Connect request sent to {name}.")
    else:
        sm = st.session_state.setdefault("seed_matches", {})
        cid = c.get("id") or f"seed_{c.get('username', 'x')}"
        sm.setdefault(cid, {"candidate": c, "messages": []})
        st.toast(f"It's a match with {name}!")
    suggestions.pop(idx)
    profile_service.save_suggestions(client, uid, suggestions)
    st.rerun()


# ─── Chat ────────────────────────────────────────────────────────────
def _chat(c: dict) -> None:
    if st.button("← Matches"):
        st.session_state.pop("match_open", None)
        st.rerun()

    basics, photo_url = _person_brief(_client(), c)
    _person_header(c["name"], basics, photo_url)
    st.divider()

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

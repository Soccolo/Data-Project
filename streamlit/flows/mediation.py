"""Mediation: two real users, a Dara on each side.

Vibrant redesign: the two-Daras-meeting motif (theme_components.mediation_orbs)
and the mint takeaway card replace plain text; intake/chat stay native.
"""

from __future__ import annotations

import streamlit as st

from dara import call_ai, conflicts, schemas
from .common import current_tier, model_caption, rule
from . import session
from . import theme_components as tc

_MEDIATION_TURNS_EACH = 3  # 6 Dara-to-Dara messages


# ─── AI engine ───────────────────────────────────────────────────────
def _intake_reply(my_name: str, other_name: str, topic: str, messages, tier) -> str:
    system = (
        f"You are Dara, privately and confidentially helping {my_name} talk through "
        f"their side of a disagreement with {other_name}. The conflict was first "
        f"described as: '{topic}' — but that wording may be how the OTHER person framed "
        f"it, so do NOT assume it reflects {my_name}'s own view or that {my_name} is the "
        f"one who feels that way. Ask {my_name} how THEY see what's happening and how "
        "it's affecting them. Be warm; one short question at a time; help them name what "
        "they felt and what they actually need. Two sentences max. Only reflect back what "
        f"{my_name} actually says — never invent details they didn't give."
    )
    try:
        return call_ai(purpose="intake", system_prompt=system, tier=tier, history=messages)
    except Exception:  # noqa: BLE001
        return "Tell me a little more about what happened, and how it landed for you."


def _summarize_intake(my_name: str, other_name: str, topic: str, messages, tier) -> dict:
    convo = "\n".join(
        f"{'Dara' if m['role'] == 'assistant' else my_name}: {m['content']}" for m in messages
    )
    system = (
        f"Summarise {my_name}'s OWN side of their disagreement with {other_name} (first "
        f"described as '{topic}') from this private intake. Capture only what {my_name} "
        "actually said — never infer unstated specifics (a field of study, a job title, a "
        "diagnosis, a reason). Return JSON: summary (1-2 sentences in their own framing), "
        "needs (their underlying needs), safe (false if ANY sign of abuse, violence, "
        "coercion, or fear), safety_reason (one sentence if unsafe)."
    )
    try:
        return schemas.normalize_intake(call_ai(
            purpose="intake", system_prompt=system, tier=tier,
            user_text=convo, schema=schemas.INTAKE, max_tokens=400,
        ))
    except Exception:  # noqa: BLE001
        return {"summary": "", "needs": [], "safe": True, "safety_reason": ""}


def _run_mediation(topic, a_name, a_summary, b_name, b_summary, tier, turns_each=_MEDIATION_TURNS_EACH):
    convo = []  # [{"speaker": "inviter"|"invitee", "content": str}]
    sides = {"inviter": (a_name, a_summary, b_name), "invitee": (b_name, b_summary, a_name)}
    order = ["inviter", "invitee"]
    for turn in range(turns_each * 2):
        role = order[turn % 2]
        my_name, my_sum, their_name = sides[role]
        lines = "\n".join(
            f"{a_name if c['speaker'] == 'inviter' else b_name}'s Dara: {c['content']}" for c in convo
        ) or "[You speak first — open warmly.]"
        system = (
            f"You are {my_name}'s Dara, mediating with {their_name}'s Dara about: '{topic}'. "
            f"You represent {my_name}, whose side is: {my_sum or 'not specified'}. "
            "Speak FOR your person but constructively — surface their real need without "
            "blame, acknowledge the other side fairly, and move toward one small concrete "
            "repair. Calm and warm, 1-2 sentences. Invent nothing beyond the summary. "
            'Output JSON: {"message": "your next line"}.\n\n'
            f"Conversation so far:\n{lines}"
        )
        try:
            msg = schemas.normalize_proxy(call_ai(
                purpose="mediation", system_prompt=system, tier=tier,
                user_text="Your next line.", schema=schemas.PROXY, max_tokens=200,
            ))
        except Exception:  # noqa: BLE001
            msg = ""
        convo.append({"speaker": role, "content": msg or "…"})
    return convo


def _takeaway(my_name, other_name, topic, my_summary, their_summary, transcript, tier) -> str:
    convo = "\n".join(c.get("content", "") for c in transcript)
    system = (
        f"Write a short, warm takeaway (2-3 sentences) for {my_name} after Dara mediated "
        f"their conflict with {other_name} about '{topic}'. Say what the friction was "
        f"really about underneath, and one concrete thing {my_name} could ask for or do "
        "next. No blame, no taking sides."
    )
    user = f"{my_name}'s side: {my_summary}\n{other_name}'s side: {their_summary}\nMediation:\n{convo}"
    try:
        return call_ai(purpose="takeaway", system_prompt=system, tier=tier, user_text=user, max_tokens=300)
    except Exception:  # noqa: BLE001
        return ""


# ─── UI ──────────────────────────────────────────────────────────────
def _client():
    try:
        return session.get_client() if session.current_user() else None
    except Exception:  # noqa: BLE001
        return None


def render() -> None:
    st.markdown("##### Mediate a conflict")
    st.title("Let's talk it *through*.")
    rule()
    model_caption("mediation")

    client, me, uid = _client(), session.current_profile(), session.user_id()
    if not (client and me and uid):
        st.info("Mediation happens between two registered users. Sign in to start one or accept an invitation.")
        return

    sid = st.session_state.get("med_open")
    if sid:
        _session_view(client, me, uid, sid)
    else:
        _list_view(client, me, uid)


def _list_view(client, me, uid) -> None:
    with st.container(border=True):
        st.subheader("Start a mediation")
        with st.form("med_new"):
            username = st.text_input("Their username", placeholder="their_username",
                                     help="The other person needs a Dara account.")
            topic = st.text_input("What's the conflict about?", placeholder="e.g. last-minute changes to plans")
            sent = st.form_submit_button("Send invite →", use_container_width=True)
        if sent:
            if not username.strip() or not topic.strip():
                st.error("Add their username and a topic.")
            else:
                row, err = conflicts.create_session(client, me, username, topic)
                if err:
                    st.error(err)
                else:
                    st.session_state["med_open"] = row["id"]
                    st.rerun()

    sessions = conflicts.list_sessions(client, uid)
    invites = [s for s in sessions if s["status"] == "invited" and s["invitee_id"] == uid]
    if invites:
        st.subheader("Invitations")
        for s in invites:
            with st.container(border=True):
                st.write(f"**{s['inviter_name']}** invited you to mediate: _{s['topic']}_")
                c1, c2 = st.columns(2)
                if c1.button("Accept", key=f"ma_{s['id']}", type="primary", use_container_width=True):
                    conflicts.respond_invite(client, s["id"], True)
                    st.session_state["med_open"] = s["id"]
                    st.rerun()
                if c2.button("Decline", key=f"md_{s['id']}", use_container_width=True):
                    conflicts.respond_invite(client, s["id"], False)
                    st.rerun()

    active = [s for s in sessions if s not in invites]
    st.subheader("Your mediations")
    if not active:
        st.caption("Nothing yet. Invite someone above to start one.")
    for s in active:
        with st.container(border=True):
            other = s["invitee_name"] if s["inviter_id"] == uid else s["inviter_name"]
            st.write(f"**{s['topic']}**  ·  with {other}")
            st.caption(_status_label(s, uid))
            if st.button("Open", key=f"mo_{s['id']}", use_container_width=True):
                st.session_state["med_open"] = s["id"]
                st.rerun()


def _status_label(s, uid) -> str:
    role = conflicts.role_of(s, uid)
    status = s["status"]
    if status == "declined":
        return "Declined"
    if status == "safety-stopped":
        return "Stopped for safety"
    if status == "invited":
        return "Waiting for them to accept" if role == "inviter" else "Invitation — needs your response"
    if status == "complete":
        return "Complete"
    if status == "mediating":
        return "The Daras are mediating…"
    # intake
    mine = conflicts.side(s, role).get("complete")
    return "Waiting for the other person's intake" if mine else "Your intake is open"


def _session_view(client, me, uid, sid) -> None:
    s = conflicts.get_session(client, sid)
    if st.button("← Mediations"):
        st.session_state.pop("med_open", None)
        st.rerun()
    if not s:
        st.caption("This mediation isn't available.")
        return

    role = conflicts.role_of(s, uid)
    other = conflicts.other_role(role)
    st.caption(f"Topic: **{s['topic']}**  ·  with {conflicts.name_of(s, other)}")
    status = s["status"]

    if status == "declined":
        st.info("This invitation was declined.")
        return
    if status == "safety-stopped":
        st.error(f"This mediation was stopped for safety: {s.get('safety_reason', '')}")
        st.caption("This isn't something to work through with an AI. Please consider reaching "
                   "out to someone you trust or a professional who can help.")
        return
    if status == "invited":
        if role == "invitee":
            st.write(f"**{s['inviter_name']}** wants to mediate this with you.")
            c1, c2 = st.columns(2)
            if c1.button("Accept", type="primary", use_container_width=True):
                conflicts.respond_invite(client, sid, True)
                st.rerun()
            if c2.button("Decline", use_container_width=True):
                conflicts.respond_invite(client, sid, False)
                st.rerun()
        else:
            st.info(f"Waiting for {s['invitee_name']} to accept your invitation.")
        return

    if status in ("mediating", "complete"):
        _render_results(s, role)
        return

    # status == 'intake'
    if not conflicts.side(s, role).get("complete"):
        _intake(client, s, role)
        return

    if conflicts.both_intakes_complete(s):
        _run_and_save(client, s)
        st.rerun()
    else:
        st.success(f"Your side is in. Waiting for {conflicts.name_of(s, other)} to finish theirs — "
                   "check back soon.")


def _intake(client, s, role) -> None:
    my_name = conflicts.name_of(s, role)
    other_name = conflicts.name_of(s, conflicts.other_role(role))

    # The two-Daras motif + a private-intake note set the scene.
    tc.mediation_orbs(a_name=f"{other_name}'s Dara", b_name=f"{my_name}'s Dara", topic=s["topic"])
    tc.info_note(
        "<strong>This part is private</strong> — only you and your Dara. When you're ready, "
        "Dara shares a short summary with the other person's Dara, never your raw words.",
        accent=tc.MINT,
    )

    msgs = conflicts.side(s, role).get("messages") or []
    if not msgs:
        opener = _intake_reply(my_name, other_name, s["topic"], [], current_tier())
        s = conflicts.append_intake_message(client, s, role, "assistant", opener)
        msgs = conflicts.side(s, role).get("messages")

    for m in msgs:
        is_dara = m["role"] == "assistant"
        with st.chat_message("assistant" if is_dara else "user", avatar="✨" if is_dara else None):
            st.write(m["content"])

    user_turns = sum(1 for m in msgs if m["role"] == "user")
    if user_turns >= 2:
        if st.button("I've said my piece — share my side →", type="primary", use_container_width=True):
            with st.spinner("Dara is summarising your side…"):
                summ = _summarize_intake(my_name, other_name, s["topic"], msgs, current_tier())
            text = summ["summary"]
            if summ.get("needs"):
                text += " (Underlying needs: " + ", ".join(summ["needs"]) + ".)"
            conflicts.complete_intake(client, s, role, text, summ["safe"], summ.get("safety_reason", ""))
            st.rerun()

    prompt = st.chat_input("Tell Dara…")
    if prompt:
        # Capture the updated session so the assistant append builds on the
        # message we just added — otherwise the second write overwrites the user's.
        s = conflicts.append_intake_message(client, s, role, "user", prompt)
        reply = _intake_reply(my_name, other_name, s["topic"],
                              conflicts.side(s, role).get("messages"), current_tier())
        conflicts.append_intake_message(client, s, role, "assistant", reply)
        st.rerun()


def _run_and_save(client, s) -> None:
    conflicts.save_mediation(client, s["id"], [])  # flip to 'mediating' so the other side doesn't re-run
    inv, ine = conflicts.side(s, "inviter"), conflicts.side(s, "invitee")
    with st.spinner("The two Daras are mediating…"):
        transcript = _run_mediation(
            s["topic"], s["inviter_name"], inv.get("summary", ""),
            s["invitee_name"], ine.get("summary", ""), current_tier(),
        )
        conflicts.save_mediation(client, s["id"], transcript)
        t_inv = _takeaway(s["inviter_name"], s["invitee_name"], s["topic"],
                          inv.get("summary", ""), ine.get("summary", ""), transcript, current_tier())
        t_ine = _takeaway(s["invitee_name"], s["inviter_name"], s["topic"],
                          ine.get("summary", ""), inv.get("summary", ""), transcript, current_tier())
        conflicts.save_takeaways(client, s["id"], t_inv, t_ine)


def _render_results(s, role) -> None:
    transcript = (s.get("mediation") or {}).get("messages") or []
    my_take = (s.get("takeaways") or {}).get(role)

    if s["status"] == "mediating" and not my_take:
        tc.mediation_orbs(a_name=f"{s['inviter_name']}'s Dara", b_name=f"{s['invitee_name']}'s Dara", topic=s["topic"])
        st.info("The two Daras are mediating now — check back in a moment "
                "(tap ← Mediations and reopen to refresh).")
        return

    tc.mediation_orbs(a_name=f"{s['inviter_name']}'s Dara", b_name=f"{s['invitee_name']}'s Dara", topic=s["topic"])
    st.subheader("How the Daras talked it through")
    for c in transcript:
        speaker = s["inviter_name"] if c.get("speaker") == "inviter" else s["invitee_name"]
        with st.chat_message("assistant", avatar="✨"):
            st.markdown(f"**{speaker}'s Dara:** {c.get('content', '')}")

    if my_take:
        tc.takeaway(my_take)

"""Mediation flow: prescreen → Dara-to-Dara mediation → per-party takeaways.

A single-session demo of the couples flow. In the full app each party talks to
their own Dara privately and the two Daras mediate; here we collect both
perspectives in one place so the whole arc is visible at once.
"""

from __future__ import annotations

import streamlit as st

from dara import call_ai
from dara import schemas
from .common import current_tier, model_caption

_SYSTEM_MEDIATION = (
    "You are mediating between two partners. Return JSON with `messages`: an "
    "array of 3 short mediator messages that (1) reflect both sides fairly, "
    "(2) name the underlying need beneath each position, and (3) suggest one "
    "small, concrete repair. Be even-handed and warm; no blame."
)
_SYSTEM_PRESCREEN = (
    "Classify whether this relationship conflict is safe and appropriate to "
    "mediate with an AI. Return JSON: safe (boolean) and reason (one sentence). "
    "Flag as unsafe anything involving abuse, violence, or coercion."
)

_SAMPLE_A = "Plans got changed last minute again and I found out by text. I felt like an afterthought."
_SAMPLE_B = "I shifted things because work blew up. I thought I was handling it so they wouldn't have to."


def render() -> None:
    st.markdown("##### Mediate a conflict")
    st.title("Let's talk it *through*.")
    model_caption("mediation")

    if st.session_state.get("med_result"):
        _render_result(st.session_state["med_result"])
        return

    with st.form("mediation_setup"):
        c1, c2 = st.columns(2)
        name_a = c1.text_input("Your name", value="Alex")
        name_b = c2.text_input("Your partner's name", value="Sam")
        topic = st.text_input("What's the conflict about?", value="Last-minute changes to plans")
        persp_a = st.text_area(f"{name_a or 'Your'} side of it", value=_SAMPLE_A, height=90)
        persp_b = st.text_area(f"{name_b or 'Their'} side of it", value=_SAMPLE_B, height=90)
        submitted = st.form_submit_button("Run mediation →", use_container_width=True)

    if submitted:
        with st.spinner("Dara is hearing both sides…"):
            result = _run(name_a or "Partner A", name_b or "Partner B", topic, persp_a, persp_b)
        st.session_state["med_result"] = result
        st.rerun()


def _run(name_a: str, name_b: str, topic: str, persp_a: str, persp_b: str) -> dict:
    tier = current_tier()
    names = {"a": name_a, "b": name_b}
    context = (
        f"Topic: {topic}\n\n{name_a}'s side: {persp_a}\n{name_b}'s side: {persp_b}"
    )
    try:
        # 1) Safety prescreen.
        prescreen = schemas.normalize_prescreen(call_ai(
            purpose="prescreen", system_prompt=_SYSTEM_PRESCREEN, tier=tier,
            user_text=topic, schema=schemas.PRESCREEN, max_tokens=200,
        ))
        if not prescreen["safe"]:
            return {"names": names, "topic": topic, "prescreen": prescreen,
                    "transcript": [], "takeaway_a": "", "takeaway_b": ""}

        # 2) Dara-to-Dara mediation — one structured call returning a few turns.
        transcript = schemas.normalize_messages(call_ai(
            purpose="mediation", system_prompt=_SYSTEM_MEDIATION, tier=tier,
            user_text=context, schema=schemas.MEDIATION, names=names, max_tokens=900,
        ))

        # 3) A private takeaway for each party.
        takeaway_a = call_ai(
            purpose="takeaway", tier=tier, names={"self": name_a, "other": name_b},
            user_text=context, max_tokens=400,
            system_prompt=f"Write a short, warm takeaway (2-3 sentences) for {name_a} about "
                          f"this conflict with {name_b}: what the friction was really about, "
                          f"and one concrete thing to ask for.",
        )
        takeaway_b = call_ai(
            purpose="takeaway", tier=tier, names={"self": name_b, "other": name_a},
            user_text=context, max_tokens=400,
            system_prompt=f"Write a short, warm takeaway (2-3 sentences) for {name_b} about "
                          f"this conflict with {name_a}: what the friction was really about, "
                          f"and one concrete thing to ask for.",
        )
    except Exception as e:  # noqa: BLE001
        return {"names": names, "topic": topic, "error": str(e),
                "prescreen": {}, "transcript": [], "takeaway_a": "", "takeaway_b": ""}

    return {"names": names, "topic": topic, "prescreen": prescreen,
            "transcript": transcript, "takeaway_a": takeaway_a, "takeaway_b": takeaway_b}


def _render_result(r: dict) -> None:
    name_a, name_b = r["names"]["a"], r["names"]["b"]
    st.caption(f"Topic: **{r['topic']}**")

    if r.get("error"):
        st.error(f"Mediation failed: {r['error']}")
        if st.button("Try again", use_container_width=True):
            st.session_state.pop("med_result", None)
            st.rerun()
        return

    if r["prescreen"].get("safe", True):
        st.success("Safety check passed — proceeding to mediation.")
    else:
        st.error(f"Safety stop: {r['prescreen'].get('reason', '')}")
        if st.button("Start over", use_container_width=True):
            st.session_state.pop("med_result", None)
            st.rerun()
        return

    st.subheader("Mediation")
    for line in r["transcript"]:
        with st.chat_message("assistant", avatar="✨"):
            st.write(line)

    st.subheader("Takeaways")
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown(f"**For {name_a}**")
            st.write(r["takeaway_a"])
    with c2:
        with st.container(border=True):
            st.markdown(f"**For {name_b}**")
            st.write(r["takeaway_b"])

    if st.button("Run another", use_container_width=True):
        st.session_state.pop("med_result", None)
        st.rerun()

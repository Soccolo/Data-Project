"""First-run profile builder — a three-step wizard completed before the app:
  1. About you   — identity, description, job
  2. Preferences — who you're looking for
  3. Photos      — upload a few (optional)

Only finishing step 3 flips the ``onboarded`` flag, so the router keeps the
user here until they're done. Earlier steps persist as they go.

Vibrant redesign: orb hero + themed step pills; forms stay native.
"""

from __future__ import annotations

import re

import streamlit as st

from dara import prefs as prefs_mod
from dara import profile as profile_service
from . import session
from . import theme_components as tc
from .common import steps

_KINDS = {
    "dating": "Dating — find someone new",
    "couples": "Couples — work through a conflict",
    "both": "Both",
}
_STEPS = ["About you", "Preferences", "Photos"]


def render() -> None:
    tc.hero(
        f'Build your {tc.grad_word("profile")}.',
        "A few details so Dara knows who it's speaking for, and who to look for.",
        show_motif=False,
    )

    step = st.session_state.setdefault("ob_step", 1)
    steps(step, _STEPS)

    if step == 1:
        _step_about()
    elif step == 2:
        _step_preferences()
    else:
        _step_photos()


# ─── Step 1: about you ───────────────────────────────────────────────
def _step_about() -> None:
    prof = session.current_profile() or {}
    basics = prof.get("basics") or {}

    with st.form("ob_about"):
        display_name = st.text_input("Your name", value=basics.get("name", ""), placeholder="Alex")
        username = st.text_input(
            "Username",
            value="" if str(prof.get("username", "")).startswith("user_") else prof.get("username", ""),
            placeholder="alex",
            help="Lowercase letters, numbers, and underscores.",
        )
        kind_label = st.radio(
            "What brings you here?", list(_KINDS.values()), index=_kind_index(prof.get("kind", "dating")),
        )

        col_g, col_o = st.columns(2)
        with col_g:
            gender = st.selectbox(
                "Your gender", prefs_mod.GENDERS,
                index=_idx(prefs_mod.GENDERS, basics.get("gender")),
            )
        with col_o:
            orientation = st.selectbox(
                "Sexuality", prefs_mod.ORIENTATIONS,
                index=_idx(prefs_mod.ORIENTATIONS, basics.get("orientation"), default=len(prefs_mod.ORIENTATIONS) - 1),
            )

        col_age, col_nat = st.columns(2)
        with col_age:
            age = st.number_input(
                "Age", min_value=prefs_mod.MIN_AGE, max_value=120,
                value=int(basics.get("age") or 27), step=1,
                help="You must be 18 or older to use Dara.",
            )
        with col_nat:
            nationality = st.text_input("Nationality", value=basics.get("nationality", ""), placeholder="e.g. Romanian")

        description = st.text_area(
            "Your description", value=basics.get("bio", ""), height=110,
            placeholder="A couple of sentences on who you are and what you're looking for.",
        )
        col_job, col_h = st.columns(2)
        with col_job:
            job = st.text_input("Job", value=basics.get("job", ""), placeholder="Architect")
        with col_h:
            height = st.number_input(
                "Height (cm)", min_value=120, max_value=230,
                value=int(basics.get("height_cm") or 170), step=1,
            )
        submitted = st.form_submit_button("Continue to preferences →", use_container_width=True)

    if not submitted:
        return

    display_name = display_name.strip()
    username = username.strip().lower()
    kind = next(k for k, v in _KINDS.items() if v == kind_label)

    if not display_name:
        st.error("Add your name so Dara knows what to call you.")
        return
    if not _valid_username(username):
        st.error("Username must be 3–20 characters: lowercase letters, numbers, or underscores.")
        return
    if int(age) < prefs_mod.MIN_AGE:
        st.error("You must be at least 18 to use Dara.")
        return

    client = session.get_client()
    uid = session.user_id()
    if not profile_service.username_available(client, username, exclude_user_id=uid):
        st.error("That username is taken — try another.")
        return

    new_basics = {
        **basics, "name": display_name, "gender": gender, "orientation": orientation,
        "age": int(age), "nationality": nationality.strip(), "bio": description.strip(),
        "job": job.strip(), "height_cm": int(height),
    }
    try:
        profile_service.update_profile(client, uid, username=username, kind=kind, basics=new_basics)
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't save your details: {e}")
        return

    session.refresh_profile()
    st.session_state["ob_step"] = 2
    st.rerun()


# ─── Step 2: preferences ─────────────────────────────────────────────
def _step_preferences() -> None:
    prof = session.current_profile() or {}
    p = {**prefs_mod.default_preferences(), **((prof.get("profile") or {}).get("preferences") or {})}

    st.write("Who should Dara look for? These shape your matches.")
    with st.form("ob_prefs"):
        interested_in = st.multiselect(
            "Interested in", prefs_mod.INTERESTED_IN,
            default=[x for x in p["interested_in"] if x in prefs_mod.INTERESTED_IN],
        )
        age_range = st.slider(
            "Age range", prefs_mod.MIN_AGE, 99,
            (max(prefs_mod.MIN_AGE, int(p["age_min"])), max(prefs_mod.MIN_AGE, int(p["age_max"]))),
        )
        height_range = st.slider(
            "Height range (cm)", 120, 230, (int(p["height_min_cm"]), int(p["height_max_cm"])),
        )
        intent = st.selectbox("Looking for", prefs_mod.INTENTS, index=_idx(prefs_mod.INTENTS, p["intent"]))
        nationalities = st.text_input(
            "Preferred nationalities (optional)", value=", ".join(p["nationalities"]),
            help="A soft preference Dara weighs — not a hard filter.",
        )
        dealbreakers = st.text_area("Dealbreakers (optional)", value=p["dealbreakers"], height=70)
        physical_prefs = st.text_area(
            "Physical preferences (optional)", value=p.get("physical_prefs", ""), height=70,
            help="e.g. 'long hair, taller than me'. Dara checks this against photos — visible "
                 "traits only, never anything protected.",
        )
        submitted = st.form_submit_button("Continue to photos →", use_container_width=True)

    back = st.button("← Back")
    if back:
        st.session_state["ob_step"] = 1
        st.rerun()

    if not submitted:
        return

    new_prefs = {
        "interested_in": interested_in,
        "age_min": age_range[0], "age_max": age_range[1],
        "height_min_cm": height_range[0], "height_max_cm": height_range[1],
        "nationalities": [n.strip() for n in nationalities.split(",") if n.strip()],
        "intent": intent,
        "dealbreakers": dealbreakers.strip(),
        "physical_prefs": physical_prefs.strip(),
    }
    profile_json = {**(prof.get("profile") or {}), "preferences": new_prefs}
    try:
        profile_service.update_profile(session.get_client(), session.user_id(), profile=profile_json)
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't save your preferences: {e}")
        return

    session.refresh_profile()
    st.session_state["ob_step"] = 3
    st.rerun()


# ─── Step 3: photos ──────────────────────────────────────────────────
def _step_photos() -> None:
    client = session.get_client()
    uid = session.user_id()

    st.write("Add a few photos so your match can put a face to the conversation. You can change these anytime.")

    try:
        photos = profile_service.list_photos(client, uid)
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't load your photos: {e}")
        photos = []

    if photos:
        cols = st.columns(3)
        for i, ph in enumerate(photos):
            with cols[i % 3]:
                if ph.get("signed_url"):
                    st.image(ph["signed_url"], use_container_width=True)
                if st.button("Remove", key=f"ob_del_{ph['id']}", use_container_width=True):
                    try:
                        profile_service.delete_photo(client, uid, ph["id"], ph["storage_path"])
                        st.rerun()
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Couldn't remove that photo: {e}")
    else:
        st.caption("No photos yet.")

    upload = st.file_uploader("Add a photo", type=["jpg", "jpeg", "png", "webp"])
    if upload is not None and st.button("Upload photo", use_container_width=True):
        try:
            profile_service.upload_photo(
                client, uid, upload.getvalue(),
                media_type=upload.type or "image/jpeg", position=len(photos),
            )
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"Upload failed: {e}")

    st.divider()
    back, finish = st.columns([1, 2])
    with back:
        if st.button("← Back", use_container_width=True):
            st.session_state["ob_step"] = 2
            st.rerun()
    with finish:
        label = "Finish — meet Dara →" if photos else "Skip photos — meet Dara →"
        if st.button(label, type="primary", use_container_width=True):
            try:
                profile_service.mark_onboarded(client, uid, session.current_profile())
            except Exception as e:  # noqa: BLE001
                st.error(f"Couldn't finish setup: {e}")
                return
            session.refresh_profile()
            st.session_state.pop("ob_step", None)
            st.rerun()


# ─── helpers ─────────────────────────────────────────────────────────
def _kind_index(kind: str) -> int:
    keys = list(_KINDS.keys())
    return keys.index(kind) if kind in keys else 0


def _idx(options: list, value, default: int = 0) -> int:
    return options.index(value) if value in options else default


def _valid_username(u: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_]{3,20}", u))

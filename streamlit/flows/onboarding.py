"""First-run profile builder.

A two-step wizard the user completes before reaching the app:
  1. About you — name, username, what they're here for, description, job, height
  2. Photos — upload a few (optional)

Only when step 2 is finished do we flip the ``onboarded`` flag, so the app
router keeps the user in the wizard until they're done. Step 1 persists as the
user goes, so a mid-flow refresh recovers their answers.
"""

from __future__ import annotations

import re

import streamlit as st

from dara import profile as profile_service
from . import session
from .common import WORDMARK, rule, steps

_KINDS = {
    "dating": "Dating — find someone new",
    "couples": "Couples — work through a conflict",
    "both": "Both",
}
_STEPS = ["About you", "Photos"]


def render() -> None:
    st.markdown(f"##### {WORDMARK}")
    st.title("Build your *profile*.")
    rule()
    st.write("A few details so Dara knows who it's speaking for. This is what your match sees.")

    step = st.session_state.setdefault("ob_step", 1)
    steps(step, _STEPS)

    if step == 1:
        _step_about()
    else:
        _step_photos()


# ─── Step 1: about you ───────────────────────────────────────────────
def _step_about() -> None:
    prof = session.current_profile() or {}
    basics = prof.get("basics") or {}

    with st.form("ob_about"):
        display_name = st.text_input("Your name", value=basics.get("name", ""), placeholder="Alex")
        username = st.text_input(
            "Username", value=prof.get("username", "") if not str(prof.get("username", "")).startswith("user_") else "",
            placeholder="alex",
            help="Lowercase letters, numbers, and underscores. People can invite you by this.",
        )
        kind_label = st.radio(
            "What brings you here?", list(_KINDS.values()),
            index=_kind_index(prof.get("kind", "dating")),
        )
        description = st.text_area(
            "Your description", value=basics.get("bio", ""), height=120,
            placeholder="A couple of sentences on who you are and what you're looking for.",
        )
        col_job, col_height = st.columns(2)
        with col_job:
            job = st.text_input("Job", value=basics.get("job", ""), placeholder="Architect")
        with col_height:
            height = st.number_input(
                "Height (cm)", min_value=120, max_value=230,
                value=int(basics.get("height_cm") or 170), step=1,
            )
        submitted = st.form_submit_button("Continue to photos →", use_container_width=True)

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

    client = session.get_client()
    uid = session.user_id()
    if not profile_service.username_available(client, username, exclude_user_id=uid):
        st.error("That username is taken — try another.")
        return

    new_basics = {
        **basics,
        "name": display_name,
        "bio": description.strip(),
        "job": job.strip(),
        "height_cm": int(height),
    }
    try:
        profile_service.update_profile(
            client, uid, username=username, kind=kind, basics=new_basics,
        )
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't save your details: {e}")
        return

    session.refresh_profile()
    st.session_state["ob_step"] = 2
    st.rerun()


# ─── Step 2: photos ──────────────────────────────────────────────────
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
        for i, p in enumerate(photos):
            with cols[i % 3]:
                if p.get("signed_url"):
                    st.image(p["signed_url"], use_container_width=True)
                if st.button("Remove", key=f"ob_del_{p['id']}", use_container_width=True):
                    try:
                        profile_service.delete_photo(client, uid, p["id"], p["storage_path"])
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
            st.session_state["ob_step"] = 1
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


def _valid_username(u: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_]{3,20}", u))

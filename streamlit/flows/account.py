"""Account page: profile, photos, plan/billing, settings, and account deletion."""

from __future__ import annotations

import streamlit as st

from dara import auth as auth_service
from dara import prefs as prefs_mod
from dara import profile as profile_service
from dara.tiers import TIER_INFO, TIER_ORDER
from . import session
from .common import go, render_portrait


def render() -> None:
    prof = session.current_profile() or {}
    st.markdown("##### Account")
    st.title(f"@{prof.get('username', '—')}")

    tab_profile, tab_prefs, tab_insights, tab_photos, tab_plan, tab_settings = st.tabs(
        ["Profile", "Preferences", "What Dara learned", "Photos", "Plan", "Settings"]
    )
    with tab_profile:
        _profile(prof)
    with tab_prefs:
        _preferences(prof)
    with tab_insights:
        _insights(prof)
    with tab_photos:
        _photos()
    with tab_plan:
        _plan(prof)
    with tab_settings:
        _settings(prof)


# ─── Profile ─────────────────────────────────────────────────────────
_KINDS = {"dating": "Dating", "couples": "Couples", "both": "Both"}


def _profile(prof: dict) -> None:
    basics = prof.get("basics") or {}
    with st.form("edit_profile"):
        name = st.text_input("Display name", value=basics.get("name", ""))
        username = st.text_input("Username", value=prof.get("username", ""))
        kinds = list(_KINDS.keys())
        cur_kind = prof.get("kind", "dating")
        kind = st.selectbox(
            "Here for", kinds,
            index=kinds.index(cur_kind) if cur_kind in kinds else 0,
            format_func=lambda k: _KINDS[k],
        )
        col_g, col_o = st.columns(2)
        with col_g:
            gender = st.selectbox(
                "Gender", prefs_mod.GENDERS, index=_idx(prefs_mod.GENDERS, basics.get("gender")),
            )
        with col_o:
            orientation = st.selectbox(
                "Sexuality", prefs_mod.ORIENTATIONS,
                index=_idx(prefs_mod.ORIENTATIONS, basics.get("orientation"), len(prefs_mod.ORIENTATIONS) - 1),
            )
        col_age, col_nat = st.columns(2)
        with col_age:
            age = st.number_input(
                "Age", min_value=prefs_mod.MIN_AGE, max_value=120,
                value=int(basics.get("age") or 27), step=1,
            )
        with col_nat:
            nationality = st.text_input("Nationality", value=basics.get("nationality", ""))
        bio = st.text_area("Description", value=basics.get("bio", ""), height=100)
        col_job, col_height = st.columns(2)
        with col_job:
            job = st.text_input("Job", value=basics.get("job", ""))
        with col_height:
            height = st.number_input(
                "Height (cm)", min_value=120, max_value=230,
                value=int(basics.get("height_cm") or 170), step=1,
            )
        submitted = st.form_submit_button("Save changes", use_container_width=True)

    if submitted:
        username = username.strip().lower()
        client = session.get_client()
        uid = session.user_id()
        if username != prof.get("username") and not profile_service.username_available(
            client, username, exclude_user_id=uid
        ):
            st.error("That username is taken.")
            return
        new_basics = {
            **basics, "name": name.strip(), "gender": gender, "orientation": orientation,
            "age": int(age), "nationality": nationality.strip(), "bio": bio.strip(),
            "job": job.strip(), "height_cm": int(height),
        }
        try:
            profile_service.update_profile(
                client, uid, username=username, kind=kind, basics=new_basics
            )
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't save: {e}")
            return
        session.refresh_profile()
        st.success("Saved.")

    _prompts_editor(prof)


# ─── Profile prompts (Hinge-style) ───────────────────────────────────
def _prompts_editor(prof: dict) -> None:
    st.divider()
    st.subheader("Profile prompts")
    st.caption("Answer a few so people browsing can get a feel for you. Leave the prompt on "
               "“—” to skip a slot.")

    existing = {p.get("prompt"): p.get("answer", "")
                for p in ((prof.get("profile") or {}).get("prompts") or [])}
    options = ["—"] + prefs_mod.PROMPTS
    prior = [p.get("prompt") for p in ((prof.get("profile") or {}).get("prompts") or [])]

    with st.form("edit_prompts"):
        chosen = []
        for i in range(3):
            cur = prior[i] if i < len(prior) else "—"
            prompt = st.selectbox(
                f"Prompt {i + 1}", options,
                index=options.index(cur) if cur in options else 0, key=f"prompt_sel_{i}",
            )
            answer = st.text_input(
                "Your answer", value=existing.get(prompt, ""), key=f"prompt_ans_{i}",
                label_visibility="collapsed", placeholder="Your answer…",
            )
            if prompt != "—" and answer.strip():
                chosen.append({"prompt": prompt, "answer": answer.strip()})
        if st.form_submit_button("Save prompts", use_container_width=True):
            try:
                profile_service.update_profile(
                    session.get_client(), session.user_id(),
                    profile={"prompts": chosen},
                )
                session.refresh_profile()
                st.success("Prompts saved.")
            except Exception as e:  # noqa: BLE001
                st.error(f"Couldn't save prompts: {e}")
    p = {**prefs_mod.default_preferences(), **((prof.get("profile") or {}).get("preferences") or {})}
    with st.form("edit_prefs"):
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
        submitted = st.form_submit_button("Save preferences", use_container_width=True)

    if submitted:
        new_prefs = {
            "interested_in": interested_in,
            "age_min": age_range[0], "age_max": age_range[1],
            "height_min_cm": height_range[0], "height_max_cm": height_range[1],
            "nationalities": [n.strip() for n in nationalities.split(",") if n.strip()],
            "intent": intent, "dealbreakers": dealbreakers.strip(),
            "physical_prefs": physical_prefs.strip(),
        }
        profile_json = {**(prof.get("profile") or {}), "preferences": new_prefs}
        try:
            profile_service.update_profile(session.get_client(), session.user_id(), profile=profile_json)
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't save: {e}")
            return
        session.refresh_profile()
        st.success("Saved.")


def _idx(options: list, value, default: int = 0) -> int:
    return options.index(value) if value in options else default


# ─── What Dara learned (portrait) ────────────────────────────────────
def _insights(prof: dict) -> None:
    # Read the freshest profile from the DB so a just-built portrait shows even
    # when the cached session profile is stale.
    portrait = {}
    try:
        uid = session.user_id()
        client = session.get_client() if session.current_user() else None
        if client and uid:
            fresh = profile_service.get_profile(client, uid) or {}
            portrait = (fresh.get("profile") or {}).get("portrait") or {}
    except Exception:  # noqa: BLE001
        pass
    if not portrait:
        portrait = (prof.get("profile") or {}).get("portrait") or {}

    bf = portrait.get("big_five") or {}
    has_portrait = bool(portrait.get("speech_notes")) or bool(portrait.get("interests")) \
        or any(v is not None for v in bf.values())
    if not has_portrait:
        st.caption(
            "Once you've finished an interview, Dara sketches what it picked up about you "
            "here — your traits, how you talk, and a few notes. Tap \u201cSee what Dara "
            "learned\u201d at the end of the interview to build it."
        )
        if st.button("Start an interview →", type="primary"):
            go("interview")
        return

    st.caption("Dara's impression from your interview — a read on how you came across, not a clinical test.")
    render_portrait(portrait)

    st.divider()
    if st.button("Refresh from a new interview", use_container_width=True):
        new_profile = {**(prof.get("profile") or {}), "portrait": None}
        try:
            profile_service.update_profile(session.get_client(), session.user_id(), profile=new_profile)
            session.refresh_profile()
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't reset: {e}")
            return
        for k in ("iv_messages", "iv_match", "iv_portrait"):
            st.session_state.pop(k, None)
        go("interview")


# ─── Photos ──────────────────────────────────────────────────────────
def _photos() -> None:
    client = session.get_client()
    uid = session.user_id()

    try:
        photos = profile_service.list_photos(client, uid)
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't load photos: {e}")
        photos = []

    if photos:
        cols = st.columns(3)
        for i, p in enumerate(photos):
            with cols[i % 3]:
                if p.get("signed_url"):
                    st.image(p["signed_url"], use_container_width=True)
                if st.button("Remove", key=f"del_photo_{p['id']}", use_container_width=True):
                    try:
                        profile_service.delete_photo(client, uid, p["id"], p["storage_path"])
                        st.rerun()
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Couldn't remove: {e}")
    else:
        st.caption("No photos yet.")

    upload = st.file_uploader("Add a photo", type=["jpg", "jpeg", "png", "webp"])
    if upload is not None and st.button("Upload", use_container_width=True):
        try:
            profile_service.upload_photo(
                client, uid, upload.getvalue(),
                media_type=upload.type or "image/jpeg",
                position=len(photos),
            )
            st.success("Uploaded.")
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"Upload failed: {e}")


# ─── Plan / billing (simulated) ──────────────────────────────────────
def _plan(prof: dict) -> None:
    current = prof.get("tier", "free")
    st.caption(f"Current plan: **{TIER_INFO[current].name}**")
    st.write("")

    cols = st.columns(len(TIER_ORDER))
    for col, key in zip(cols, TIER_ORDER):
        info = TIER_INFO[key]
        with col:
            with st.container(border=True):
                st.markdown(f"**{info.name}**")
                st.markdown(f"### {info.price}")
                st.caption(info.blurb)
                for perk in info.perks:
                    st.write(f"• {perk}")
                if key == current:
                    st.button("Current plan", key=f"plan_{key}", disabled=True, use_container_width=True)
                else:
                    verb = "Switch to" if TIER_ORDER.index(key) < TIER_ORDER.index(current) else "Upgrade to"
                    if st.button(f"{verb} {info.name}", key=f"plan_{key}", use_container_width=True):
                        try:
                            profile_service.set_tier(session.get_client(), session.user_id(), key)
                            session.refresh_profile()
                            st.toast(f"You're on {info.name} now.", icon="✨")
                            st.rerun()
                        except Exception as e:  # noqa: BLE001
                            st.error(f"Couldn't change plan: {e}")

    st.caption(
        "Billing is simulated for the PoC — switching plans takes effect instantly and "
        "immediately changes which models your calls route to. Wire Stripe in later."
    )


# ─── Settings + danger zone ──────────────────────────────────────────
def _settings(prof: dict) -> None:
    st.write(f"Signed in as **{prof.get('email', '—')}**")

    with st.expander("Change email"):
        with st.form("change_email"):
            new_email = st.text_input("New email")
            if st.form_submit_button("Update email"):
                res = auth_service.update_email(session.get_client(), new_email)
                if res.ok:
                    st.success("Check your new inbox to confirm the change.")
                else:
                    st.error(res.error or "Couldn't update email.")

    with st.expander("Change password"):
        with st.form("change_password"):
            pw1 = st.text_input("New password", type="password")
            pw2 = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Update password"):
                if pw1 != pw2:
                    st.error("Passwords don't match.")
                elif len(pw1) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    res = auth_service.update_password(session.get_client(), pw1)
                    st.success("Password updated.") if res.ok else st.error(res.error or "Failed.")

    st.divider()
    st.subheader("Danger zone")
    st.caption("Deleting your account removes your profile, photos, matches, and conflict sessions. This can't be undone.")
    confirm = st.checkbox("I understand — delete everything.")
    if st.button("Delete my account", type="primary", disabled=not confirm):
        res = auth_service.delete_account(session.get_client(), session.user_id())
        if res.ok:
            session.logout()
            st.rerun()
        else:
            st.error(res.error or "Couldn't delete account.")

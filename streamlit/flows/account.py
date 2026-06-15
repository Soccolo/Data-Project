"""Account page: profile, photos, plan/billing, settings, and account deletion."""

from __future__ import annotations

import streamlit as st

from dara import auth as auth_service
from dara import profile as profile_service
from dara.tiers import TIER_INFO, TIER_ORDER
from . import session


def render() -> None:
    prof = session.current_profile() or {}
    st.markdown("##### Account")
    st.title(f"@{prof.get('username', '—')}")

    tab_profile, tab_photos, tab_plan, tab_settings = st.tabs(
        ["Profile", "Photos", "Plan", "Settings"]
    )
    with tab_profile:
        _profile(prof)
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
        bio = st.text_area("Bio", value=basics.get("bio", ""), height=100)
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
        new_basics = {**basics, "name": name.strip(), "bio": bio.strip()}
        try:
            profile_service.update_profile(
                client, uid, username=username, kind=kind, basics=new_basics
            )
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't save: {e}")
            return
        session.refresh_profile()
        st.success("Saved.")


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

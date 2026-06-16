"""Profile service: the ``public.users`` row plus photo storage.

Pure functions over a Supabase client whose session is already attached, so
row-level security scopes every write to the signed-in user.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from supabase import Client

from .tiers import Tier

PHOTO_BUCKET = "dara-photos"
_SIGNED_URL_TTL = 3600


def get_profile(client: Client, user_id: str) -> Optional[Dict[str, Any]]:
    res = client.table("users").select("*").eq("id", user_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def ensure_profile(client: Client, user: Any) -> Dict[str, Any]:
    """Idempotently guarantee a profile row exists.

    The ``handle_new_user`` trigger normally creates it at sign-up; this is a
    fallback for projects where the trigger isn't installed yet.
    """
    user_id = user.id if hasattr(user, "id") else user["id"]
    existing = get_profile(client, user_id)
    if existing:
        return existing

    email = getattr(user, "email", None) or (user.get("email") if isinstance(user, dict) else "") or ""
    row = {
        "id": user_id,
        "username": f"user_{str(user_id).replace('-', '')[:8]}",
        "email": email,
        "kind": "dating",
        "tier": "free",
        "basics": {},
        "profile": {},
    }
    client.table("users").insert(row).execute()
    return get_profile(client, user_id) or row


def is_onboarded(profile: Optional[Dict[str, Any]]) -> bool:
    if not profile:
        return False
    return bool((profile.get("profile") or {}).get("onboarded"))


def update_profile(
    client: Client,
    user_id: str,
    *,
    username: Optional[str] = None,
    kind: Optional[str] = None,
    basics: Optional[Dict[str, Any]] = None,
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    if username is not None:
        patch["username"] = username
    if kind is not None:
        patch["kind"] = kind
    if basics is not None:
        patch["basics"] = basics
    if profile is not None:
        patch["profile"] = profile
    if patch:
        client.table("users").update(patch).eq("id", user_id).execute()
    return get_profile(client, user_id) or {}


def complete_onboarding(
    client: Client, user_id: str, *, username: str, kind: str, display_name: str,
    current: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    current = current or get_profile(client, user_id) or {}
    basics = dict(current.get("basics") or {})
    basics["name"] = display_name
    profile = dict(current.get("profile") or {})
    profile["onboarded"] = True
    return update_profile(client, user_id, username=username, kind=kind, basics=basics, profile=profile)


def mark_onboarded(client: Client, user_id: str, current: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Flip the onboarded flag once the profile wizard finishes. Used when the
    basics were already saved step-by-step during the wizard."""
    current = current or get_profile(client, user_id) or {}
    profile = dict(current.get("profile") or {})
    profile["onboarded"] = True
    return update_profile(client, user_id, profile=profile)


def username_available(client: Client, username: str, exclude_user_id: Optional[str] = None) -> bool:
    res = client.table("users").select("id").ilike("username", username).execute()
    rows = res.data or []
    if not rows:
        return True
    if exclude_user_id and all(r["id"] == exclude_user_id for r in rows):
        return True
    return False


def set_tier(client: Client, user_id: str, tier: Tier) -> Dict[str, Any]:
    client.table("users").update({"tier": tier}).eq("id", user_id).execute()
    return get_profile(client, user_id) or {}


# ─── Photos ──────────────────────────────────────────────────────────
def list_photos(client: Client, user_id: str) -> List[Dict[str, Any]]:
    res = client.table("photos").select("*").eq("user_id", user_id).order("position").execute()
    photos = res.data or []
    out: List[Dict[str, Any]] = []
    for p in photos:
        out.append({**p, "signed_url": _signed_url(client, p["storage_path"])})
    return out


def upload_photo(client: Client, user_id: str, data: bytes, media_type: str, position: int = 0) -> Dict[str, Any]:
    ext = (media_type.split("/")[-1] or "jpg").replace("jpeg", "jpg")
    path = f"{user_id}/{uuid.uuid4()}.{ext}"
    client.storage.from_(PHOTO_BUCKET).upload(
        path, data, {"content-type": media_type, "upsert": "true"},
    )
    res = client.table("photos").insert({
        "user_id": user_id, "storage_path": path, "position": position, "media_type": media_type,
    }).execute()
    rows = res.data or []
    return rows[0] if rows else {"storage_path": path}


def delete_photo(client: Client, user_id: str, photo_id: str, storage_path: str) -> None:
    client.table("photos").delete().eq("id", photo_id).eq("user_id", user_id).execute()
    try:
        client.storage.from_(PHOTO_BUCKET).remove([storage_path])
    except Exception:  # noqa: BLE001 — row is gone; orphaned object is harmless
        pass


def _signed_url(client: Client, storage_path: str) -> Optional[str]:
    try:
        res = client.storage.from_(PHOTO_BUCKET).create_signed_url(storage_path, _SIGNED_URL_TTL)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(res, dict):
        return res.get("signedURL") or res.get("signedUrl") or res.get("signed_url")
    return None


def download_photo_bytes(client: Client, storage_path: str) -> Optional[bytes]:
    """Raw image bytes for a stored photo — used to feed the vision model.
    RLS lets any authenticated user read photos, so this works for a match's
    photos too, not just the caller's own."""
    try:
        return client.storage.from_(PHOTO_BUCKET).download(storage_path)
    except Exception:  # noqa: BLE001
        return None


# ─── In-progress interview draft (private, on user_state) ────────────
def save_interview_draft(client: Client, user_id: str, messages) -> None:
    """Persist the live interview so a page refresh restores it. Owner-only."""
    try:
        client.table("user_state").upsert(
            {"user_id": user_id, "interview_draft": messages},
            on_conflict="user_id",
        ).execute()
    except Exception:  # noqa: BLE001
        pass


def load_interview_draft(client: Client, user_id: str) -> list:
    try:
        res = (client.table("user_state").select("interview_draft")
               .eq("user_id", user_id).limit(1).execute())
        if res.data:
            draft = res.data[0].get("interview_draft")
            if isinstance(draft, list):
                return draft
    except Exception:  # noqa: BLE001
        pass
    return []


def clear_interview_draft(client: Client, user_id: str) -> None:
    try:
        client.table("user_state").upsert(
            {"user_id": user_id, "interview_draft": None},
            on_conflict="user_id",
        ).execute()
    except Exception:  # noqa: BLE001
        pass

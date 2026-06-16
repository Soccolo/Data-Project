"""Matchmaking: turn a user's interview + stated preferences into a scored
match against a candidate, including a vision read of the candidate's photos.

Design choices that matter:
- Hard preferences (gender, age, height) are matched against the candidate's
  *stated profile*, not guessed from anything.
- The photo read only assesses what a photo legitimately shows (vibe, setting,
  presentation). It never infers ethnicity, nationality, or age from a face.
- "Preferred nationality" is a soft signal the verdict weighs, not a gate.
- Everything degrades gracefully: no real candidate (e.g. an empty PoC) falls
  back to a simulated one so the flow always completes.
"""

from __future__ import annotations

import base64
import random
from typing import Any, Dict, List, Optional

from . import prefs as prefs_mod
from . import profile as profile_service
from . import schemas
from .ai_client import call_ai
from .config import settings
from .tiers import Tier

_rng = random.Random(11)

_SCORE_SYSTEM = (
    "You are Dara, turning a matchmaking interview into a compatibility verdict "
    "for your user about a specific candidate you found. Weigh the interview, the "
    "user's stated preferences, the candidate's profile, and the photo read. Return "
    "JSON with: score (integer 0-100), verdict (one short, warm sentence), and "
    "reasons (3 short, specific strings). Ground every reason in the actual details "
    "given — never invent facts."
)

_PHOTO_SYSTEM = (
    "You are Dara, glancing at a match candidate's photos for your user. Describe "
    "ONLY what the photos genuinely show — overall vibe, setting, energy, how they "
    "present themselves. Do NOT guess ethnicity, nationality, age, or any protected "
    "trait from a face; those come from the profile, not a photo. Return JSON: "
    "impression (one sentence), vibe_tags (3-5 short tags), fit_comment (one sentence "
    "on how that vibe fits what the user is looking for)."
)

_SAMPLE = [
    {"name": "Mara", "gender": "Woman", "job": "Marine biologist", "nationality": "Portuguese",
     "bio": "Weekend free-diver, weekday data nerd. Looking for someone genuinely curious."},
    {"name": "Ezra", "gender": "Man", "job": "Jazz pianist", "nationality": "Canadian",
     "bio": "Plays late, cooks well, bad at small talk but great at the real kind."},
    {"name": "Noa", "gender": "Non-binary", "job": "Climate researcher", "nationality": "Dutch",
     "bio": "Cargo-bikes everywhere, reads two books at once, always up for a detour."},
]


def find_match(
    *,
    conversation: Optional[List[Dict[str, str]]] = None,
    tier: Tier = "free",
    client: Any = None,
    me: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Orchestrate a single match reveal. Always returns a result dict with
    keys: candidate, photo_fit, simulated, score, verdict, reasons."""
    prefs = {**prefs_mod.default_preferences(), **(((me or {}).get("profile") or {}).get("preferences") or {})}

    candidate = None
    if client is not None and me is not None:
        try:
            candidate = _find_candidate(client, me, prefs)
        except Exception:  # noqa: BLE001 — degrade to a simulated candidate
            candidate = None
    simulated = candidate is None
    if simulated:
        candidate = _simulated_candidate(prefs)

    photo_fit = _analyze_photos(client, candidate, prefs, tier)
    result = _score(conversation or [], me or {}, prefs, candidate, photo_fit, tier)
    result.update({"candidate": candidate, "photo_fit": photo_fit, "simulated": simulated})
    return result


# ─── Candidate selection (real users) ────────────────────────────────
def _find_candidate(client: Any, me: Dict[str, Any], prefs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    me_id = me.get("id")
    want = prefs_mod.wanted_genders(prefs)
    my_gender = (me.get("basics") or {}).get("gender")

    res = (client.table("users").select("*")
           .neq("id", me_id).in_("kind", ["dating", "both"]).limit(60).execute())
    rows = res.data or []

    passed: set = set()
    try:
        sres = client.table("user_state").select("passed_ids").eq("user_id", me_id).limit(1).execute()
        if sres.data:
            passed = set(sres.data[0].get("passed_ids") or [])
    except Exception:  # noqa: BLE001
        pass

    ranked: List[tuple] = []
    for r in rows:
        if r.get("id") in passed:
            continue
        b = r.get("basics") or {}
        if b.get("gender") and want and b["gender"] not in want:
            continue
        age = b.get("age")
        if age and not (prefs["age_min"] <= _int(age) <= prefs["age_max"]):
            continue
        h = b.get("height_cm")
        if h and not (prefs["height_min_cm"] <= _int(h) <= prefs["height_max_cm"]):
            continue
        their_want = prefs_mod.wanted_genders((r.get("profile") or {}).get("preferences") or {})
        mutual = (not my_gender) or (my_gender in their_want)
        ranked.append((0 if mutual else 1, r))

    if not ranked:
        return None
    best_rank = min(t[0] for t in ranked)
    top = [r for rank, r in ranked if rank == best_rank]
    chosen = dict(_rng.choice(top))
    try:
        chosen["_photos"] = profile_service.list_photos(client, chosen["id"])
    except Exception:  # noqa: BLE001
        chosen["_photos"] = []
    return chosen


def _simulated_candidate(prefs: Dict[str, Any]) -> Dict[str, Any]:
    want = prefs_mod.wanted_genders(prefs)
    pool = [s for s in _SAMPLE if s["gender"] in want] or _SAMPLE
    s = dict(_rng.choice(pool))
    lo_age = max(prefs_mod.MIN_AGE, _int(prefs["age_min"]))
    hi_age = max(lo_age, _int(prefs["age_max"]))
    lo_h, hi_h = sorted((_int(prefs["height_min_cm"]), _int(prefs["height_max_cm"])))
    return {
        "username": s["name"].lower(),
        "basics": {
            "name": s["name"], "gender": s["gender"], "age": _rng.randint(lo_age, hi_age),
            "job": s["job"], "nationality": s["nationality"], "bio": s["bio"],
            "height_cm": _rng.randint(lo_h, hi_h),
        },
        "_photos": [],
    }


# ─── Photo read (vision) ─────────────────────────────────────────────
def _analyze_photos(client: Any, candidate: Dict[str, Any], prefs: Dict[str, Any], tier: Tier) -> Optional[Dict[str, Any]]:
    photos = candidate.get("_photos") or []
    media: List[Dict[str, str]] = []
    if client is not None and photos:
        for p in photos[:2]:
            data = profile_service.download_photo_bytes(client, p.get("storage_path", ""))
            if data:
                media.append({
                    "mediaType": p.get("media_type", "image/jpeg"),
                    "base64": base64.b64encode(data).decode(),
                })
    # In live mode with no actual image, there's nothing to look at.
    if not media and settings.ai_mode != "mock":
        return None

    user_text = (
        ("The candidate's photos are attached. " if media else "")
        + f"What the user is looking for: {prefs_mod.summarize_preferences(prefs)}"
    )
    try:
        raw = call_ai(
            purpose="photoAnalysis", system_prompt=_PHOTO_SYSTEM, tier=tier,
            user_text=user_text, media=media or None, schema=schemas.PHOTO_FIT,
        )
        return schemas.normalize_photo_fit(raw)
    except Exception:  # noqa: BLE001
        return None


# ─── Scoring ─────────────────────────────────────────────────────────
def _score(conversation, me, prefs, candidate, photo_fit, tier) -> Dict[str, Any]:
    convo = "\n".join(
        f"{'You' if m.get('role') == 'user' else 'Dara'}: {m.get('content', '')}"
        for m in conversation
    )
    cb = candidate.get("basics") or {}
    photo_line = ""
    if photo_fit:
        tags = ", ".join(photo_fit.get("vibe_tags", []))
        photo_line = f"Photo read: {photo_fit.get('impression', '')} ({tags}). {photo_fit.get('fit_comment', '')}"

    user_text = (
        f"YOUR USER\n{prefs_mod.summarize_self(me.get('basics') or {})}\n"
        f"Looking for: {prefs_mod.summarize_preferences(prefs)}\n\n"
        f"CANDIDATE: {cb.get('name', 'Someone')}\n{prefs_mod.summarize_self(cb)}\n{photo_line}\n\n"
        f"INTERVIEW\n{convo}\n\n"
        "Give the compatibility verdict now."
    )
    try:
        raw = call_ai(
            purpose="score", system_prompt=_SCORE_SYSTEM, tier=tier,
            user_text=user_text, schema=schemas.SCORE, max_tokens=700,
        )
        return schemas.normalize_score(raw)
    except Exception as e:  # noqa: BLE001
        return {"score": 0, "verdict": f"Couldn't score the match: {e}", "reasons": []}


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default

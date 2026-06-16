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
from .tiers import Tier, effective_tier

_rng = random.Random(11)

PROXY_TURNS_EACH_SIDE = 10  # 20 messages total in a Dara-to-Dara conversation

# Dara-to-Dara conversation length, per the Mira original: 10 turns each side.
PROXY_TURNS_EACH_SIDE = 10

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

_PORTRAIT_SYSTEM = (
    "You are Dara, distilling a getting-to-know-you interview into a structured "
    "portrait of your user, so you can later represent them faithfully in "
    "conversations with other people's Daras. Capture who they are AND how they "
    "actually talk. Return JSON with: interests, values, communication_style, "
    "humor_style, looking_for, dealbreakers, observations, speech_notes (a precise "
    "description of their writing voice — casing, punctuation, rhythm, slang), and "
    "recent_messages (2-3 short lines written in their exact voice, as if texting). "
    "Ground everything in what they actually said; do not invent biography."
)


def distill_portrait(conversation, basics, tier: Tier = "free") -> Dict[str, Any]:
    """Turn an interview transcript into the structured portrait."""
    convo = "\n".join(
        f"{'User' if m.get('role') == 'user' else 'Dara'}: {m.get('content', '')}"
        for m in (conversation or [])
    )
    user_text = (
        f"Here is the interview with {basics.get('name', 'the user')}.\n"
        f"Basics: {prefs_mod.summarize_self(basics)}\n\n"
        f"TRANSCRIPT\n{convo}\n\n"
        "Distil the portrait now."
    )
    try:
        raw = call_ai(
            purpose="profile", system_prompt=_PORTRAIT_SYSTEM, tier=tier,
            user_text=user_text, schema=schemas.PORTRAIT, max_tokens=900,
        )
        return schemas.normalize_portrait(raw)
    except Exception:  # noqa: BLE001
        return schemas.normalize_portrait({})


def get_or_build_portrait(me, conversation, tier: Tier = "free", client: Any = None) -> Dict[str, Any]:
    """Return the user's cached portrait, distilling and persisting it once if
    it doesn't exist yet."""
    existing = ((me or {}).get("profile") or {}).get("portrait")
    if existing and existing.get("speech_notes"):
        return schemas.normalize_portrait(existing)

    portrait = distill_portrait(conversation, (me or {}).get("basics") or {}, tier)

    uid = (me or {}).get("id")
    if client is not None and uid:
        try:
            profile_json = {**((me or {}).get("profile") or {}), "portrait": portrait}
            profile_service.update_profile(client, uid, profile=profile_json)
        except Exception:  # noqa: BLE001
            pass
    return portrait


# ─── Dara-to-Dara proxy conversation ─────────────────────────────────
def _proxy_system(portrait, my_basics, their_basics, conversation, total_turns) -> str:
    """Roleplay prompt: speak as my_basics in their own voice, drawn from the
    portrait. Mirrors Mira's proxy roleplay — voice fidelity + anti-hallucination."""
    me_name = my_basics.get("name", "You")
    their_name = their_basics.get("name", "them")
    interests = ", ".join(portrait.get("interests") or []) or "unspecified"
    values = ", ".join(portrait.get("values") or []) or "unspecified"
    samples = portrait.get("recent_messages") or []
    voice_block = (
        "Examples of how they ACTUALLY write (match this exactly — casing, "
        "punctuation, length, slang):\n" + "\n".join(f"> {m}" for m in samples)
        if samples else "(no samples — follow the speech notes)"
    )
    convo_lines = (
        "\n".join(
            f"{me_name if m['speaker'] == 'me' else their_name}: {m['content']}"
            for m in conversation
        )
        if conversation
        else "[You're starting. Send a warm, on-brand opener in your voice.]"
    )
    return (
        f"You are roleplaying {me_name} in a getting-to-know-you conversation with "
        f"{their_name}. You ARE {me_name}. Speaking in their exact voice matters more "
        f"than anything else — {me_name} will read this transcript.\n\n"
        f"Who you are: {prefs_mod.summarize_self(my_basics)}\n"
        f"Communication style: {portrait.get('communication_style', 'natural')}. "
        f"Humor: {portrait.get('humor_style', 'unspecified')}.\n"
        f"Pulled toward: {interests}. Values: {values}.\n"
        f"Looking for: {portrait.get('looking_for', 'unspecified')}.\n\n"
        f"VOICE — write exactly like this:\n{portrait.get('speech_notes', '(natural)')}\n{voice_block}\n\n"
        f"Who they are (so you know what to react to): {prefs_mod.summarize_self(their_basics)}\n\n"
        "RULES:\n"
        "- If you're curious about something, ASK IT NOW — there is no 'later'.\n"
        "- Share your own concrete facts willingly when they come up; don't be evasive.\n"
        "- NEVER invent specifics you weren't given (employer, neighbourhood, names, "
        "trips). If asked something you don't know, defer warmly — 'i'll tell you when "
        "we actually meet' — in your voice. Inventing breaks trust when they read this.\n"
        "- Keep messages SHORT (1-3 sentences). React naturally.\n\n"
        f"You have ~{total_turns} messages total. Conversation so far "
        f"({len(conversation)} of ~{total_turns}):\n{convo_lines}\n\n"
        'Output strict JSON, no markdown: {"message": "your next message in your exact voice"}'
    )


def run_proxy(me_portrait, me_basics, cand_portrait, cand_basics,
              tier: Tier = "free", turns_each: int = PROXY_TURNS_EACH_SIDE, on_turn=None):
    """Alternate turns between the two agents. Returns a transcript list of
    ``{"speaker": "me"|"them", "content": str}`` ("me" = the user's side)."""
    convo: List[Dict[str, str]] = []
    total = turns_each * 2
    for turn in range(total):
        is_me = (turn % 2 == 0)
        speaker = "me" if is_me else "them"
        portrait = me_portrait if is_me else cand_portrait
        my_b = me_basics if is_me else cand_basics
        their_b = cand_basics if is_me else me_basics
        # Recast the running transcript to the current speaker's perspective.
        perspective = [
            {"speaker": "me" if m["speaker"] == speaker else "them", "content": m["content"]}
            for m in convo
        ]
        try:
            raw = call_ai(
                purpose="proxyTurn",
                system_prompt=_proxy_system(portrait, my_b, their_b, perspective, total),
                tier=tier, user_text="Send your next message.", schema=schemas.PROXY,
            )
            msg = schemas.normalize_proxy(raw)
        except Exception:  # noqa: BLE001
            msg = ""
        convo.append({"speaker": speaker, "content": msg or "…"})
        if on_turn:
            try:
                on_turn(turn + 1, total, list(convo))
            except Exception:  # noqa: BLE001
                pass
    return convo


# ─── Dara-to-Dara proxy conversation ─────────────────────────────────
def _proxy_system(portrait, my_basics, their_basics, total_turns, conversation) -> str:
    name = my_basics.get("name", "you")
    their_name = their_basics.get("name", "them")
    speech = portrait.get("speech_notes") or ""
    samples = portrait.get("recent_messages") or []
    sample_block = ""
    if samples:
        joined = "\n".join(f"> {s}" for s in samples)
        sample_block = (
            f"\nExamples of how {name} ACTUALLY writes (match this exactly — casing, "
            f"punctuation, length, slang):\n{joined}\n"
        )
    convo_block = (
        "[You're starting. Send a warm, on-brand opener in your voice.]"
        if not conversation else
        "\n".join(
            f"{name if m['speaker'] == 'me' else their_name}: {m['content']}"
            for m in conversation
        )
    )
    return (
        f"You are roleplaying {name} in a getting-to-know-you conversation with "
        f"{their_name}. You ARE {name}. Sounding like them matters more than anything.\n\n"
        f"Who you are: {prefs_mod.summarize_self(my_basics)}\n"
        f"Communication style: {portrait.get('communication_style', 'natural')}. "
        f"Humor: {portrait.get('humor_style', '')}.\n"
        f"Pulled toward: {', '.join(portrait.get('interests', []))}. "
        f"Values: {', '.join(portrait.get('values', []))}.\n"
        f"Looking for: {portrait.get('looking_for', '')}.\n"
        f"Speech style: {speech}\n{sample_block}\n"
        f"Who they are (react to this, don't recite it): {their_name}, "
        f"{their_basics.get('age', '?')}, {their_basics.get('gender', '')}.\n\n"
        "Rules: This is casual. If you're curious, ASK NOW — there is no 'later'. "
        "Share concrete facts about yourself willingly when they come up. Keep messages "
        "SHORT (1-3 sentences). Conduct it in English even if your human's native "
        "language differs.\n"
        "ANTI-HALLUCINATION: never invent facts about yourself not given above (employer, "
        "neighbourhood, friends, trips). If asked something you don't know, defer warmly "
        "in-voice ('i'll tell you on the date') rather than making it up.\n"
        f"You have ~{total_turns} total messages. Be efficient.\n\n"
        f"Conversation so far:\n{convo_block}\n\n"
        'Output strict JSON: {"message": "your next message in voice"}'
    )


def _proxy_turn(portrait, my_basics, their_basics, conversation, total_turns, tier) -> str:
    system = _proxy_system(portrait, my_basics, their_basics, total_turns, conversation)
    try:
        raw = call_ai(
            purpose="proxyTurn", system_prompt=system, tier=tier,
            user_text="Send your next message.", schema=schemas.PROXY, max_tokens=300,
        )
        msg = (raw or {}).get("message") if isinstance(raw, dict) else None
        return (str(msg).strip() if msg else "…")
    except Exception:  # noqa: BLE001
        return "…"


def run_proxy(me, candidate, tier: Tier = "free", turns_each: int = PROXY_TURNS_EACH_SIDE, on_turn=None):
    """Alternate turns between the two users' agents, each roleplaying its human
    from their portrait. Returns the transcript: [{speaker: 'me'|'them', content}].
    The 'higher' of the two tiers drives the model (per effective_tier)."""
    me_tier = (me or {}).get("tier") or tier
    cand_tier = (candidate or {}).get("tier") or "free"
    eff = effective_tier(me_tier, cand_tier)

    me_portrait = ((me or {}).get("profile") or {}).get("portrait") or {}
    cand_portrait = ((candidate or {}).get("profile") or {}).get("portrait") or {}
    me_basics = (me or {}).get("basics") or {}
    cand_basics = (candidate or {}).get("basics") or {}

    convo: List[Dict[str, str]] = []
    for turn in range(turns_each * 2):
        is_me = turn % 2 == 0
        speaker = "me" if is_me else "them"
        portrait = me_portrait if is_me else cand_portrait
        my_b = me_basics if is_me else cand_basics
        their_b = cand_basics if is_me else me_basics
        # Recast the running transcript to the current speaker's point of view.
        perspective = [
            {"speaker": "me" if m["speaker"] == speaker else "them", "content": m["content"]}
            for m in convo
        ]
        msg = _proxy_turn(portrait, my_b, their_b, perspective, turns_each * 2, eff)
        convo.append({"speaker": speaker, "content": msg})
        if on_turn:
            on_turn(list(convo))
    return convo

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

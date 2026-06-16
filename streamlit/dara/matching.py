"""Matchmaking: interview → stored portrait → Dara-to-Dara proxy conversation
→ scored verdict, with a vision read of the candidate's photos.

Pipeline (mirrors Mira):
1. Distil the user's interview into a structured portrait (cached on the user).
2. Pick a candidate — a real user if one fits, else a built-in seed test account,
   else a simulated persona — so the flow always completes.
3. Run a proxy conversation: each side's agent roleplays its human from the
   portrait (10 turns each = 20 messages).
4. Read the candidate's photos for vibe (never protected attributes).
5. Score from the proxy transcript.

Design guardrails: hard preferences (gender, age, height) match the candidate's
*stated profile*; the photo read only describes what a photo legitimately shows;
"preferred nationality" is a soft signal, never a gate.
"""

from __future__ import annotations

import base64
import random
from typing import Any, Dict, List, Optional

from . import prefs as prefs_mod
from . import profile as profile_service
from . import schemas
from . import seed as seed_mod
from .ai_client import call_ai
from .config import settings
from .tiers import Tier, effective_tier

_rng = random.Random(11)

PROXY_TURNS_EACH_SIDE = 10  # 20 messages total in a Dara-to-Dara conversation

_SCORE_SYSTEM = (
    "You are Dara, reporting back to your user after your proxy just had a "
    "getting-to-know-you conversation with a candidate's proxy. Weigh that "
    "conversation, your user's stated preferences, the candidate's profile, and the "
    "photo read. Be honest, not sycophantic — notice real chemistry and real friction. "
    "Return JSON with: score (integer 0-100), verdict (one short, warm sentence), and "
    "reasons (3 short, specific strings grounded in what actually happened)."
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
    "Record ONLY what they actually stated — never specialise or fill gaps. If they "
    "said 'actuary' but not the field, keep 'actuary'; do NOT upgrade it to 'pensions "
    "actuary' or any specific guess. Leave unknowns out entirely, and let the "
    "recent_messages invent no concrete facts. Ground everything in what they said."
)

_SAMPLE = [
    {"name": "Mara", "gender": "Woman", "job": "Marine biologist", "nationality": "Portuguese",
     "bio": "Weekend free-diver, weekday data nerd. Looking for someone genuinely curious."},
    {"name": "Ezra", "gender": "Man", "job": "Jazz pianist", "nationality": "Canadian",
     "bio": "Plays late, cooks well, bad at small talk but great at the real kind."},
    {"name": "Noa", "gender": "Non-binary", "job": "Climate researcher", "nationality": "Dutch",
     "bio": "Cargo-bikes everywhere, reads two books at once, always up for a detour."},
]


# ─── Portrait distillation ───────────────────────────────────────────
def distill_portrait(conversation, basics, tier: Tier = "free") -> Dict[str, Any]:
    convo = "\n".join(
        f"{'User' if m.get('role') == 'user' else 'Dara'}: {m.get('content', '')}"
        for m in (conversation or [])
    )
    user_text = (
        f"Here is the interview with {basics.get('name', 'the user')}.\n"
        f"Basics: {prefs_mod.summarize_self(basics)}\n\n"
        f"TRANSCRIPT\n{convo}\n\nDistil the portrait now."
    )
    try:
        raw = call_ai(purpose="profile", system_prompt=_PORTRAIT_SYSTEM, tier=tier,
                      user_text=user_text, schema=schemas.PORTRAIT, max_tokens=900)
        return schemas.normalize_portrait(raw)
    except Exception:  # noqa: BLE001
        return schemas.normalize_portrait({})


def get_or_build_portrait(me, conversation, tier: Tier = "free", client: Any = None) -> Dict[str, Any]:
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


def _ensure_portrait(entity: Dict[str, Any]) -> Dict[str, Any]:
    """Real users who haven't been interviewed (and any sparse profile) get a
    minimal portrait built from their basics so the proxy can still roleplay."""
    p = (entity.get("profile") or {}).get("portrait")
    if p and p.get("speech_notes"):
        return schemas.normalize_portrait(p)
    b = entity.get("basics") or {}
    return schemas.normalize_portrait({
        "communication_style": "natural, conversational",
        "looking_for": b.get("bio", ""),
        "speech_notes": "relaxed, conversational; complete but unfussy sentences",
        "recent_messages": [b["bio"]] if b.get("bio") else [],
        "vibe": "",
    })


# ─── Dara-to-Dara proxy conversation ─────────────────────────────────
def _proxy_system(portrait, my_basics, their_basics, total_turns, conversation) -> str:
    name = (my_basics.get("name") or "you").replace(" (Test)", "")
    their_name = (their_basics.get("name") or "them").replace(" (Test)", "")
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
        "\n".join(f"{name if m['speaker'] == 'me' else their_name}: {m['content']}"
                  for m in conversation)
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
        f"Speech style: {portrait.get('speech_notes', '(natural)')}\n{sample_block}\n"
        f"Who they are (react to this, don't recite it): {their_name}, "
        f"{their_basics.get('age', '?')}, {their_basics.get('gender', '')}.\n\n"
        "Rules: This is casual. If you're curious, ASK NOW — there is no 'later'. "
        "Share concrete facts about yourself willingly when they come up. Keep messages "
        "SHORT (1-3 sentences). Conduct it in English even if your human's native "
        "language differs.\n"
        "ANTI-HALLUCINATION (critical): only state facts explicitly given above. NEVER "
        "guess specifics you weren't told — not your employer, neighbourhood, friends, "
        "trips, NOR a narrower version of something general. If you're 'an actuary' and "
        "they ask what kind, you genuinely DO NOT know — do not pick one. When asked "
        "anything you don't know, playfully deferring IS the correct answer: 'ha, let's "
        f"keep that for when we actually meet' or 'i'll tell you in person' — in {name}'s "
        f"voice. Guessing breaks trust when {name} reads this transcript.\n"
        f"You have ~{total_turns} total messages. Be efficient.\n\n"
        f"Conversation so far:\n{convo_block}\n\n"
        'Output strict JSON: {"message": "your next message in voice"}'
    )


def _proxy_turn(portrait, my_basics, their_basics, conversation, total_turns, tier) -> str:
    system = _proxy_system(portrait, my_basics, their_basics, total_turns, conversation)
    try:
        raw = call_ai(purpose="proxyTurn", system_prompt=system, tier=tier,
                      user_text="Send your next message.", schema=schemas.PROXY, max_tokens=300)
        return schemas.normalize_proxy(raw) or "…"
    except Exception:  # noqa: BLE001
        return "…"


def run_proxy(me, candidate, tier: Tier = "free", turns_each: int = PROXY_TURNS_EACH_SIDE, on_turn=None):
    """Alternate turns between the two users' agents. Returns the transcript:
    [{speaker: 'me'|'them', content}]. The higher of the two tiers drives the model."""
    eff = effective_tier((me or {}).get("tier") or tier, (candidate or {}).get("tier") or "free")
    me_portrait = ((me or {}).get("profile") or {}).get("portrait") or {}
    cand_portrait = ((candidate or {}).get("profile") or {}).get("portrait") or {}
    me_basics = (me or {}).get("basics") or {}
    cand_basics = (candidate or {}).get("basics") or {}

    convo: List[Dict[str, str]] = []
    total = turns_each * 2
    for turn in range(total):
        is_me = turn % 2 == 0
        speaker = "me" if is_me else "them"
        portrait = me_portrait if is_me else cand_portrait
        my_b = me_basics if is_me else cand_basics
        their_b = cand_basics if is_me else me_basics
        perspective = [
            {"speaker": "me" if m["speaker"] == speaker else "them", "content": m["content"]}
            for m in convo
        ]
        msg = _proxy_turn(portrait, my_b, their_b, perspective, total, eff)
        convo.append({"speaker": speaker, "content": msg})
        if on_turn:
            try:
                on_turn(turn + 1, total, list(convo))
            except Exception:  # noqa: BLE001
                pass
    return convo


# ─── Orchestration ───────────────────────────────────────────────────
def find_match(*, conversation: Optional[List[Dict[str, str]]] = None, tier: Tier = "free",
               client: Any = None, me: Optional[Dict[str, Any]] = None, on_turn=None) -> Dict[str, Any]:
    """Run a full match reveal. Always returns: candidate, photo_fit, transcript,
    score, verdict, reasons, source ('real'|'seed'|'simulated'), simulated, me_name."""
    me = dict(me or {})
    prefs = {**prefs_mod.default_preferences(), **((me.get("profile") or {}).get("preferences") or {})}

    # 1) the user's portrait (distilled once, then cached)
    me_portrait = get_or_build_portrait(me, conversation, tier, client)
    me["profile"] = {**(me.get("profile") or {}), "portrait": me_portrait}
    me_name = (me.get("basics") or {}).get("name", "You")

    # 2) candidate: real → seed → simulated
    candidate, source = _choose_candidate(client, me, prefs)
    candidate = dict(candidate)
    candidate["profile"] = {**(candidate.get("profile") or {}), "portrait": _ensure_portrait(candidate)}

    # 3) proxy conversation
    transcript = run_proxy(me, candidate, tier=tier, turns_each=PROXY_TURNS_EACH_SIDE, on_turn=on_turn)

    # 4) photo read + 5) score from the transcript
    photo_fit = _analyze_photos(client, candidate, prefs, tier)
    result = _score(transcript, me, prefs, candidate, photo_fit, tier)
    result.update({
        "candidate": candidate, "photo_fit": photo_fit, "transcript": transcript,
        "source": source, "simulated": source != "real", "me_name": me_name,
    })
    return result


def _choose_candidate(client, me, prefs):
    if client is not None and me.get("id"):
        try:
            real = _find_candidate(client, me, prefs)
            if real:
                return real, "real"
        except Exception:  # noqa: BLE001
            pass
    seeded = _pick_seed(prefs)
    if seeded:
        return seeded, "seed"
    return _simulated_candidate(prefs), "simulated"


def _matches_prefs(basics: Dict[str, Any], prefs: Dict[str, Any]) -> bool:
    want = prefs_mod.wanted_genders(prefs)
    if basics.get("gender") and want and basics["gender"] not in want:
        return False
    age = basics.get("age")
    if age and not (prefs["age_min"] <= _int(age) <= prefs["age_max"]):
        return False
    h = basics.get("height_cm")
    if h and not (prefs["height_min_cm"] <= _int(h) <= prefs["height_max_cm"]):
        return False
    return True


def _find_candidate(client: Any, me: Dict[str, Any], prefs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    me_id = me.get("id")
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
        if not _matches_prefs(r.get("basics") or {}, prefs):
            continue
        their_want = prefs_mod.wanted_genders((r.get("profile") or {}).get("preferences") or {})
        mutual = (not my_gender) or (my_gender in their_want)
        ranked.append((0 if mutual else 1, r))

    if not ranked:
        return None
    best = min(t[0] for t in ranked)
    chosen = dict(_rng.choice([r for rank, r in ranked if rank == best]))
    try:
        chosen["_photos"] = profile_service.list_photos(client, chosen["id"])
    except Exception:  # noqa: BLE001
        chosen["_photos"] = []
    return chosen


def _pick_seed(prefs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pool = [c for c in seed_mod.seed_candidates() if _matches_prefs(c.get("basics") or {}, prefs)]
    return _rng.choice(pool) if pool else None


def _simulated_candidate(prefs: Dict[str, Any]) -> Dict[str, Any]:
    want = prefs_mod.wanted_genders(prefs)
    pool = [s for s in _SAMPLE if s["gender"] in want] or _SAMPLE
    s = dict(_rng.choice(pool))
    lo_age = max(prefs_mod.MIN_AGE, _int(prefs["age_min"]))
    hi_age = max(lo_age, _int(prefs["age_max"]))
    lo_h, hi_h = sorted((_int(prefs["height_min_cm"]), _int(prefs["height_max_cm"])))
    return {
        "username": s["name"].lower(),
        "basics": {"name": s["name"], "gender": s["gender"], "age": _rng.randint(lo_age, hi_age),
                   "job": s["job"], "nationality": s["nationality"], "bio": s["bio"],
                   "height_cm": _rng.randint(lo_h, hi_h)},
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
                media.append({"mediaType": p.get("media_type", "image/jpeg"),
                              "base64": base64.b64encode(data).decode()})
    if not media and settings.ai_mode != "mock":
        return None
    user_text = (("The candidate's photos are attached. " if media else "")
                 + f"What the user is looking for: {prefs_mod.summarize_preferences(prefs)}")
    try:
        raw = call_ai(purpose="photoAnalysis", system_prompt=_PHOTO_SYSTEM, tier=tier,
                      user_text=user_text, media=media or None, schema=schemas.PHOTO_FIT)
        return schemas.normalize_photo_fit(raw)
    except Exception:  # noqa: BLE001
        return None


# ─── Scoring (from the proxy transcript) ─────────────────────────────
def _score(transcript, me, prefs, candidate, photo_fit, tier) -> Dict[str, Any]:
    me_name = (me.get("basics") or {}).get("name", "You")
    cb = candidate.get("basics") or {}
    cand_name = cb.get("name", "Someone")
    convo = "\n".join(
        f"{me_name if m['speaker'] == 'me' else cand_name}: {m['content']}" for m in transcript
    )
    photo_line = ""
    if photo_fit:
        tags = ", ".join(photo_fit.get("vibe_tags", []))
        photo_line = f"Photo read: {photo_fit.get('impression', '')} ({tags}). {photo_fit.get('fit_comment', '')}"

    user_text = (
        f"YOUR USER\n{prefs_mod.summarize_self(me.get('basics') or {})}\n"
        f"Looking for: {prefs_mod.summarize_preferences(prefs)}\n\n"
        f"CANDIDATE: {cand_name}\n{prefs_mod.summarize_self(cb)}\n{photo_line}\n\n"
        f"THE PROXY CONVERSATION\n{convo}\n\nGive the compatibility verdict now."
    )
    try:
        raw = call_ai(purpose="score", system_prompt=_SCORE_SYSTEM, tier=tier,
                      user_text=user_text, schema=schemas.SCORE, max_tokens=700)
        return schemas.normalize_score(raw)
    except Exception as e:  # noqa: BLE001
        return {"score": 0, "verdict": f"Couldn't score the match: {e}", "reasons": []}


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def persona_reply(candidate, me_basics, chat, tier: Tier = "free") -> str:
    """A seed/persona candidate replying in their own voice to a real user's
    chat. ``chat`` is [{"sender": "me"|"them", "body": str}] where 'them' is the
    candidate. Same voice + anti-hallucination rules as the proxy."""
    portrait = _ensure_portrait(candidate)
    cand_basics = candidate.get("basics") or {}
    # In the roleplay's frame, the candidate is "me"; the real user is "them".
    perspective = [
        {"speaker": "me" if m.get("sender") == "them" else "them", "content": m.get("body", "")}
        for m in (chat or [])
    ]
    return _proxy_turn(portrait, cand_basics, me_basics or {"name": "they"}, perspective, 40, tier)

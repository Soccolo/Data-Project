"""JSON schemas for structured AI calls, plus normalizers.

The schemas are deliberately limited to the subset Gemini's ``responseSchema``
accepts (type / properties / items / required / enum) so the *same* schema also
works as a Claude tool ``input_schema``. Range/shape enforcement that a schema
can't guarantee (e.g. score 0–100) happens in the normalizers, which also fill
defaults so the UI never blanks out on a slightly-off model response.
"""

from __future__ import annotations

from typing import Any, Dict, List

# ─── Schemas ─────────────────────────────────────────────────────────
SCORE: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "verdict": {"type": "string"},
        "reasons": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "verdict", "reasons"],
}

PRESCREEN: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "safe": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["safe", "reason"],
}

# Distillation of one party's private intake: their side, underlying needs, and
# a safety judgement (abuse / violence / coercion → not safe to mediate).
INTAKE: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "needs": {"type": "array", "items": {"type": "string"}},
        "safe": {"type": "boolean"},
        "safety_reason": {"type": "string"},
    },
    "required": ["summary", "safe"],
}

MEDIATION: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "messages": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["messages"],
}

# In-chat Dara help: a few message options the user can send, each with a short
# label describing its angle ("Playful", "Ask about her work", "Suggest coffee").
SUGGESTIONS: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        },
    },
    "required": ["suggestions"],
}

# Personality portrait distilled from the interview. Mirrors the shape of the
# seed candidates' ``portrait`` so interviewed users and seeds are interchangeable
# in the proxy step. ``speech_notes`` + ``recent_messages`` drive voice matching.
PORTRAIT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "interests": {"type": "array", "items": {"type": "string"}},
        "values": {"type": "array", "items": {"type": "string"}},
        "communication_style": {"type": "string"},
        "humor_style": {"type": "string"},
        "looking_for": {"type": "string"},
        "dealbreakers": {"type": "array", "items": {"type": "string"}},
        "observations": {"type": "array", "items": {"type": "string"}},
        "speech_notes": {"type": "string"},
        "recent_messages": {"type": "array", "items": {"type": "string"}},
        "vibe": {"type": "string"},
        "big_five": {
            "type": "object",
            "properties": {
                "openness": {"type": "integer"},
                "conscientiousness": {"type": "integer"},
                "extraversion": {"type": "integer"},
                "agreeableness": {"type": "integer"},
                "neuroticism": {"type": "integer"},
            },
        },
    },
    "required": ["communication_style", "speech_notes"],
}

# One turn of a Dara-to-Dara proxy conversation.
PROXY: Dict[str, Any] = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
}

# Does a candidate's photo match the user's stated physical preferences?
PHYSICAL: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "meets": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["meets"],
}

# Photo read. Deliberately about what a photo legitimately shows — overall
# vibe, setting, presentation — NOT protected attributes (ethnicity,
# nationality, exact age), which can't be reliably or fairly inferred from a face.
PHOTO_FIT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "impression": {"type": "string"},
        "vibe_tags": {"type": "array", "items": {"type": "string"}},
        "fit_comment": {"type": "string"},
    },
    "required": ["impression", "vibe_tags", "fit_comment"],
}


# ─── Normalizers ─────────────────────────────────────────────────────
def normalize_score(d: Any) -> Dict[str, Any]:
    d = d if isinstance(d, dict) else {}
    try:
        score = int(d.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))
    reasons = d.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    if not isinstance(reasons, list):
        reasons = []
    return {
        "score": score,
        "verdict": str(d.get("verdict") or "Worth a real conversation."),
        "reasons": [str(r) for r in reasons if str(r).strip()][:5],
    }


def normalize_intake(d: Any) -> Dict[str, Any]:
    d = d if isinstance(d, dict) else {}
    needs = d.get("needs") or []
    if isinstance(needs, str):
        needs = [needs]
    if not isinstance(needs, list):
        needs = []
    return {
        "summary": str(d.get("summary") or "").strip(),
        "needs": [str(n).strip() for n in needs if str(n).strip()][:6],
        "safe": bool(d.get("safe", True)),
        "safety_reason": str(d.get("safety_reason") or "").strip(),
    }


def normalize_prescreen(d: Any) -> Dict[str, Any]:
    d = d if isinstance(d, dict) else {}
    return {"safe": bool(d.get("safe", True)), "reason": str(d.get("reason") or "")}


def normalize_messages(d: Any) -> List[str]:
    msgs = d.get("messages") if isinstance(d, dict) else d
    if isinstance(msgs, str):
        msgs = [msgs]
    if not isinstance(msgs, list):
        msgs = []
    return [str(m) for m in msgs if str(m).strip()][:5]


def normalize_physical(d: Any) -> Dict[str, Any]:
    d = d if isinstance(d, dict) else {}
    return {"meets": bool(d.get("meets", True)), "reason": str(d.get("reason") or "").strip()}


def normalize_suggestions(d: Any) -> List[Dict[str, str]]:
    items = d.get("suggestions") if isinstance(d, dict) else d
    if not isinstance(items, list):
        items = []
    out: List[Dict[str, str]] = []
    for it in items:
        if isinstance(it, str):
            text, label = it, ""
        elif isinstance(it, dict):
            text, label = str(it.get("text") or "").strip(), str(it.get("label") or "").strip()
        else:
            continue
        if text:
            out.append({"label": label, "text": text})
    return out[:3]


def normalize_proxy(d: Any) -> str:
    if isinstance(d, dict):
        return str(d.get("message") or "").strip()
    return str(d or "").strip()


def normalize_portrait(d: Any) -> Dict[str, Any]:
    d = d if isinstance(d, dict) else {}

    def _list(key: str, limit: int) -> List[str]:
        v = d.get(key) or []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            v = []
        return [str(x).strip() for x in v if str(x).strip()][:limit]

    bf = d.get("big_five") if isinstance(d.get("big_five"), dict) else {}

    def _score(k):
        try:
            return max(0, min(100, int(bf.get(k))))
        except (TypeError, ValueError):
            return None

    return {
        "interests": _list("interests", 8),
        "values": _list("values", 8),
        "communication_style": str(d.get("communication_style") or "natural").strip(),
        "humor_style": str(d.get("humor_style") or "").strip(),
        "looking_for": str(d.get("looking_for") or "").strip(),
        "dealbreakers": _list("dealbreakers", 6),
        "observations": _list("observations", 6),
        "speech_notes": str(d.get("speech_notes") or "").strip(),
        "recent_messages": _list("recent_messages", 5),
        "vibe": str(d.get("vibe") or "").strip(),
        "big_five": {k: _score(k) for k in
                     ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]},
    }


def normalize_photo_fit(d: Any) -> Dict[str, Any]:
    d = d if isinstance(d, dict) else {}
    tags = d.get("vibe_tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        tags = []
    return {
        "impression": str(d.get("impression") or "").strip(),
        "vibe_tags": [str(t) for t in tags if str(t).strip()][:6],
        "fit_comment": str(d.get("fit_comment") or "").strip(),
    }

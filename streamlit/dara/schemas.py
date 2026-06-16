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

MEDIATION: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "messages": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["messages"],
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

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

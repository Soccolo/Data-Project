"""Mock AI responses for the PoC.

These let the whole app run with zero API keys — useful for demos and for
Streamlit Community Cloud. Every response is generated purpose-by-purpose so
the conversation still feels coherent. Swap to live providers by setting
``DARA_AI_MODE=live`` and supplying a provider key; the call sites don't change.
"""

from __future__ import annotations

import json
import random
from typing import Any, Dict, List, Optional

from .tiers import Purpose

# Deterministic-ish flavour without being identical every turn.
_rng = random.Random(7)

_INTERVIEW_QUESTIONS = [
    "Tell me a little about yourself — what does a good week look like for you?",
    "What pulls your attention lately: a project, a person, a place?",
    "When you click with someone, what is it usually about?",
    "What's something you'd want a match to just *get* about you without explaining?",
    "Last one: what are you actually hoping to find here?",
]

_INTAKE_QUESTIONS = [
    "Thanks for trusting me with this. In your own words, what happened?",
    "How did that land for you — what did it bring up?",
    "What would 'better' look like, even a little?",
    "Is there anything you'd want your partner to understand before we talk it through?",
]

_MEDIATION_TURNS = [
    "Both of you are describing the same evening from two ends of the same rope. "
    "{a} felt unheard; {b} felt managed. Neither is wrong about their own experience.",
    "Here's the knot: the plan changed late, and the change read as 'your time matters less.' "
    "That's the hurt under the logistics.",
    "A small repair that tends to hold: name the change *out loud and early*, and let the other "
    "say what it costs them — before fixing it.",
]


def mock_response(
    purpose: Purpose,
    *,
    system_prompt: str = "",
    user_text: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    schema: Optional[Dict[str, Any]] = None,
    names: Optional[Dict[str, str]] = None,
) -> str:
    """Return a plausible response string for ``purpose``.

    When ``schema`` is set the caller expects JSON, so we return a JSON string
    shaped to match what the real flows parse.
    """
    history = history or []
    names = names or {}
    user_turns = sum(1 for m in history if m.get("role") == "user")

    if purpose == "interview":
        idx = min(user_turns, len(_INTERVIEW_QUESTIONS) - 1)
        lead = "" if user_turns == 0 else _reflect(user_text) + " "
        return lead + _INTERVIEW_QUESTIONS[idx]

    if purpose == "intake":
        if schema:
            return json.dumps({
                "summary": "Felt sidelined by a last-minute change and wants to feel considered and looped in early.",
                "needs": ["to feel considered", "advance notice", "acknowledgement"],
                "safe": True,
                "safety_reason": "",
            })
        idx = min(user_turns, len(_INTAKE_QUESTIONS) - 1)
        lead = "" if user_turns == 0 else _reflect(user_text) + " "
        return lead + _INTAKE_QUESTIONS[idx]

    if purpose == "compatibilityFilter":
        return json.dumps({"compatible": True, "reason": "Overlapping values and complementary energy."})

    if purpose == "prescreen":
        return json.dumps({
            "safe": True,
            "reason": "Everyday relationship friction — appropriate for mediation.",
        })

    if purpose == "score":
        score = _rng.randint(72, 91)
        return json.dumps({
            "score": score,
            "verdict": "Worth a real conversation.",
            "reasons": [
                "You both light up talking about the work you choose, not the work you're handed.",
                "Similar pace — neither of you rushes the getting-to-know-you part.",
                "One healthy difference: they plan, you improvise. That tends to balance.",
            ],
        })

    if purpose == "proxyTurn":
        lines = [
            "ok hi — so what actually pulls your attention these days?",
            "love that. is it the thing itself or the people around it?",
            "honestly same. what does a good weekend look like for you?",
            "noted. i'm more of a long-walk-then-too-much-coffee person",
            "what's something you'd want someone to just get without explaining?",
            "that's a good answer. what tends to make you click with someone?",
            "fair. what are you actually hoping to find here — no wrong answer",
            "i like how you put that. what would you rather do on a first date?",
            "ha, bold. what's a small thing that reliably makes your day better?",
            "ok i'm into this conversation. what's been on your mind lately?",
        ]
        return json.dumps({"message": _rng.choice(lines)}) if schema else _rng.choice(lines)

    if purpose == "mediation":
        a = names.get("a", "Partner A")
        b = names.get("b", "Partner B")
        return json.dumps({"messages": [t.format(a=a, b=b) for t in _MEDIATION_TURNS]})

    if purpose == "takeaway":
        who = names.get("self", "you")
        other = names.get("other", "your partner")
        return (
            f"For {who}: the friction wasn't about the calendar — it was about feeling like an "
            f"afterthought when plans shift. Ask for a heads-up, not a veto.\n\n"
            f"What {other} needs: a moment to flag changes before solving them, so the shift "
            f"doesn't read as dismissal."
        )

    if purpose == "profile":
        return json.dumps({
            "interests": ["good food", "music", "long conversations", "the outdoors"],
            "values": ["curiosity", "honesty", "warmth"],
            "communication_style": "warm, direct, a little playful",
            "humor_style": "dry, self-aware",
            "looking_for": "someone curious who shows up and means it",
            "dealbreakers": ["flakiness", "incuriosity"],
            "observations": ["thinks out loud", "values their people", "open to being surprised"],
            "speech_notes": "relaxed sentences, occasional dash, warm but not gushy, no heavy slang",
            "recent_messages": [
                "honestly that made my whole week, not gonna lie",
                "i'm in — tell me when and where",
                "ok but have you tried the place on the corner? changed my life",
            ],
            "vibe": "approachable, grounded, curious",
            "big_five": {"openness": 78, "conscientiousness": 60, "extraversion": 57,
                         "agreeableness": 72, "neuroticism": 43},
        })

    if purpose == "photoAnalysis":
        if schema:
            return json.dumps({
                "impression": "Warm, candid, outdoorsy — looks relaxed and approachable.",
                "vibe_tags": ["outdoorsy", "warm", "easygoing", "active"],
                "fit_comment": "The laid-back, active energy reads as a good fit for what you described.",
            })
        return "Warm, candid, outdoorsy. Reads as approachable and a little adventurous."

    # Fallback
    return "…"


def _reflect(user_text: Optional[str]) -> str:
    """A tiny acknowledgement so replies don't feel like a fixed script."""
    if not user_text:
        return "Got it."
    snippet = user_text.strip().split(".")[0]
    if len(snippet) > 60:
        snippet = snippet[:57] + "…"
    openers = ["That's a good place to start —", "I hear you —", "Noted —", "Makes sense —"]
    return f"{_rng.choice(openers)} “{snippet}.”"

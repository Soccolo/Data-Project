"""Dating preferences: the option vocabularies plus small helpers, shared by
onboarding, the account editor, and the matchmaking logic so they never drift.

Own attributes live in ``users.basics`` (gender, orientation, age, nationality,
height_cm); what someone is looking for lives in ``users.profile.preferences``.
Both are free-form JSON, so none of this needs a schema migration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

MIN_AGE = 18  # Dating is adults-only.

GENDERS = ["Woman", "Man", "Non-binary", "Other"]
ORIENTATIONS = [
    "Straight", "Gay", "Lesbian", "Bisexual", "Pansexual",
    "Asexual", "Queer", "Questioning", "Prefer not to say",
]
INTERESTED_IN = ["Women", "Men", "Non-binary people", "Everyone"]
INTENTS = [
    "Long-term relationship", "Short-term / casual",
    "New friends", "Still figuring it out",
]

# Map an "interested in" selection to the gender values it should match.
_INTEREST_TO_GENDER = {
    "Women": {"Woman"},
    "Men": {"Man"},
    "Non-binary people": {"Non-binary"},
    "Everyone": {"Woman", "Man", "Non-binary", "Other"},
}


def default_preferences() -> Dict[str, Any]:
    return {
        "interested_in": [],
        "age_min": 18,
        "age_max": 60,
        "height_min_cm": 140,
        "height_max_cm": 210,
        "nationalities": [],   # soft preference — weighed, never a hard gate
        "intent": INTENTS[0],
        "dealbreakers": "",
    }


def wanted_genders(prefs: Dict[str, Any]) -> Set[str]:
    """The set of gender values this user wants to be matched with."""
    out: Set[str] = set()
    for sel in (prefs.get("interested_in") or []):
        out |= _INTEREST_TO_GENDER.get(sel, set())
    return out or set(GENDERS)


def summarize_self(basics: Dict[str, Any]) -> str:
    """A compact prose line describing the user, for AI prompts."""
    bits: List[str] = []
    if basics.get("age"):
        bits.append(f"{basics['age']}")
    if basics.get("gender"):
        bits.append(basics["gender"].lower())
    if basics.get("orientation") and basics["orientation"] != "Prefer not to say":
        bits.append(basics["orientation"].lower())
    if basics.get("job"):
        bits.append(basics["job"])
    if basics.get("nationality"):
        bits.append(basics["nationality"])
    if basics.get("height_cm"):
        bits.append(f"{basics['height_cm']}cm")
    head = ", ".join(bits) if bits else "no details given"
    bio = (basics.get("bio") or "").strip()
    return f"{head}." + (f' Bio: "{bio}"' if bio else "")


def summarize_preferences(prefs: Dict[str, Any]) -> str:
    """A compact prose line describing what the user wants, for AI prompts."""
    p = {**default_preferences(), **(prefs or {})}
    looking = ", ".join(p["interested_in"]) or "anyone"
    parts = [
        f"interested in {looking}",
        f"ages {p['age_min']}–{p['age_max']}",
        f"height {p['height_min_cm']}–{p['height_max_cm']}cm",
        f"intent: {p['intent']}",
    ]
    if p["nationalities"]:
        parts.append("soft preference toward: " + ", ".join(p["nationalities"]))
    if (p.get("dealbreakers") or "").strip():
        parts.append(f"dealbreakers: {p['dealbreakers'].strip()}")
    return "; ".join(parts) + "."

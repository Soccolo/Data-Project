"""In-chat Dara assistant — suggests openers, replies, and date ideas inside a
match conversation. Draws on both people's portraits and the chat so far, and
writes in the user's own casual voice rather than a generic 'AI' tone.
"""

from __future__ import annotations

from typing import Any, Dict, List

from . import schemas
from .ai_client import call_ai
from .tiers import Tier


def _strip_test(name: str) -> str:
    return (name or "").replace(" (Test)", "").strip() or "they"


def _portrait_lines(label: str, person: Dict[str, Any]) -> str:
    basics = person.get("basics") or {}
    port = (person.get("profile") or {}).get("portrait") or person.get("portrait") or {}
    name = _strip_test(basics.get("name") or label)
    bits: List[str] = [f"{label} is {name}."]
    if basics.get("job"):
        bits.append(f"Job: {basics['job']}.")
    if basics.get("bio"):
        bits.append(f"Bio: {basics['bio']}")
    if port.get("interests"):
        bits.append("Interests: " + ", ".join(map(str, port["interests"][:6])) + ".")
    if port.get("values"):
        bits.append("Values: " + ", ".join(map(str, port["values"][:5])) + ".")
    if port.get("vibe"):
        bits.append(f"Vibe: {port['vibe']}.")
    if label == "You" and port.get("speech_notes"):
        bits.append(f"Your texting style: {port['speech_notes']}")
    if label != "You" and port.get("looking_for"):
        bits.append(f"They're looking for: {port['looking_for']}")
    return " ".join(bits)


_KIND = {
    "opener": ("Suggest opening messages to start the conversation. Each should reference "
               "something specific and real about them — an interest, their job, a line from "
               "their bio — so it never reads as a generic 'hey'."),
    "reply": ("Suggest replies the user could send next. Each should move things forward: pick "
              "up on what they just said, ask a genuine question, or share something small. "
              "Vary the angle across the options (one warm, one curious, one lightly playful)."),
    "date": ("Suggest specific, low-pressure date ideas grounded in interests the two actually "
             "share. Name a concrete kind of place or activity and keep it casual — a coffee, a "
             "walk, a particular sort of spot — not an elaborate itinerary."),
}


def suggest(kind: str, me: Dict[str, Any], other: Dict[str, Any],
            history: List[Dict[str, str]], tier: Tier = "free",
            client: Any = None) -> List[Dict[str, str]]:
    """Return up to 3 {label, text} message suggestions for the chat."""
    kind = kind if kind in _KIND else "reply"
    me_name = _strip_test(((me.get("basics") or {}).get("name")) or "You")
    other_name = _strip_test(((other.get("basics") or {}).get("name")) or "them")

    system = (
        f"You are Dara, helping {me_name} message {other_name}, someone they matched with on a "
        f"dating app. {_KIND[kind]}\n\n"
        "Write each message in the FIRST PERSON, the way the user would actually text it — "
        "natural, casual, short, in their own voice (match the texting style noted below if "
        "one is given). Do NOT sound like an AI, do NOT be formal, do NOT over-explain.\n\n"
        "CRITICAL — never invent facts. Use ONLY details that appear below or in the chat. If "
        "the bio says 'pastry chef', you may mention baking; do NOT inflate it to 'owns a "
        "bakery'. If a detail isn't stated, don't assume it — keep the message general rather "
        "than fabricating specifics. Don't put words in the other person's mouth.\n\n"
        "Give each suggestion a 2–4 word label describing its angle. Return 2–3 options."
    )

    ctx: List[str] = [_portrait_lines("You", me), _portrait_lines("They", other)]
    if history:
        recent = history[-10:]
        lines = "\n".join(f"{(h.get('from') or '?').upper()}: {h.get('text', '')}" for h in recent)
        ctx.append("Conversation so far:\n" + lines)
    else:
        ctx.append("There are no messages yet — this is the very start of the chat.")

    try:
        raw = call_ai(purpose="chatAssist", system_prompt=system, tier=tier,
                      user_text="\n\n".join(ctx), schema=schemas.SUGGESTIONS, max_tokens=600)
        return schemas.normalize_suggestions(raw)
    except Exception:  # noqa: BLE001
        return []

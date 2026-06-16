"""Conflict sessions: two users, a Dara on each side.

Reuses the conflict_sessions table — RLS (cs_select_party / cs_update_party)
already limits every row to the two named parties, so these calls run with each
user's own client.

Flow: the inviter starts a session naming the invitee → the invitee accepts →
each party privately does intake with their own Dara → when both intakes are
done (and safe) the two Daras mediate → each party gets a takeaway.

This module is pure data access. The AI steps (intake interview, summary +
safety, the Dara-to-Dara mediation, takeaways) live in the engine/flow layer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

_TABLE = "conflict_sessions"

_EMPTY_SIDE = {"messages": [], "summary": None, "safetyFlag": None, "complete": False}


def _name(profile: Optional[Dict[str, Any]], default: str = "Someone") -> str:
    return ((profile or {}).get("basics") or {}).get("name") or default


def _find_user(client: Any, username: str) -> Optional[Dict[str, Any]]:
    res = (client.table("users").select("id,username,basics")
           .eq("username", username.strip().lower()).limit(1).execute())
    return (res.data or [None])[0]


def create_session(client: Any, me: Dict[str, Any], invitee_username: str, topic: str
                   ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Invite another user (by username) to mediate a conflict. Returns (row, error)."""
    invitee = _find_user(client, invitee_username)
    if not invitee:
        return None, "No user with that username."
    if invitee["id"] == me.get("id"):
        return None, "You can't start a mediation with yourself."
    row = {
        "inviter_id": me["id"], "inviter_username": me.get("username", ""), "inviter_name": _name(me),
        "invitee_id": invitee["id"], "invitee_username": invitee["username"],
        "invitee_name": (invitee.get("basics") or {}).get("name") or invitee["username"],
        "topic": topic.strip(), "status": "invited",
    }
    res = client.table(_TABLE).insert(row).execute()
    return (res.data or [row])[0], None


def list_sessions(client: Any, uid: str) -> List[Dict[str, Any]]:
    res = (client.table(_TABLE).select("*")
           .or_(f"inviter_id.eq.{uid},invitee_id.eq.{uid}")
           .order("updated_at", desc=True).execute())
    return res.data or []


def get_session(client: Any, sid: str) -> Optional[Dict[str, Any]]:
    res = client.table(_TABLE).select("*").eq("id", sid).limit(1).execute()
    return (res.data or [None])[0]


def role_of(session: Dict[str, Any], uid: str) -> str:
    return "inviter" if session.get("inviter_id") == uid else "invitee"


def other_role(role: str) -> str:
    return "invitee" if role == "inviter" else "inviter"


def name_of(session: Dict[str, Any], role: str) -> str:
    return session.get(f"{role}_name") or "Someone"


def side(session: Dict[str, Any], role: str) -> Dict[str, Any]:
    return (session.get("intake") or {}).get(role) or dict(_EMPTY_SIDE)


def both_intakes_complete(session: Dict[str, Any]) -> bool:
    intake = session.get("intake") or {}
    return bool((intake.get("inviter") or {}).get("complete")
                and (intake.get("invitee") or {}).get("complete"))


# ─── mutations ───────────────────────────────────────────────────────
def _update(client: Any, sid: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    res = client.table(_TABLE).update(fields).eq("id", sid).execute()
    return (res.data or [{}])[0]


def respond_invite(client: Any, sid: str, accept: bool) -> Dict[str, Any]:
    return _update(client, sid, {"status": "intake" if accept else "declined"})


def append_intake_message(client: Any, session: Dict[str, Any], role: str,
                          msg_role: str, content: str) -> Dict[str, Any]:
    intake = dict(session.get("intake") or {})
    s = dict(intake.get(role) or _EMPTY_SIDE)
    msgs = list(s.get("messages") or [])
    msgs.append({"role": msg_role, "content": content})
    s["messages"] = msgs
    intake[role] = s
    return _update(client, session["id"], {"intake": intake})


def complete_intake(client: Any, session: Dict[str, Any], role: str, summary: str,
                    safe: bool, safety_reason: str = "") -> Dict[str, Any]:
    intake = dict(session.get("intake") or {})
    s = dict(intake.get(role) or _EMPTY_SIDE)
    s["summary"] = summary
    s["safetyFlag"] = None if safe else (safety_reason or "flagged")
    s["complete"] = True
    intake[role] = s
    fields: Dict[str, Any] = {"intake": intake}
    if not safe:
        fields["status"] = "safety-stopped"
        fields["safety_reason"] = safety_reason
    return _update(client, session["id"], fields)


def save_mediation(client: Any, sid: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    return _update(client, sid, {
        "mediation": {"messages": messages, "inviterWantsWrap": False,
                      "inviteeWantsWrap": False, "wrappedAt": None, "wrappedReason": None},
        "status": "mediating",
    })


def save_takeaways(client: Any, sid: str, inviter_takeaway: str, invitee_takeaway: str) -> Dict[str, Any]:
    return _update(client, sid, {
        "takeaways": {"inviter": inviter_takeaway, "invitee": invitee_takeaway},
        "status": "complete",
    })

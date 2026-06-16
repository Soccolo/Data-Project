"""Connections + chat between real users.

A "connect" is a meet request (reusing the meets table). When the other person
accepts — or has already requested you — it becomes a match, and the two can
exchange messages. RLS on meets/messages already restricts everything to the
two parties, so these calls run with each user's own client.

Seed/simulated candidates aren't real rows, so they don't pass through here —
the flow layer handles those as a local persona chat.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _name(profile: Optional[Dict[str, Any]], default: str = "Someone") -> str:
    return ((profile or {}).get("basics") or {}).get("name") or default


def is_real_user_id(candidate_id: Optional[str]) -> bool:
    """Seed candidates use ids like 'seed_mei' and simulated ones have none;
    real users are UUIDs from Supabase."""
    return bool(candidate_id) and not str(candidate_id).startswith("seed_")


def _between(client: Any, a: str, b: str) -> Optional[Dict[str, Any]]:
    res = (client.table("meets").select("*")
           .or_(f"and(proposer_id.eq.{a},recipient_id.eq.{b}),"
                f"and(proposer_id.eq.{b},recipient_id.eq.{a})")
           .limit(1).execute())
    return (res.data or [None])[0]


def _set_status(client: Any, meet_id: str, status: str) -> Dict[str, Any]:
    res = client.table("meets").update({"status": status}).eq("id", meet_id).execute()
    return (res.data or [{}])[0]


def connect(client: Any, me: Dict[str, Any], candidate: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    """Send a connect request, or instant-match if the candidate already
    requested you. Returns {"meet": row, "matched": bool}."""
    me_id, cand_id = me["id"], candidate["id"]
    existing = _between(client, me_id, cand_id)
    if existing:
        # They already reached out to you and it's pending → accepting completes the match.
        if existing["status"] == "pending" and existing["recipient_id"] == me_id:
            return {"meet": _set_status(client, existing["id"], "accepted"), "matched": True}
        return {"meet": existing, "matched": existing["status"] == "accepted"}

    row = {
        "proposer_id": me_id, "recipient_id": cand_id,
        "proposer_name": _name(me), "recipient_name": _name(candidate),
        "message": note or None, "status": "pending",
    }
    res = client.table("meets").insert(row).execute()
    return {"meet": (res.data or [row])[0], "matched": False}


def accept(client: Any, meet_id: str) -> Dict[str, Any]:
    return _set_status(client, meet_id, "accepted")


def decline(client: Any, meet_id: str) -> Dict[str, Any]:
    return _set_status(client, meet_id, "declined")


def incoming_requests(client: Any, uid: str) -> List[Dict[str, Any]]:
    res = (client.table("meets").select("*")
           .eq("recipient_id", uid).eq("status", "pending").execute())
    return res.data or []


def outgoing_requests(client: Any, uid: str) -> List[Dict[str, Any]]:
    res = (client.table("meets").select("*")
           .eq("proposer_id", uid).eq("status", "pending").execute())
    return res.data or []


def matches(client: Any, uid: str) -> List[Dict[str, Any]]:
    res = (client.table("meets").select("*").eq("status", "accepted")
           .or_(f"proposer_id.eq.{uid},recipient_id.eq.{uid}").execute())
    return res.data or []


def other_party(meet: Dict[str, Any], uid: str) -> Tuple[str, str]:
    """(id, name) of the person who isn't `uid`."""
    if meet.get("proposer_id") == uid:
        return meet.get("recipient_id"), meet.get("recipient_name", "Them")
    return meet.get("proposer_id"), meet.get("proposer_name", "Them")


def send_message(client: Any, meet_id: str, sender_id: str, body: str) -> Dict[str, Any]:
    res = client.table("messages").insert(
        {"meet_id": meet_id, "sender_id": sender_id, "body": body}
    ).execute()
    return (res.data or [{}])[0]


def list_messages(client: Any, meet_id: str) -> List[Dict[str, Any]]:
    res = (client.table("messages").select("*")
           .eq("meet_id", meet_id).order("created_at").execute())
    return res.data or []

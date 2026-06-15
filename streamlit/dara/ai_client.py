"""AI client.

The Dara call sites (interview, mediation, score, ...) call ``call_ai`` with
a ``purpose`` instead of hitting Anthropic/Google directly. ``call_ai`` resolves
the model from the (tier, purpose) routing table and dispatches to the right
provider — or to canned mock responses when ``DARA_AI_MODE=mock`` (the PoC
default), so the app runs with zero keys.

This is the server-side equivalent of the web scaffold's ``/api/llm`` route +
browser ``callAI`` collapsed into one function, since Streamlit has no
browser/server split.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .config import settings
from .mock import mock_response
from .providers import call_provider
from .tiers import ModelChoice, Purpose, Tier, effective_tier, model_for


def resolve_model(purpose: Purpose, tier: Tier = "free", partner_tier: Optional[Tier] = None) -> ModelChoice:
    """The (tier, purpose) → model decision, exposed so the UI can show which
    model a call routes to (even in mock mode, for transparency)."""
    resolved_partner = partner_tier or tier
    eff_tier = effective_tier(tier, resolved_partner) if purpose in ("proxyTurn", "mediation") else tier
    return model_for(eff_tier, purpose)


def call_ai(
    *,
    purpose: Purpose,
    system_prompt: str,
    tier: Tier = "free",
    user_text: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    media: Optional[List[Dict[str, str]]] = None,
    schema: Optional[Dict[str, Any]] = None,
    partner_tier: Optional[Tier] = None,
    names: Optional[Dict[str, str]] = None,
    max_tokens: Optional[int] = None,
) -> Any:
    """Route a single AI call and return the model output.

    If ``schema`` is provided the response is expected to be JSON and is parsed
    loosely; otherwise the raw text is returned.
    """
    if settings.ai_mode == "mock":
        text = mock_response(
            purpose,
            system_prompt=system_prompt,
            user_text=user_text,
            history=history,
            schema=schema,
            names=names,
        )
    else:
        choice = resolve_model(purpose, tier, partner_tier)
        body: Dict[str, Any] = {
            "purpose": purpose,
            "systemPrompt": system_prompt,
            "userText": user_text,
            "history": history,
            "media": media,
            "schema": schema,
            "partnerTier": partner_tier or tier,
            "max_tokens": max_tokens,
        }
        text = call_provider(choice, body)

    # If a schema was requested, the response should be JSON. Parse loosely.
    if schema:
        return parse_json_loose(text)
    return text


def parse_json_loose(text: str) -> Any:
    """Pulled from the artifact's existing parseJsonLoose."""
    if not text:
        return {}
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        return json.loads(clean)
    except Exception:
        pass
    first = clean.find("{")
    last = clean.rfind("}")
    if first >= 0 and last > first:
        try:
            return json.loads(clean[first:last + 1])
        except Exception:
            pass
    return {}

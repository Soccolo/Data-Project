"""Dara — Streamlit scaffold package.

AI matchmaker and mediator. Mirrors the architecture of the web scaffold:
tier-based model routing, multi-provider AI calls, and a Supabase backend
governed by row-level security.
"""

from .ai_client import call_ai, parse_json_loose, resolve_model
from .tiers import ModelChoice, Purpose, Tier, effective_tier, model_for

__all__ = [
    "call_ai",
    "parse_json_loose",
    "resolve_model",
    "model_for",
    "effective_tier",
    "ModelChoice",
    "Purpose",
    "Tier",
]

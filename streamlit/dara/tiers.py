"""Tier-based model routing.

Each AI call site identifies itself with a ``purpose``. The app picks the
model based on (tier, purpose). Free users get Gemini Flash for everything;
paid users get Claude on the calls where it matters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

Tier = Literal["free", "pro", "x"]

Purpose = Literal[
    "interview",            # Dara learning who you are — voice matters
    "profile",              # distil the interview into a stored JSON portrait
    "photoAnalysis",        # vision call
    "compatibilityFilter",  # cheap soft gate before proxy
    "proxyTurn",            # Dara-to-Dara matching conversation (HIGH VOLUME)
    "score",                # post-match verdict shown to user
    "prescreen",            # safety classification on a conflict topic
    "intake",               # private conflict intake with own Dara
    "mediation",            # Dara-to-Dara conflict mediation (HIGH VOLUME)
    "takeaway",             # synthesised takeaways for each partner
]

Provider = Literal["google", "anthropic", "deepseek"]


@dataclass(frozen=True)
class ModelChoice:
    provider: Provider
    model: str
    # What we tell the user this call is using (helps with debugging + transparency)
    label: str


# Routing table. Edit this to tune the tradeoff between cost and quality.
#
# Heuristics applied:
# - free: all Gemini 2.5 Flash. Cheapest path. Quality is fine for most
#   tasks; matching pairs of free-tier Daras will both speak Flash.
# - pro: Claude Sonnet 4.6 on the personal/sensitive calls the user
#   reads (interview, intake, score, takeaway). Gemini Flash on the
#   volume-heavy shared calls (proxy, mediation) since both partners
#   read the transcript in English regardless of preference.
# - x: All Sonnet. Mediation upgraded to Sonnet for relationship work
#   that benefits from extra nuance.
_ROUTES: Dict[Tier, Dict[Purpose, ModelChoice]] = {
    "free": {
        "interview":           ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "profile":             ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "photoAnalysis":       ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "compatibilityFilter": ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "proxyTurn":           ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "score":               ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "prescreen":           ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "intake":              ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "mediation":           ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "takeaway":            ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
    },
    "pro": {
        "interview":           ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "profile":             ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "photoAnalysis":       ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "compatibilityFilter": ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "proxyTurn":           ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "score":               ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "prescreen":           ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "intake":              ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "mediation":           ModelChoice("google",    "gemini-2.5-flash",          "Gemini Flash"),
        "takeaway":            ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
    },
    "x": {
        "interview":           ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "profile":             ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "photoAnalysis":       ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "compatibilityFilter": ModelChoice("anthropic", "claude-haiku-4-5-20251001", "Claude Haiku"),
        "proxyTurn":           ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "score":               ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "prescreen":           ModelChoice("anthropic", "claude-haiku-4-5-20251001", "Claude Haiku"),
        "intake":              ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "mediation":           ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
        "takeaway":            ModelChoice("anthropic", "claude-sonnet-4-6",         "Claude Sonnet"),
    },
}


def model_for(tier: Tier, purpose: Purpose) -> ModelChoice:
    routes = _ROUTES.get(tier) or _ROUTES["free"]
    return routes.get(purpose) or _ROUTES["free"][purpose]


def effective_tier(tier_a: Tier, tier_b: Tier) -> Tier:
    """For two-party calls (Dara-to-Dara proxy, mediation), the "higher" of
    the two users' tiers determines the model. So a pro user matching with a
    free user gets the pro experience.
    """
    rank = {"free": 0, "pro": 1, "x": 2}
    return tier_a if rank[tier_a] >= rank[tier_b] else tier_b


@dataclass(frozen=True)
class TierInfo:
    key: Tier
    name: str
    price: str          # display only — billing is simulated in the PoC
    blurb: str
    perks: tuple[str, ...]


# Presentation metadata for the billing page. The routing table above is what
# actually changes behaviour per tier; this just describes it to the user.
TIER_INFO: Dict[Tier, TierInfo] = {
    "free": TierInfo(
        "free", "Free", "$0",
        "Everything runs on Gemini Flash. Plenty to find your footing.",
        ("Unlimited interviews & mediation", "Gemini Flash on every call", "Matches with other free users"),
    ),
    "pro": TierInfo(
        "pro", "Pro", "$12/mo",
        "Claude Sonnet on the calls you actually read — interviews, intakes, scores, takeaways.",
        ("Everything in Free", "Claude Sonnet on personal calls", "Higher-quality match verdicts"),
    ),
    "x": TierInfo(
        "x", "X", "$29/mo",
        "Claude across the board, including the high-volume Dara-to-Dara conversations.",
        ("Everything in Pro", "Claude on proxy & mediation turns", "Haiku-powered safety gating"),
    ),
}

TIER_ORDER: tuple[Tier, ...] = ("free", "pro", "x")

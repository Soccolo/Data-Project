"""Seed test candidates — a small built-in pool so matchmaking has real
profiles to run against before there are other registered users.

Mirrors Mira's CANDIDATES: each has ``basics`` (the same fields a real user's
profile uses) and a structured ``portrait`` (the JSON personality sketch that
later drives Dara-to-Dara proxy conversations). Shaped exactly like a real
``users`` row so the matcher can treat seed and real candidates identically.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Each portrait mirrors what `distill_portrait` produces from an interview, so
# seed candidates and interviewed users are interchangeable in the proxy step.
SEED_CANDIDATES: List[Dict[str, Any]] = [
    {
        "id": "seed_mei",
        "username": "mei",
        "is_seed": True,
        "basics": {
            "name": "Mei", "gender": "Woman", "orientation": "Bisexual", "age": 26,
            "nationality": "Chinese", "job": "Philosophy PhD candidate", "height_cm": 165,
            "bio": "Philosophy postgrad. Surrealism nerd. Talks too much about dim sum.",
        },
        "profile": {
            "preferences": {"interested_in": ["Men", "Women"], "age_min": 24, "age_max": 34,
                            "height_min_cm": 165, "height_max_cm": 200, "intent": "Long-term relationship"},
            "portrait": {
                "interests": ["surrealist film", "continental philosophy", "cooking", "board games"],
                "values": ["curiosity", "absurdity", "depth", "play"],
                "communication_style": "playful, layered, quick",
                "humor_style": "absurd, self-aware, slightly chaotic",
                "looking_for": "someone whose mind is restless and who doesn't take themselves too seriously",
                "dealbreakers": ["rigid thinkers", "people who take themselves too seriously"],
                "observations": ["quotes Borges and SpongeBob in the same breath", "ambivalent about academia", "genuinely warm"],
                "speech_notes": "lowercase often, em-dashes everywhere, sentence fragments, swerves between highbrow references and goofy slang, occasional 'lol' or 'honestly'",
                "recent_messages": [
                    "honestly i think most people pretend deleuze is harder than he is — like it's just vibes",
                    "havent slept much. brain is goo. but in a good way maybe",
                    "ok but the dim sum near goodge street is genuinely transcendent",
                ],
                "vibe": "playful, a little eccentric, intellectual warmth",
            },
        },
        "_photos": [],
    },
    {
        "id": "seed_yuki",
        "username": "yuki",
        "is_seed": True,
        "basics": {
            "name": "Yuki", "gender": "Woman", "orientation": "Straight", "age": 27,
            "nationality": "Japanese", "job": "Freelance photographer", "height_cm": 162,
            "bio": "Photographer. Quiet most of the time, then suddenly not.",
        },
        "profile": {
            "preferences": {"interested_in": ["Men"], "age_min": 26, "age_max": 35,
                            "height_min_cm": 165, "height_max_cm": 200, "intent": "Long-term relationship"},
            "portrait": {
                "interests": ["film photography", "jazz", "long walks", "small bookshops"],
                "values": ["quiet attention", "craft", "authenticity"],
                "communication_style": "measured, warm, observant",
                "humor_style": "dry, occasional",
                "looking_for": "a thoughtful person who can sit in silence comfortably",
                "dealbreakers": ["loud insecurity", "always-on personalities"],
                "observations": ["notices small things", "private but not closed off", "cares deeply about her work"],
                "speech_notes": "careful complete sentences, proper punctuation, short paragraphs, occasional ellipsis when she trails off, no slang, gentle",
                "recent_messages": [
                    "I think the city sounds different in autumn. I notice it most walking to the market in the morning.",
                    "Mostly fine. Working on a series about hands.",
                    "It's a little late tonight... maybe tomorrow?",
                ],
                "vibe": "quiet, composed, artistic",
            },
        },
        "_photos": [],
    },
    {
        "id": "seed_priya",
        "username": "priya",
        "is_seed": True,
        "basics": {
            "name": "Priya", "gender": "Woman", "orientation": "Bisexual", "age": 29,
            "nationality": "British-Indian", "job": "Human rights lawyer", "height_cm": 170,
            "bio": "Human rights lawyer. Cooks aggressively. Always traveling.",
        },
        "profile": {
            "preferences": {"interested_in": ["Men", "Women"], "age_min": 27, "age_max": 38,
                            "height_min_cm": 160, "height_max_cm": 205, "intent": "Long-term relationship"},
            "portrait": {
                "interests": ["policy", "cooking", "travel", "literature", "climbing"],
                "values": ["justice", "family", "depth", "adventure"],
                "communication_style": "warm, articulate, direct",
                "humor_style": "sharp, observational",
                "looking_for": "someone substantial — career, values, willing to engage",
                "dealbreakers": ["emotional unavailability", "casual cruelty"],
                "observations": ["serious without being heavy", "protective of close people", "curious about the world"],
                "speech_notes": "full sentences, proper punctuation, occasional exclamation marks when she's into something, warm directness with sharp asides, sometimes caps for emphasis",
                "recent_messages": [
                    "Honestly the policy stuff has been brutal this month — but I love it. Tired in a good way.",
                    "We HAVE to go to that new Tamil place in Tooting. I'm telling you. It's life-changing.",
                    "Saturday could work, yeah. Bring something to argue about.",
                ],
                "vibe": "warm, grounded, vibrant",
            },
        },
        "_photos": [],
    },
    {
        "id": "seed_marcus",
        "username": "marcus",
        "is_seed": True,
        "basics": {
            "name": "Marcus", "gender": "Man", "orientation": "Gay", "age": 31,
            "nationality": "British", "job": "M&A analyst", "height_cm": 185,
            "bio": "Finance by day, novel-in-progress by night. Bad at sports.",
        },
        "profile": {
            "preferences": {"interested_in": ["Men"], "age_min": 27, "age_max": 40,
                            "height_min_cm": 165, "height_max_cm": 200, "intent": "Long-term relationship"},
            "portrait": {
                "interests": ["novels", "classical music", "cooking", "long debates"],
                "values": ["ambition", "craft", "loyalty", "intellect"],
                "communication_style": "considered, dry, precise",
                "humor_style": "deadpan, literary",
                "looking_for": "someone with their own centre of gravity who'll still show up",
                "dealbreakers": ["flakiness", "incuriosity"],
                "observations": ["more romantic than the job suggests", "reads constantly", "guards his time"],
                "speech_notes": "complete sentences, careful word choice, a dry aside per message, rarely uses emoji, slightly formal even when warm",
                "recent_messages": [
                    "Survived the quarter-close. Rewarded myself with eighty pages of a very slow novel.",
                    "I cook to decompress. Tonight: an ambitious ragù, modest expectations.",
                    "Free Thursday. I'll even pretend to enjoy a walk.",
                ],
                "vibe": "composed, literary, quietly warm",
            },
        },
        "_photos": [],
    },
]


def seed_candidates() -> List[Dict[str, Any]]:
    """Deep-ish copies so callers can annotate without mutating the constants."""
    return [
        {**c, "basics": dict(c["basics"]),
         "profile": {**c["profile"], "portrait": dict(c["profile"]["portrait"])}}
        for c in SEED_CANDIDATES
    ]

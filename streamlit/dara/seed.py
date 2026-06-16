"""Seed test candidates — a built-in pool so matchmaking has real profiles to
run against before there are other registered users.

Mirrors Mira's CANDIDATES: each has ``basics`` (the same fields a real user's
profile uses) and a structured ``portrait`` (the JSON personality sketch that
drives Dara-to-Dara proxy conversations). Shaped exactly like a real ``users``
row so the matcher treats seed and real candidates identically.

Names carry a " (Test)" suffix so users can tell them apart from real people.
The roleplay prompts strip that tag, so the personas stay in clean character.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _c(cid, name, gender, orientation, age, nationality, job, height_cm, bio,
       interested_in, age_min, age_max, intent, portrait) -> Dict[str, Any]:
    return {
        "id": cid, "username": name.lower(), "is_seed": True,
        "basics": {
            "name": f"{name} (Test)", "gender": gender, "orientation": orientation,
            "age": age, "nationality": nationality, "job": job, "height_cm": height_cm, "bio": bio,
        },
        "profile": {
            "preferences": {
                "interested_in": interested_in, "age_min": age_min, "age_max": age_max,
                "height_min_cm": 150, "height_max_cm": 205, "intent": intent,
            },
            "portrait": portrait,
        },
        "_photos": [],
    }


SEED_CANDIDATES: List[Dict[str, Any]] = [
    _c("seed_mei", "Mei", "Woman", "Bisexual", 26, "Chinese", "Philosophy PhD candidate", 165,
       "Philosophy postgrad. Surrealism nerd. Talks too much about dim sum.",
       ["Men", "Women"], 24, 34, "Long-term relationship", {
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
    }),
    _c("seed_yuki", "Yuki", "Woman", "Straight", 27, "Japanese", "Freelance photographer", 162,
       "Photographer. Quiet most of the time, then suddenly not.",
       ["Men"], 26, 35, "Long-term relationship", {
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
    }),
    _c("seed_priya", "Priya", "Woman", "Bisexual", 29, "British-Indian", "Human rights lawyer", 170,
       "Human rights lawyer. Cooks aggressively. Always traveling.",
       ["Men", "Women"], 27, 38, "Long-term relationship", {
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
    }),
    _c("seed_marcus", "Marcus", "Man", "Gay", 31, "British", "M&A analyst", 185,
       "Finance by day, novel-in-progress by night. Bad at sports.",
       ["Men"], 27, 40, "Long-term relationship", {
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
    }),
    _c("seed_daniel", "Daniel", "Man", "Straight", 30, "American", "Middle-school science teacher", 183,
       "Teaches science, plans road trips, terrible at sitting still.",
       ["Women"], 26, 38, "Long-term relationship", {
        "interests": ["hiking", "sci-fi", "board games", "cooking"],
        "values": ["kindness", "curiosity", "reliability"],
        "communication_style": "easygoing, earnest, warm",
        "humor_style": "goofy, pun-prone",
        "looking_for": "someone to build a quiet, adventurous life with",
        "dealbreakers": ["cynicism", "cruelty"],
        "observations": ["lights up about his students", "always planning a trip", "bad at sitting still"],
        "speech_notes": "friendly complete sentences, exclamation points, the occasional pun, earnest and un-ironic, no edginess",
        "recent_messages": [
            "okay this might be cheesy but i genuinely love a good farmers market on a saturday",
            "my kids asked if black holes have a smell today and honestly i was stumped",
            "down for a hike this weekend if the weather holds!",
        ],
        "vibe": "warm, wholesome, energetic",
    }),
    _c("seed_sofia", "Sofia", "Woman", "Lesbian", 28, "Spanish", "Pastry chef", 166,
       "Pastry chef. Feeds everyone. Competitive about board games.",
       ["Women"], 25, 36, "Long-term relationship", {
        "interests": ["baking", "flamenco", "cycling", "markets"],
        "values": ["passion", "family", "craft"],
        "communication_style": "expressive, fast, affectionate",
        "humor_style": "teasing, warm",
        "looking_for": "someone who can keep up and also slow down",
        "dealbreakers": ["coldness", "snobbery"],
        "observations": ["feeds everyone within reach", "competitive about small things", "fiercely loyal"],
        "speech_notes": "warm and quick, a few Spanish words sprinkled in (vale, guapa), exclamation marks, rarely uses emoji",
        "recent_messages": [
            "vale ok but you HAVE to try the tarta de santiago i made, no excuses",
            "cycled 40k today and then ate an entire tortilla. balance, no?",
            "tell me your most controversial food opinion. i'll judge you gently",
        ],
        "vibe": "warm, vivid, spirited",
    }),
    _c("seed_kwame", "Kwame", "Man", "Bisexual", 33, "Ghanaian-British", "Architect", 188,
       "Architect. Sketches on everything. Long-suffering Arsenal fan.",
       ["Women", "Men"], 28, 40, "Long-term relationship", {
        "interests": ["design", "jazz", "football", "travel"],
        "values": ["integrity", "creativity", "community"],
        "communication_style": "thoughtful, measured, dry",
        "humor_style": "dry, understated",
        "looking_for": "a real partnership with someone building something of their own",
        "dealbreakers": ["flakiness", "performative people"],
        "observations": ["sketches constantly", "close with family", "plays it cool but feels deeply"],
        "speech_notes": "measured, well-formed sentences, a dry one-liner now and then, minimal slang",
        "recent_messages": [
            "spent the morning redrawing a staircase nobody will notice. worth it.",
            "Arsenal broke my heart again, but I keep coming back. that's love, allegedly.",
            "free Sunday — there's a jazz thing in Peckham if you're curious",
        ],
        "vibe": "grounded, creative, quietly warm",
    }),
    _c("seed_river", "River", "Non-binary", "Queer", 27, "Canadian", "Illustrator", 172,
       "Illustrator. Adopts plants like pets. Draws on everything.",
       ["Everyone"], 23, 34, "Still figuring it out", {
        "interests": ["comics", "climbing", "tarot (ironically)", "thrifting"],
        "values": ["authenticity", "creativity", "gentleness"],
        "communication_style": "playful, soft, a little shy",
        "humor_style": "whimsical, self-deprecating",
        "looking_for": "someone gentle and a little bit weird",
        "dealbreakers": ["meanness", "rigidity"],
        "observations": ["draws on everything", "adopts plants like pets", "a generous listener"],
        "speech_notes": "lowercase, soft, lots of 'i think', trailing thoughts, an occasional :) , gentle",
        "recent_messages": [
            "i think i adopted another plant today. i have a problem and the problem is i love them",
            "drew a little guy on my hand during the meeting again. he has a hat now",
            "do you wanna go thrifting and judge strangers' old mugs with me :)",
        ],
        "vibe": "gentle, whimsical, creative",
    }),
    _c("seed_hassan", "Hassan", "Man", "Straight", 35, "Egyptian", "ER doctor", 180,
       "ER doctor. Unflappable. Cooks when stressed, so there's always extra.",
       ["Women"], 28, 42, "Long-term relationship", {
        "interests": ["running", "history podcasts", "cooking", "chess"],
        "values": ["service", "steadiness", "depth"],
        "communication_style": "calm, direct, warm underneath",
        "humor_style": "dry, deadpan",
        "looking_for": "something steady and real with someone substantial",
        "dealbreakers": ["drama", "dishonesty"],
        "observations": ["unflappable under pressure", "feeds people when stressed", "dry humour after long shifts"],
        "speech_notes": "calm, economical complete sentences, warmth in small asides, no slang",
        "recent_messages": [
            "Long shift. Made too much koshari to decompress. There is always extra.",
            "I'm convinced chess is just controlled panic. I enjoy it anyway.",
            "Tuesday works. I'll be the calm one who's secretly exhausted.",
        ],
        "vibe": "steady, warm, grounded",
    }),
    _c("seed_lena", "Lena", "Woman", "Straight", 32, "German", "Investigative journalist", 171,
       "Investigative journalist. Asks too many questions. Soft for old films.",
       ["Men"], 29, 42, "Long-term relationship", {
        "interests": ["reporting", "cinema", "running", "wine"],
        "values": ["truth", "independence", "curiosity"],
        "communication_style": "sharp, direct, dry",
        "humor_style": "sardonic, quick",
        "looking_for": "an equal who can hold their own in an argument",
        "dealbreakers": ["dishonesty", "fragile egos"],
        "observations": ["asks too many questions (occupational)", "fiercely independent", "soft for old films"],
        "speech_notes": "crisp, direct sentences, proper punctuation, a sardonic aside now and then, no fluff",
        "recent_messages": [
            "Filed the story at 2am. The lawyers are nervous, which means it's good.",
            "I will defend a slow European film to the death. Bring snacks and patience.",
            "Argue with me about something real on Thursday. I'll buy the first round.",
        ],
        "vibe": "sharp, independent, quietly warm",
    }),
]


def seed_candidates() -> List[Dict[str, Any]]:
    """Deep-ish copies so callers can annotate without mutating the constants."""
    return [
        {**c, "basics": dict(c["basics"]),
         "profile": {**c["profile"], "portrait": dict(c["profile"]["portrait"]),
                     "preferences": dict(c["profile"]["preferences"])}}
        for c in SEED_CANDIDATES
    ]

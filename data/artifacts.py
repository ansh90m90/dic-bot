"""Sealed Artifacts — equipable items with perks and dangerous drawbacks.

Every artifact is a data dict. ``modifiers`` is what the engine actually
applies:

* ``digestion_multiplier`` — multiplier on digestion gain while equipped.
* ``message_delete_ratio`` — fraction of the user's messages deleted.
* ``corruption_per_day``   — corruption gained per day while equipped.
* ``sanity_drain_per_day`` — sanity lost per day while equipped (and offline).
* ``gold_multiplier``      — multiplier on gold earned while equipped.

Grades descend from 0 (divine) to 3 (minor).
"""
from __future__ import annotations

from typing import Dict, List

# key, name, grade, effect (perk), curse (drawback), modifiers
_RAW: List[Dict] = [
    {
        "key": "1-010",
        "name": "Mucus of the True Creator",
        "grade": 1,
        "effect": "Doubles the digestion of your potion (2x XP).",
        "curse": "One in every ten of your messages is devoured; +5 corruption each day.",
        "modifiers": {
            "digestion_multiplier": 2.0,
            "message_delete_ratio": 0.1,
            "corruption_per_day": 5.0,
        },
    },
    {
        "key": "1-042",
        "name": "Beyonder's Dream Lens",
        "grade": 1,
        "effect": "Doubles gold earned from events and trades.",
        "curse": "Drains 3 sanity per day while worn; nightmares of the gray fog.",
        "modifiers": {
            "gold_multiplier": 2.0,
            "sanity_drain_per_day": 3.0,
        },
    },
    {
        "key": "2-021",
        "name": "Scabbard of the Silver Knight",
        "grade": 2,
        "effect": "Grants a +25% digestion multiplier.",
        "curse": "Deletes 1 in 20 messages you send.",
        "modifiers": {
            "digestion_multiplier": 1.25,
            "message_delete_ratio": 0.05,
        },
    },
    {
        "key": "2-137",
        "name": "Amulet of the Pale Emperor",
        "grade": 2,
        "effect": "Halves all corruption gained from failed rituals.",
        "curse": "Drains 2 sanity per day.",
        "modifiers": {
            "sanity_drain_per_day": 2.0,
        },
    },
    {
        "key": "3-0782",
        "name": "Penny of Fortune",
        "grade": 3,
        "effect": "Grants a small luck bonus to anomaly rolls (+10% digestion).",
        "curse": "Occasionally whispers false divinations.",
        "modifiers": {
            "digestion_multiplier": 1.1,
        },
    },
    {
        "key": "3-060",
        "name": "Lantern of the Evernight",
        "grade": 3,
        "effect": "Reveals an extra ingredient on anomaly participation.",
        "curse": "1 in 25 messages are devoured by darkness.",
        "modifiers": {
            "message_delete_ratio": 0.04,
        },
    },
    {
        "key": "0-88",
        "name": "Staff of the Stars",
        "grade": 0,
        "effect": "Triples digestion and grants immunity to gibberish-filtering.",
        "curse": "Drains 10 corruption per day; cannot be unequipped without divine aid.",
        "modifiers": {
            "digestion_multiplier": 3.0,
            "corruption_per_day": 10.0,
        },
    },
    {
        "key": "0-17",
        "name": "Heart of the Abyss",
        "grade": 0,
        "effect": "Doubles all gold and triples anomaly rewards.",
        "curse": "Drains 8 sanity per day; loss of control is inevitable without sealing.",
        "modifiers": {
            "gold_multiplier": 2.0,
            "sanity_drain_per_day": 8.0,
        },
    },
]

SEALED_ARTIFACTS: Dict[str, Dict] = {a["key"]: a for a in _RAW}


def get_artifact(key: str) -> Dict | None:
    return SEALED_ARTIFACTS.get(key)

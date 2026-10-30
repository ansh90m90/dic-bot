"""The 22 Beyonder Pathways of Lord of the Mysteries.

This is the single source of truth for pathway lore used across the bot. Each
pathway holds its Sequence 9 -> Sequence 0 ladder, its group, and the
above-sequence being it ultimately belongs to.
"""
from __future__ import annotations

import math
from typing import Dict, List

# Digestion multipliers per Sequence.
# Calibrated so Sequence 9 takes 72 hours (3 continuous days = 4,320 mins) of VC activity.
# Sequence 2 takes 480 hours (8 months @ 2 hours/day = 28,800 mins) of VC activity.
BASE_VC_MINUTES_SEQ9 = 4320.0  # 72 hours = 3 continuous days
BASE_VC_MINUTES_SEQ2 = 28800.0  # 480 hours = 240 days (8 months) * 2 hours

DIGESTION_MULTIPLIERS: Dict[int, float] = {
    9: 1.0,      # 72h continuous VC = 100%
    8: 0.720,    # 100h total VC
    7: 0.480,    # 150h total VC
    6: 0.327,    # 220h total VC
    5: 0.240,    # 300h total VC
    4: 0.189,    # 380h total VC
    3: 0.164,    # 440h total VC
    2: 0.150,    # 480h total VC = 8 months @ 2h/day
    1: 0.120,    # 600h total VC = 10+ months
    0: 0.0,
}

# group key -> ordered list of pathway keys
GROUPS: Dict[str, List[str]] = {
    "Lord of the Mysteries": ["fool", "error", "door"],
    "God Almighty": ["visionary", "hanged_man", "white_tower", "sun", "tyrant"],
    "Eternal Darkness": ["darkness", "death", "twilight_giant"],
    "Calamity of Destruction": ["red_priest", "demoness"],
    "Demon of Knowledge": ["hermit", "paragon"],
    "Father of Devils": ["chained", "abyss"],
    "Goddess of Origin": ["moon", "mother"],
    "Anarchy": ["black_emperor", "justiciar"],
    "Key of Light": ["wheel_of_fortune"],
}

PATHWAYS: Dict[str, Dict] = {
    "fool": {
        "name": "Fool",
        "group": "Lord of the Mysteries",
        "above": "Lord of the Mysteries",
        "sequences": {
            9: "Seer", 8: "Clown", 7: "Magician", 6: "Faceless", 5: "Marionettist",
            4: "Bizarro Sorcerer", 3: "Scholar of Yore", 2: "Miracle Invoker",
            1: "Attendant of Mysteries", 0: "The Fool",
        },
    },
    "error": {
        "name": "Error",
        "group": "Lord of the Mysteries",
        "above": "Lord of the Mysteries",
        "sequences": {
            9: "Marauder", 8: "Swindler", 7: "Cryptologist", 6: "Prometheus",
            5: "Dream Stealer", 4: "Parasite", 3: "Mentor of Deceit",
            2: "Trojan Horse of Destiny", 1: "Worm of Time", 0: "Error",
        },
    },
    "door": {
        "name": "Door",
        "group": "Lord of the Mysteries",
        "above": "Lord of the Mysteries",
        "sequences": {
            9: "Apprentice", 8: "Trickmaster", 7: "Astrologer", 6: "Scribe",
            5: "Traveler", 4: "Secrets Sorcerer", 3: "Wanderer",
            2: "Planeswalker", 1: "Key of Stars", 0: "Door",
        },
    },
    "visionary": {
        "name": "Visionary",
        "group": "God Almighty",
        "above": "God Almighty",
        "sequences": {
            9: "Spectator", 8: "Telepathist", 7: "Psychiatrist", 6: "Hypnotist",
            5: "Dreamwalker", 4: "Manipulator", 3: "Dreamweaver",
            2: "Discerner", 1: "Author", 0: "Visionary",
        },
    },
    "hanged_man": {
        "name": "Hanged Man",
        "group": "God Almighty",
        "above": "God Almighty",
        "sequences": {
            9: "Secrets Suppliant", 8: "Listener", 7: "Shadow Ascetic",
            6: "Rose Bishop", 5: "Shepherd", 4: "Black Knight",
            3: "Trinity Templar", 2: "Profane Presbyter", 1: "Dark Angel",
            0: "Hanged Man",
        },
    },
    "white_tower": {
        "name": "White Tower",
        "group": "God Almighty",
        "above": "God Almighty",
        "sequences": {
            9: "Reader", 8: "Student of Ratiocination", 7: "Detective",
            6: "Polymath", 5: "Mysticism Magister", 4: "Prophet",
            3: "Cognizer", 2: "Sage", 1: "Omniscient Eye", 0: "White Tower",
        },
    },
    "sun": {
        "name": "Sun",
        "group": "God Almighty",
        "above": "God Almighty",
        "sequences": {
            9: "Bard", 8: "Light Suppliant", 7: "Solar High Priest", 6: "Notary",
            5: "Priest of Light", 4: "Unshadowed", 3: "Justice Mentor",
            2: "Light Seeker", 1: "Light of the World", 0: "Sun",
        },
    },
    "tyrant": {
        "name": "Tyrant",
        "group": "God Almighty",
        "above": "God Almighty",
        "sequences": {
            9: "Sailor", 8: "Folk of Rage", 7: "Seafarer", 6: "Windblessed",
            5: "Ocean Songster", 4: "Cataclysmic Interrer", 3: "Sea King",
            2: "Calamity", 1: "Thunder God", 0: "Tyrant",
        },
    },
    "darkness": {
        "name": "Darkness",
        "group": "Eternal Darkness",
        "above": "Eternal Darkness",
        "sequences": {
            9: "Sleepless", 8: "Midnight Poet", 7: "Nightmare",
            6: "Soul Assurer", 5: "Spirit Warlock", 4: "Nightwatcher",
            3: "Horror Bishop", 2: "Servant of Concealment",
            1: "Knight of Misfortune", 0: "Darkness",
        },
    },
    "death": {
        "name": "Death",
        "group": "Eternal Darkness",
        "above": "Eternal Darkness",
        "sequences": {
            9: "Corpse Collector", 8: "Gravedigger", 7: "Spirit Medium",
            6: "Spirit Guide", 5: "Gatekeeper", 4: "Undying",
            3: "Ferryman", 2: "Death Consul", 1: "Pale Emperor", 0: "Death",
        },
    },
    "twilight_giant": {
        "name": "Twilight Giant",
        "group": "Eternal Darkness",
        "above": "Eternal Darkness",
        "sequences": {
            9: "Warrior", 8: "Pugilist", 7: "Weapon Master", 6: "Dawn Paladin",
            5: "Guardian", 4: "Demon Hunter", 3: "Silver Knight",
            2: "Glory", 1: "Hand of God", 0: "Twilight Giant",
        },
    },
    "red_priest": {
        "name": "Red Priest",
        "group": "Calamity of Destruction",
        "above": "Calamity of Destruction",
        "sequences": {
            9: "Hunter", 8: "Provoker", 7: "Pyromaniac", 6: "Conspirer",
            5: "Reaper", 4: "Iron-blooded Knight", 3: "War Bishop",
            2: "Weather Warlock", 1: "Conqueror", 0: "Red Priest",
        },
    },
    "demoness": {
        "name": "Demoness",
        "group": "Calamity of Destruction",
        "above": "Calamity of Destruction",
        "sequences": {
            9: "Assassin", 8: "Instigator", 7: "Witch", 6: "Pleasure",
            5: "Affliction", 4: "Despair", 3: "Unaging", 2: "Catastrophe",
            1: "Apocalypse", 0: "Demoness",
        },
    },
    "hermit": {
        "name": "Hermit",
        "group": "Demon of Knowledge",
        "above": "Demon of Knowledge",
        "sequences": {
            9: "Mystery Pryer", 8: "Melee Scholar", 7: "Warlock",
            6: "Scrolls Professor", 5: "Constellations Master",
            4: "Mysticologist", 3: "Clairvoyant", 2: "Sage",
            1: "Knowledge Emperor", 0: "Hermit",
        },
    },
    "paragon": {
        "name": "Paragon",
        "group": "Demon of Knowledge",
        "above": "Demon of Knowledge",
        "sequences": {
            9: "Savant", 8: "Archaeologist", 7: "Appraiser", 6: "Artisan",
            5: "Astronomer", 4: "Alchemist", 3: "Arcane Scholar",
            2: "Knowledge Magister", 1: "Luminary", 0: "Paragon",
        },
    },
    "chained": {
        "name": "Chained",
        "group": "Father of Devils",
        "above": "Father of Devils",
        "sequences": {
            9: "Prisoner", 8: "Lunatic", 7: "Werewolf", 6: "Zombie",
            5: "Wraith", 4: "Puppet", 3: "Disciple of Silence",
            2: "Ancient Bane", 1: "Abomination", 0: "Chained",
        },
    },
    "abyss": {
        "name": "Abyss",
        "group": "Father of Devils",
        "above": "Father of Devils",
        "sequences": {
            9: "Criminal", 8: "Unwinged Angel", 7: "Serial Killer",
            6: "Devil", 5: "Desire Apostle", 4: "Demon", 3: "Blatherer",
            2: "Bloody Archduke", 1: "Filthy Monarch", 0: "Abyss",
        },
    },
    "moon": {
        "name": "Moon",
        "group": "Goddess of Origin",
        "above": "Goddess of Origin",
        "sequences": {
            9: "Apothecary", 8: "Beast Tamer", 7: "Vampire",
            6: "Potions Professor", 5: "Scarlet Scholar", 4: "Shaman King",
            3: "High Summoner", 2: "Life-Giver", 1: "Beauty Goddess", 0: "Moon",
        },
    },
    "mother": {
        "name": "Mother",
        "group": "Goddess of Origin",
        "above": "Goddess of Origin",
        "sequences": {
            9: "Planter", 8: "Doctor", 7: "Harvest Priest", 6: "Biologist",
            5: "Druid", 4: "Ancient Alchemist", 3: "Pallbearer",
            2: "Desolate Matriarch", 1: "Nature Walker", 0: "Mother",
        },
    },
    "black_emperor": {
        "name": "Black Emperor",
        "group": "Anarchy",
        "above": "Anarchy",
        "sequences": {
            9: "Lawyer", 8: "Barbarian", 7: "Briber", 6: "Baron of Corruption",
            5: "Mentor of Disorder", 4: "Count of the Fallen",
            3: "Frenzied Mage", 2: "Duke of Entropy",
            1: "Prince of Eradication", 0: "Black Emperor",
        },
    },
    "justiciar": {
        "name": "Justiciar",
        "group": "Anarchy",
        "above": "Anarchy",
        "sequences": {
            9: "Arbiter", 8: "Sheriff", 7: "Investigator", 6: "Judge",
            5: "Disciplinary Paladin", 4: "Imperative Mage",
            3: "Chaos Hunter", 2: "Balancer", 1: "Hand of Order", 0: "Justiciar",
        },
    },
    "wheel_of_fortune": {
        "name": "Wheel of Fortune",
        "group": "Key of Light",
        "above": "Key of Light",
        "sequences": {
            9: "Monster", 8: "Robot", 7: "Lucky One", 6: "Calamity Priest",
            5: "Winner", 4: "Misfortune Mage", 3: "Chaoswalker",
            2: "Soothsayer", 1: "Snake of Mercury", 0: "Wheel of Fortune",
        },
    },
}


def pathway_keys() -> List[str]:
    """Return all pathway keys in canonical order."""
    keys: List[str] = []
    for group in GROUPS.values():
        for key in group:
            keys.append(key)
    return keys


def get_pathway(key: str) -> Dict | None:
    """Return a pathway dict by key, or ``None``."""
    return PATHWAYS.get(key.lower())


def resolve_pathway(name: str) -> str | None:
    """Resolve a fuzzy user-supplied name to a pathway key (case/space-insensitive)."""
    target = name.strip().lower().replace(" ", "_").replace("-", "_")
    if target.startswith("the_"):
        target = target[4:]
    if target in PATHWAYS:
        return target
    for key, data in PATHWAYS.items():
        if data["name"].lower().replace(" ", "_") == target:
            return key
        if data["sequences"][0].lower().replace(" ", "_") == target:
            return key
    for key, data in PATHWAYS.items():
        if target in key or target in data["name"].lower():
            return key
    return None


def sequence_name(key: str, sequence: int) -> str:
    """Return the sequence title for a pathway and sequence number."""
    data = get_pathway(key)
    if data is None:
        return f"Sequence {sequence}"
    return data["sequences"].get(sequence, f"Sequence {sequence}")


def rank_title(sequence: int) -> str:
    """A formal rank title for a sequence number."""
    if sequence == 0:
        return "True God"
    if sequence == 1:
        return "King of Angels"
    if sequence == 2:
        return "Angel"
    if sequence in (3, 4):
        return "Saint"
    if 5 <= sequence <= 7:
        return "Beyonder"
    if sequence == 8:
        return "Initiate"
    return "Mortal"


def address(sequence: int) -> str:
    """How the Attendant addresses a user of a given sequence."""
    if sequence == 0:
        return "Deity"
    if sequence == 1:
        return "King of Angels"
    if sequence == 2:
        return "Angel"
    if sequence in (3, 4):
        return "Saint"
    if 5 <= sequence <= 7:
        return "Beyonder"
    if sequence == 8:
        return "Initiate"
    return "Mortal"


def estimated_ascension_time(current_sequence: int, current_digestion: float) -> str:
    """Calculate an estimated remaining time to advance.

    Pads the estimate by ~30% over ideal continuous time to cover irregular logins,
    daily breaks, and real-world variance.
    """
    if current_sequence <= 0:
        return "Apex Reached"

    remaining_percent = max(0.0, 100.0 - current_digestion)
    if remaining_percent <= 0:
        return "Ready for Ascension"

    mult = DIGESTION_MULTIPLIERS.get(current_sequence, 1.0)
    if mult <= 0:
        return "Ready for Ascension"

    # Base continuous minutes at 100% digestion
    total_minutes_needed = BASE_VC_MINUTES_SEQ9 / mult
    rem_minutes = total_minutes_needed * (remaining_percent / 100.0)

    # Apply 1.30x buffer for real-world irregular activity
    buffered_minutes = rem_minutes * 1.30
    buffered_hours = buffered_minutes / 60.0

    # Human-readable formatting tailored to play patterns
    if current_sequence == 9:
        # At Seq 9, 3 days continuous = 72h. Buffered is ~4-5 days.
        days = buffered_hours / 24.0
        return f"~{math.ceil(days)}–{math.ceil(days) + 1} Days (Active VC)"
    elif current_sequence in (8, 7):
        days = buffered_hours / 12.0  # assuming ~12 hours active presence a day
        return f"~{math.ceil(days)}–{math.ceil(days) + 2} Days"
    elif current_sequence in (6, 5):
        weeks = (buffered_hours / 4.0) / 7.0  # assuming ~4h active a day
        return f"~{max(1, round(weeks))}–{max(2, round(weeks) + 1)} Weeks"
    elif current_sequence in (4, 3):
        months = (buffered_hours / 3.0) / 30.0  # assuming ~3h active a day
        return f"~{max(1, round(months, 1))}–{round(months + 1, 1)} Months"
    elif current_sequence == 2:
        # User specified: Seq 2 to 1 takes ~8 months @ 2 hours/day. Buffered = ~8–9 months.
        months = (buffered_hours / 2.0) / 30.0
        return f"~{max(1, round(months, 1))}–{round(months + 1, 1)} Months"
    else:  # Sequence 1
        months = (buffered_hours / 2.0) / 30.0
        return f"~{max(1, round(months, 1))}–{round(months + 1, 1)} Months"


def advancement_requirements(target_sequence: int) -> Dict:
    """Return requirements to advance *into* ``target_sequence`` (8..0)."""
    req: Dict = {
        "gold": 0,
        "tarot": 0,
        "characteristics": 1,
        "char_sequence": target_sequence,
        "ingredients": {},   # rarity -> count
        "min_active_days": 0,
        "min_sanity": 0.0,
        "max_corruption": 100.0,
        "hazard_percent": 0.0,
        "trial": None,       # trial key or None
        "slot_capped": False,
        "max_slots": None,
        "apotheosis": False,
    }

    if target_sequence == 0:
        req.update({
            "gold": 0,
            "tarot": 25,
            "characteristics": 3,
            "char_sequence": 1,
            "min_sanity": 90.0,
            "max_corruption": 10.0,
            "apotheosis": True,
        })
        return req

    if target_sequence == 8:
        req.update({
            "gold": 150,
            "tarot": 0,
            "ingredients": {"common": 2, "uncommon": 1},
            "min_active_days": 3,
            "min_sanity": 60.0,
            "max_corruption": 50.0,
            "hazard_percent": 5.0,
        })
    elif target_sequence == 7:
        req.update({
            "gold": 400,
            "tarot": 1,
            "ingredients": {"common": 3, "uncommon": 2},
            "min_active_days": 7,
            "min_sanity": 65.0,
            "max_corruption": 45.0,
            "hazard_percent": 10.0,
        })
    elif target_sequence == 6:
        req.update({
            "gold": 1000,
            "tarot": 2,
            "ingredients": {"common": 4, "uncommon": 3, "rare": 1},
            "min_active_days": 15,
            "min_sanity": 70.0,
            "max_corruption": 40.0,
            "hazard_percent": 15.0,
        })
    elif target_sequence == 5:
        req.update({
            "gold": 2500,
            "tarot": 4,
            "ingredients": {"common": 5, "uncommon": 4, "rare": 2},
            "min_active_days": 30,
            "min_sanity": 75.0,
            "max_corruption": 35.0,
            "hazard_percent": 20.0,
            "trial": "acting",
        })
    elif target_sequence == 4:
        req.update({
            "gold": 7500,
            "tarot": 8,
            "ingredients": {"common": 5, "uncommon": 5, "rare": 3, "legendary": 1},
            "min_active_days": 60,
            "min_sanity": 80.0,
            "max_corruption": 25.0,
            "hazard_percent": 25.0,
            "trial": "demigod",
        })
    elif target_sequence == 3:
        req.update({
            "gold": 20000,
            "tarot": 15,
            "ingredients": {"uncommon": 6, "rare": 4, "legendary": 2},
            "min_active_days": 100,
            "min_sanity": 85.0,
            "max_corruption": 20.0,
            "hazard_percent": 30.0,
            "trial": "demigod",
        })
    elif target_sequence == 2:
        req.update({
            "gold": 55000,
            "tarot": 30,
            "characteristics": 2,
            "char_sequence": 2,
            "ingredients": {"rare": 6, "legendary": 4},
            "min_active_days": 160,
            "min_sanity": 88.0,
            "max_corruption": 15.0,
            "hazard_percent": 35.0,
            "trial": "angel",
            "slot_capped": True,
            "max_slots": 6,
        })
    elif target_sequence == 1:
        # Advancing from Seq 2 into Seq 1: 8 months of daily VC (at least 2h/day)
        req.update({
            "gold": 150000,
            "tarot": 60,
            "characteristics": 3,
            "char_sequence": 1,
            "ingredients": {"rare": 8, "legendary": 6},
            "min_active_days": 240,  # 8 months of daily activity
            "min_sanity": 92.0,
            "max_corruption": 10.0,
            "hazard_percent": 40.0,
            "trial": "acting",
            "slot_capped": True,
            "max_slots": 3,
        })

    return req

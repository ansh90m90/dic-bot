"""The 22 Beyonder Pathways of Lord of the Mysteries.

This is the single source of truth for pathway lore used across the bot. Each
pathway holds its Sequence 9 -> Sequence 0 ladder, its group, and the
above-sequence being it ultimately belongs to. Tweak names here and every
command follows automatically.

Sequence ladders use the widely circulated English translations. The `name` of
each pathway is the sequence-0 title; the `sequences` map is keyed by sequence
number (9 down to 0).
"""
from __future__ import annotations

from typing import Dict, List

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
    # Try matching the display name and the sequence-0 title of each pathway.
    for key, data in PATHWAYS.items():
        if data["name"].lower().replace(" ", "_") == target:
            return key
        if data["sequences"][0].lower().replace(" ", "_") == target:
            return key
    # Contains-match as a last resort.
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


def advancement_requirements(target_sequence: int) -> Dict:
    """Return requirements to advance *into* ``target_sequence`` (8..0).

    ``target_sequence`` is the sequence the Beyonder is ascending TO.
    A potion *formula* and a *Beyonder characteristic* for that sequence are
    always required on top of these (enforced in the /advance command).
    """
    req: Dict = {
        "gold": 0,
        "ingredients": {},   # rarity -> count
        "min_active_days": 0,
        "trial": None,       # trial key or None
        "slot_capped": False,
        "apotheosis": False,
    }
    if target_sequence == 0:
        req["apotheosis"] = True
        return req

    req["gold"] = {
        8: 50, 7: 100, 6: 250, 5: 500, 4: 1500,
        3: 4000, 2: 10000, 1: 25000,
    }.get(target_sequence, 0)

    if target_sequence >= 8:
        req["ingredients"]["common"] = 1
    elif target_sequence >= 7:
        req["ingredients"]["common"] = 2
    elif target_sequence >= 5:
        req["ingredients"]["common"] = 3
        req["ingredients"]["uncommon"] = 2
    elif target_sequence == 4:
        req["ingredients"]["common"] = 3
        req["ingredients"]["uncommon"] = 3
        req["ingredients"]["rare"] = 1
        req["min_active_days"] = 30
        req["trial"] = "demigod"
    elif target_sequence == 3:
        req["ingredients"]["uncommon"] = 4
        req["ingredients"]["rare"] = 2
        req["ingredients"]["legendary"] = 1
        req["trial"] = "demigod"
    elif target_sequence == 2:
        req["ingredients"]["rare"] = 3
        req["ingredients"]["legendary"] = 2
        req["min_active_days"] = 90
        req["trial"] = "angel"
    elif target_sequence == 1:
        req["ingredients"]["legendary"] = 3
        req["min_active_days"] = 180
        req["trial"] = "acting"
        req["slot_capped"] = True
    return req

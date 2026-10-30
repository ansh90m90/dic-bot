"""Potion ingredients, formula/characteristic keys, and monster drop tables."""
from __future__ import annotations

import random

# Rarity tiers, lowest to highest.
RARITIES: tuple[str, ...] = ("common", "uncommon", "rare", "legendary")

INGREDIENT_NAMES: dict[str, list[str]] = {
    "common": [
        "Moon Flower", "Manhal Fish Eye", "Dried Mandrake", "Silver Powder",
        "Night Herb", "Ordinary Quill", "Stale Bread of the Spirit World",
        "Rainwater from a Foggy Night",
    ],
    "uncommon": [
        "Sheep Horn Black Fish Blood", "Seven-colored Lizard Pituitary",
        "Zombie Flesh", "Merman Scales", "Spirit Dust", "Mandrake Root",
        "Nighthawk Feather", "Bottled Moonlight",
    ],
    "rare": [
        "Mind Dragon Brain", "Elder Tree Sap", "Wraith Marrow",
        "Blood of the Moon", "Fate Knot", "Siren Tear", "Beyonder Corrupted Silver",
        "Fragment of a Broken Dream",
    ],
    "legendary": [
        "Beyonder Characteristic Fragment", "Angel's Feather", "Abyss Stone",
        "Seed of the Spirit World", "Uniqueness Shard", "Essence of the Gray Fog",
    ],
}

# Weighted drop table: rarity -> relative weight.
DROP_WEIGHTS: dict[str, int] = {
    "common": 60,
    "uncommon": 28,
    "rare": 10,
    "legendary": 2,
}


def formula_key(pathway_key: str, sequence: int) -> str:
    """Inventory key for a potion formula of a given pathway/sequence."""
    return f"formula:{pathway_key}:{sequence}"


def characteristic_key(pathway_key: str, sequence: int) -> str:
    """Inventory key for a Beyonder characteristic of a given pathway/sequence."""
    return f"characteristic:{pathway_key}:{sequence}"


def is_formula(key: str) -> bool:
    return key.startswith("formula:")


def is_characteristic(key: str) -> bool:
    return key.startswith("characteristic:")


def is_ingredient(key: str) -> bool:
    return not (is_formula(key) or is_characteristic(key))


def roll_rarity() -> str:
    """Roll a weighted random ingredient rarity."""
    total = sum(DROP_WEIGHTS.values())
    pick = random.randint(1, total)
    upto = 0
    for rarity, weight in DROP_WEIGHTS.items():
        upto += weight
        if pick <= upto:
            return rarity
    return "common"


def roll_ingredient() -> str:
    """Roll a random ingredient name (single instance)."""
    rarity = roll_rarity()
    return random.choice(INGREDIENT_NAMES[rarity])


def rarity_of(key: str) -> str:
    """Infer a rarity label for display. Ingredients are looked up by name."""
    if is_formula(key):
        return "formula"
    if is_characteristic(key):
        return "characteristic"
    for rarity, names in INGREDIENT_NAMES.items():
        if key in names:
            return rarity
    return "common"

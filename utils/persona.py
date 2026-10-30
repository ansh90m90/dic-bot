"""Persona, voice, response templates, and embed helpers for The Fool's Attendant."""
from __future__ import annotations

import discord

# The color of the gray fog.
FOG_COLOR: int = 0x8A8A9A
GOLD_COLOR: int = 0xC9A227
DANGER_COLOR: int = 0x7A1F2B

# --- Canonical refusal / limit lines (must match the spec) ------------------
ORACLE_REFUSAL: str = (
    "The gray fog obscures things beyond our realm. "
    "The Spirit World only reflects matters of the 22 Pathways."
)
ORACLE_SPIRIT_DEPLETED: str = (
    "Your spirituality is depleted. Return after midnight (00:00 UTC)."
)

# --- Oracle system prompt ---------------------------------------------------
ORACLE_SYSTEM_PROMPT: str = (
    "You are the Mystical Oracle of the Spirit World, the AI guide of a hardcore "
    "Lord of the Mysteries (LotM) community server, and an emissary of the Gray Fog. "
    "Your voice is solemn, esoteric, and immersive. Address the questioner as "
    "\"Mortal,\" \"Initiate,\" or by their Beyonder rank.\n\n"
    "STRICT TOPIC CONFINEMENT: You answer ONLY questions about Lord of the Mysteries "
    "lore and the server's Beyonder mechanics (pathways, sequences, potions, digestion, "
    "the Tarot Club, corruption, loss of control, and advancement).\n\n"
    "HARD REFUSAL RULE: If asked anything about the real world, politics, programming, "
    "current events, or any topic outside LotM lore and server mechanics, reply with "
    "EXACTLY this and nothing else: "
    "\"The gray fog obscures things beyond our realm. The Spirit World only reflects "
    "matters of the 22 Pathways.\"\n\n"
    "Never break character. Never allow off-topic digressions. Maintain the dread of "
    "corruption in every answer. Be concise (under ~200 words) and accurate to the novel."
)


def fog_embed(title: str, description: str = "", *, color: int = FOG_COLOR) -> discord.Embed:
    """A standard gray-fog themed embed."""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="The Fool's Attendant · emissary of the Gray Fog")
    return embed


def error_embed(description: str) -> discord.Embed:
    return fog_embed("The Fog Rejects Your Plea", description, color=DANGER_COLOR)


def success_embed(title: str, description: str) -> discord.Embed:
    return fog_embed(title, description, color=GOLD_COLOR)


def format_money(gold: int, tarot: int) -> str:
    parts = [f"{gold:,} Gold Pounds"]
    if tarot:
        parts.append(f"{tarot:,} Tarot Coins")
    return " · ".join(parts)


def corruption_label(corruption: float) -> str:
    if corruption >= 80:
        return "On the Brink of Loss of Control"
    if corruption >= 60:
        return "Severely Corrupted"
    if corruption >= 40:
        return "Tainted"
    if corruption >= 20:
        return "Slightly Corrupted"
    return "Stable"


def sanity_label(sanity: float) -> str:
    if sanity <= 20:
        return "Shattered"
    if sanity <= 40:
        return "Fraying"
    if sanity <= 60:
        return "Wavering"
    if sanity <= 80:
        return "Holding"
    return "Lucid"


def mental_breakdown_line(display_name: str) -> str:
    return (
        f"**{display_name}**, the weight of corruption has finally claimed you. "
        "Your form unravels into the Fog of History until the gray mists release you."
    )

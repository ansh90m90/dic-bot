"""Assign a per-(pathway, sequence) Discord role so it shows on the profile."""
from __future__ import annotations

import discord

from data import pathways
from settings import settings

# A color per above-sequence group, for a little flavor.
_GROUP_COLORS = {
    "Lord of the Mysteries": 0x5C5C99,
    "God Almighty": 0xC9A227,
    "Eternal Darkness": 0x3B3B4F,
    "Calamity of Destruction": 0xA0303A,
    "Demon of Knowledge": 0x3E7A5E,
    "Father of Devils": 0x6B2E3F,
    "Goddess of Origin": 0xB07A9E,
    "Anarchy": 0x8A6E3A,
    "Key of Light": 0x9B86C9,
}


def role_name(pathway_key: str, sequence: int) -> str:
    data = pathways.get_pathway(pathway_key)
    if not data:
        return f"Sequence {sequence}"
    return f"{data['name']} · {pathways.sequence_name(pathway_key, sequence)}"


async def sync_beyonder_role(
    db, member: discord.Member | None, pathway_key: str, sequence: int
) -> discord.Role | None:
    """Give a member the role for their pathway+sequence, removing the old one.

    Roles are created lazily (only when someone reaches that combination) and
    reused by name. Returns the assigned role, or ``None`` if roles are disabled
    or the bot lacks the "Manage Roles" permission.
    """
    if not settings.get("features_roles", True):
        return None
    if not isinstance(member, discord.Member) or member.guild is None:
        return None
    guild = member.guild

    # Remove the previously assigned Beyonder role (tracked by id).
    user = db.get_user(member.id) or {}
    old_id = user.get("beyond_role_id")
    if old_id and str(old_id).isdigit():
        old_role = guild.get_role(int(old_id))
        if old_role is not None:
            try:
                await member.remove_roles(old_role, reason="Beyonder progression")
            except (discord.Forbidden, discord.HTTPException):
                pass

    name = role_name(pathway_key, sequence)
    role = discord.utils.get(guild.roles, name=name)
    if role is None:
        data = pathways.get_pathway(pathway_key) or {}
        color = discord.Color(_GROUP_COLORS.get(data.get("group"), 0x8A8A9A))
        try:
            role = await guild.create_role(name=name, color=color, reason="Beyonder role")
        except (discord.Forbidden, discord.HTTPException):
            return None

    try:
        await member.add_roles(role, reason="Beyonder progression")
    except (discord.Forbidden, discord.HTTPException):
        return None

    db.set_beyond_role(member.id, str(role.id))
    return role

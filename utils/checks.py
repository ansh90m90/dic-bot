"""Privilege-tier checks for The Fool's Attendant.

Tier      Entity            Check
-----     ---------------   ------------------------------------------------
Owner     Above the Seq.    Guild owner OR a configured OWNER_ID.
Admin     Archangel Council `administrator` permission OR the ADMIN_ROLE.
Mod       Delegated Roles   `manage_messages` permission OR the MOD_ROLE.
"""
from __future__ import annotations

import discord
from discord import app_commands

import config
from settings import settings


def is_owner(interaction: discord.Interaction) -> bool:
    if interaction.user.id in config.OWNER_IDS:
        return True
    guild = interaction.guild
    return bool(guild and guild.owner_id == interaction.user.id)


def is_admin(interaction: discord.Interaction) -> bool:
    if is_owner(interaction):
        return True
    member = interaction.user
    if isinstance(member, discord.Member):
        if member.guild_permissions.administrator:
            return True
        if any(r.name.lower() == settings.get("admin_role", config.ADMIN_ROLE).lower() for r in member.roles):
            return True
    return False


def is_moderator(interaction: discord.Interaction) -> bool:
    if is_admin(interaction):
        return True
    member = interaction.user
    if isinstance(member, discord.Member):
        if member.guild_permissions.manage_messages:
            return True
        if any(r.name.lower() == settings.get("mod_role", config.MOD_ROLE).lower() for r in member.roles):
            return True
    return False


def is_beyonder(interaction: discord.Interaction) -> bool:
    """Check if the interacting member has sworn fealty and drunk a Sequence 9 potion."""
    bot = interaction.client
    db = getattr(bot, "db", None)
    if db is None:
        return True
    user = db.get_user(interaction.user.id)
    return bool(user and user.get("pathway") is not None and user.get("sequence") is not None)


def _owner_predicate(interaction: discord.Interaction) -> bool:
    if is_owner(interaction):
        return True
    raise app_commands.CheckFailure("Only the one Above the Sequences may command this.")


def _admin_predicate(interaction: discord.Interaction) -> bool:
    if is_admin(interaction):
        return True
    raise app_commands.CheckFailure("Only the Archangel Council holds this authority.")


def _mod_predicate(interaction: discord.Interaction) -> bool:
    if is_moderator(interaction):
        return True
    raise app_commands.CheckFailure("Only a delegated moderator may perform this act.")


def _beyonder_predicate(interaction: discord.Interaction) -> bool:
    if is_beyonder(interaction):
        return True
    raise app_commands.CheckFailure(
        "You are an ordinary mortal. In this realm, only members who seek supernatural power "
        "and authority brew and drink their potion (`/pathway choose <pathway>`) to awaken as a Beyonder. "
        "Mortals cannot wield supernatural abilities or invoke Beyonder commands."
    )


owner_only = app_commands.check(_owner_predicate)
admin_only = app_commands.check(_admin_predicate)
mod_only = app_commands.check(_mod_predicate)
beyonder_only = app_commands.check(_beyonder_predicate)


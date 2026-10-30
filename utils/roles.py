"""Assign and synchronize per-(pathway, sequence) Discord roles with hoisting and diagnostics."""
from __future__ import annotations

import discord
from typing import Optional, Tuple

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


async def resolve_member(
    guild: discord.Guild, user_or_member: discord.Member | discord.User | int
) -> Optional[discord.Member]:
    """Resolve a user or ID to a guild Member with cache + API fallback."""
    if isinstance(user_or_member, discord.Member):
        return user_or_member
    user_id = user_or_member.id if hasattr(user_or_member, "id") else int(user_or_member)
    member = guild.get_member(user_id)
    if member is not None:
        return member
    try:
        return await guild.fetch_member(user_id)
    except (discord.NotFound, discord.HTTPException, discord.Forbidden):
        return None


def role_name(pathway_key: str, sequence: int) -> str:
    """Format: '{Pathway Name} · Seq {sequence} {Sequence Title}'"""
    data = pathways.get_pathway(pathway_key)
    if not data:
        return f"Sequence {sequence}"
    title = pathways.sequence_name(pathway_key, sequence)
    return f"{data['name']} · Seq {sequence} {title}"


def legacy_role_name(pathway_key: str, sequence: int) -> str:
    """Legacy Format: '{Pathway Name} · {Sequence Title}'"""
    data = pathways.get_pathway(pathway_key)
    if not data:
        return f"Sequence {sequence}"
    title = pathways.sequence_name(pathway_key, sequence)
    return f"{data['name']} · {title}"


async def sync_beyonder_role(
    db, member_or_user: discord.Member | discord.User | int, pathway_key: str, sequence: int,
    guild: Optional[discord.Guild] = None,
) -> Tuple[Optional[discord.Role], Optional[str]]:
    """Synchronize a member's Pathway + Sequence role.

    Returns:
        (role, None) on success.
        (None, error_reason) on failure with actionable diagnostic text.
    """
    if not settings.get("features_roles", True):
        return None, "Role management is currently disabled in /settings (features_roles=false)."

    # Resolve guild and member
    target_guild = guild
    if isinstance(member_or_user, discord.Member) and target_guild is None:
        target_guild = member_or_user.guild

    if target_guild is None:
        return None, "No Discord server (guild) could be determined for role assignment."

    member = await resolve_member(target_guild, member_or_user)
    if member is None:
        return None, f"Member could not be found or fetched in guild {target_guild.name}."

    # Check bot manage_roles permission
    me = target_guild.me
    if not me.guild_permissions.manage_roles:
        return None, (
            f"The Fool's Attendant lacks the **Manage Roles** permission in **{target_guild.name}**. "
            "Please grant this permission in Server Settings > Roles."
        )

    target_name = role_name(pathway_key, sequence)
    legacy_name = legacy_role_name(pathway_key, sequence)
    should_hoist = sequence <= 4

    data = pathways.get_pathway(pathway_key) or {}
    group_name = data.get("group", "")
    target_color = discord.Color(_GROUP_COLORS.get(group_name, 0x8A8A9A))

    # Look for existing target role or rename legacy role in-place
    role = discord.utils.get(target_guild.roles, name=target_name)
    if role is None:
        legacy_role = discord.utils.get(target_guild.roles, name=legacy_name)
        if legacy_role is not None:
            # Check hierarchy before modifying
            if me.top_role <= legacy_role:
                return None, (
                    f"Bot's highest role (**{me.top_role.name}**) is below legacy role "
                    f"**{legacy_role.name}**. Move the bot's role above Beyonder roles."
                )
            try:
                await legacy_role.edit(
                    name=target_name,
                    color=target_color,
                    hoist=should_hoist,
                    reason="In-place rename to new Beyonder role format",
                )
                role = legacy_role
            except (discord.Forbidden, discord.HTTPException) as exc:
                return None, f"Failed to rename legacy role '{legacy_name}': {exc}"

    if role is None:
        try:
            role = await target_guild.create_role(
                name=target_name,
                color=target_color,
                hoist=should_hoist,
                reason="Beyonder role creation",
            )
        except discord.Forbidden:
            return None, "Forbidden: The bot lacks permission to create roles in this server."
        except discord.HTTPException as exc:
            return None, f"HTTP error while creating role '{target_name}': {exc}"

    # Verify hierarchy for the target role
    if me.top_role <= role:
        return None, (
            f"Bot's top role (**{me.top_role.name}**) is lower than or equal to **{role.name}**. "
            "Drag the bot's role higher in Server Settings > Roles."
        )

    # Ensure hoist setting is kept up to date
    if role.hoist != should_hoist:
        try:
            await role.edit(hoist=should_hoist, reason="Update Beyonder hoist tier")
        except (discord.Forbidden, discord.HTTPException):
            pass

    # Remove previous Beyonder roles tracked by ID or by naming pattern
    user = db.get_user(member.id) or {}
    old_id = user.get("beyond_role_id")
    if old_id and str(old_id).isdigit() and int(old_id) != role.id:
        old_role = target_guild.get_role(int(old_id))
        if old_role is not None:
            try:
                await member.remove_roles(old_role, reason="Beyonder promotion/demotion")
                # If old role is now empty and was a sequence role, clean it up
                if len(old_role.members) == 0 and (" · Seq " in old_role.name or " · " in old_role.name):
                    if me.top_role > old_role:
                        await old_role.delete(reason="Deleting unused Sequence role")
            except (discord.Forbidden, discord.HTTPException):
                pass

    # Also clean up any other pathway sequence roles the member might still hold
    for r in list(member.roles):
        if r.id != role.id and (" · Seq " in r.name or " · " in r.name):
            # Check if this matches a pathway role pattern
            for p in pathways.PATHWAYS.values():
                if r.name.startswith(f"{p['name']} · "):
                    if me.top_role > r:
                        try:
                            await member.remove_roles(r, reason="Beyonder sequence transition")
                        except (discord.Forbidden, discord.HTTPException):
                            pass
                    break

    # Assign new role to member
    if role not in member.roles:
        try:
            await member.add_roles(role, reason="Beyonder progression sync")
        except discord.Forbidden:
            return None, (
                f"Missing permissions to assign role **{role.name}** to **{member.display_name}**."
            )
        except discord.HTTPException as exc:
            return None, f"Error adding role '{role.name}': {exc}"

    db.set_beyond_role(member.id, str(role.id))
    return role, None


async def sync_all_guild_roles(bot: discord.Client, guild: discord.Guild) -> dict[str, int]:
    """Sync Beyonder roles for all registered members in a guild. Returns summary metrics."""
    metrics = {"synced": 0, "skipped": 0, "errors": 0}
    if not hasattr(bot, "db"):
        return metrics

    db = bot.db  # type: ignore[attr-defined]
    beyonders = db.all_beyonders()
    for row in beyonders:
        uid = int(row["user_id"])
        pathway = row.get("pathway")
        seq = row.get("sequence")
        if not pathway or seq is None:
            metrics["skipped"] += 1
            continue
        member = await resolve_member(guild, uid)
        if member is None:
            metrics["skipped"] += 1
            continue
        role, error = await sync_beyonder_role(db, member, pathway, int(seq), guild=guild)
        if error is not None:
            metrics["errors"] += 1
        else:
            metrics["synced"] += 1

    return metrics

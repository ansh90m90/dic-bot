"""Assign and synchronize per-(pathway, sequence) and Archangel Discord roles with hoisting and diagnostics."""
from __future__ import annotations

import discord
from typing import Optional, Tuple, Dict, Any, List

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

ARCHANGEL_COUNCIL_ROLE_NAME = "🪽 Archangel Council"
ARCHANGEL_COLOR = 0xF0B229  # Radiant Occult Gold

LEGENDARY_ANGEL_TITLES = [
    "Angel of Time",
    "Angel of Retribution",
    "Angel of Concealment",
    "Angel of Fate",
    "Angel of Wisdom",
    "Angel of War",
    "Angel of Death",
    "Angel of Imagination",
    "Angel of Stars",
    "Angel of White",
    "Angel of Purity",
    "Angel of Secrets",
    "Angel of Judgment",
    "Angel of Redemption",
    "Angel of the Grey Fog",
    "King of Angels",
    "Chief of the Silver City",
    "Sword of Silver",
    "Hand of Order",
    "Eye of Omniscience",
    "Prince of Abolition",
    "Angel of Dreams",
]


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


def pathway_role_name(pathway_key: str) -> str:
    """Format: 'Pathway · {Pathway Name}' (e.g. 'Pathway · The Fool')."""
    data = pathways.get_pathway(pathway_key)
    name = data["name"] if data else pathway_key.title()
    return f"Pathway · {name}"


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


def angel_role_name(title: str) -> str:
    """Format: '🪽 Archangel · {Title}'."""
    clean = title.strip()
    if clean.startswith("🪽 "):
        return clean
    if clean.lower().startswith("archangel"):
        return f"🪽 {clean}"
    return f"🪽 Archangel · {clean}"


async def ensure_pathway_role(
    guild: discord.Guild, pathway_key: str
) -> Tuple[Optional[discord.Role], Optional[str]]:
    """Ensure a Pathway allegiance role exists in the server."""
    me = guild.me
    if not me.guild_permissions.manage_roles:
        return None, f"Lacking Manage Roles permission in {guild.name}."

    p_name = pathway_role_name(pathway_key)
    data = pathways.get_pathway(pathway_key) or {}
    group_name = data.get("group", "")
    target_color = discord.Color(_GROUP_COLORS.get(group_name, 0x8A8A9A))

    role = discord.utils.get(guild.roles, name=p_name)
    if role is None:
        try:
            role = await guild.create_role(
                name=p_name,
                color=target_color,
                hoist=False,
                mentionable=True,
                reason="Automatic Pathway allegiance role creation",
            )
        except (discord.Forbidden, discord.HTTPException) as exc:
            return None, f"Failed to create role '{p_name}': {exc}"

    return role, None


async def setup_all_pathway_roles(guild: discord.Guild) -> dict[str, Any]:
    """Pre-provision all 22 Pathway roles and the Archangel Council role in a server."""
    res = {
        "pathways_created": 0,
        "pathways_existing": 0,
        "council_role": False,
        "errors": [],
    }

    me = guild.me
    if not me.guild_permissions.manage_roles:
        res["errors"].append(
            f"The Fool's Attendant lacks **Manage Roles** in {guild.name}."
        )
        return res

    # 1. Archangel Council Role (hoisted, golden)
    council_role = discord.utils.get(guild.roles, name=ARCHANGEL_COUNCIL_ROLE_NAME)
    if council_role is None:
        try:
            council_role = await guild.create_role(
                name=ARCHANGEL_COUNCIL_ROLE_NAME,
                color=discord.Color(ARCHANGEL_COLOR),
                hoist=True,
                mentionable=True,
                reason="Archangel Council supreme authority role creation",
            )
            res["council_role"] = True
        except Exception as exc:
            res["errors"].append(f"Failed to create council role: {exc}")
    else:
        res["council_role"] = True

    # 2. All 22 Pathway Roles
    for p_key in pathways.PATHWAYS.keys():
        p_name = pathway_role_name(p_key)
        existing = discord.utils.get(guild.roles, name=p_name)
        if existing is not None:
            res["pathways_existing"] += 1
            continue

        role, err = await ensure_pathway_role(guild, p_key)
        if err:
            res["errors"].append(err)
        elif role:
            res["pathways_created"] += 1

    return res


async def sync_angel_title_role(
    db, member: discord.Member, title: Optional[str] = None
) -> Tuple[Optional[discord.Role], Optional[str]]:
    """Synchronize an administrator's unique Angel Title and Archangel Council role."""
    guild = member.guild
    me = guild.me
    if not me.guild_permissions.manage_roles:
        return None, "Bot lacks Manage Roles permission."

    # Look up title from DB if not provided
    if title is None:
        row = db.get_angel_title(member.id)
        if not row:
            return None, "No Angel title is registered for this member."
        title = row["title"]
    else:
        db.set_angel_title(member.id, title)

    # 1. Ensure Archangel Council role is granted
    council_role = discord.utils.get(guild.roles, name=ARCHANGEL_COUNCIL_ROLE_NAME)
    if council_role is None:
        try:
            council_role = await guild.create_role(
                name=ARCHANGEL_COUNCIL_ROLE_NAME,
                color=discord.Color(ARCHANGEL_COLOR),
                hoist=True,
                mentionable=True,
                reason="Archangel Council initialization",
            )
        except Exception:
            pass

    if council_role and council_role not in member.roles:
        if me.top_role > council_role:
            try:
                await member.add_roles(council_role, reason="Archangel Council membership")
            except Exception:
                pass

    # 2. Ensure unique Angel Title role
    target_role_name = angel_role_name(title)
    role = discord.utils.get(guild.roles, name=target_role_name)
    if role is None:
        try:
            role = await guild.create_role(
                name=target_role_name,
                color=discord.Color(ARCHANGEL_COLOR),
                hoist=True,
                mentionable=True,
                reason="Unique Angel title role creation",
            )
        except (discord.Forbidden, discord.HTTPException) as exc:
            return None, f"Failed to create Angel title role: {exc}"

    if me.top_role <= role:
        return None, (
            f"Bot's top role (**{me.top_role.name}**) is lower than or equal to **{role.name}**. "
            "Drag the bot's role higher in Server Settings > Roles."
        )

    # Remove any old unique Angel roles the member had
    for r in list(member.roles):
        if r.name.startswith("🪽 Archangel · ") and r.id != role.id:
            try:
                await member.remove_roles(r, reason="Unique Angel title update")
                if len(r.members) == 0 and me.top_role > r:
                    await r.delete(reason="Clean up unused unique Angel title role")
            except Exception:
                pass

    if role not in member.roles:
        try:
            await member.add_roles(role, reason="Unique Angel title bestowed")
        except Exception as exc:
            return None, f"Failed to assign role '{role.name}': {exc}"

    db.set_angel_title(member.id, title, str(role.id))
    return role, None


async def remove_angel_title_role(db, member: discord.Member) -> Optional[str]:
    """Remove a member's unique Angel Title and clean up the role."""
    guild = member.guild
    me = guild.me
    db.clear_angel_title(member.id)

    if not me.guild_permissions.manage_roles:
        return "Bot lacks Manage Roles permission."

    for r in list(member.roles):
        if r.name.startswith("🪽 Archangel · "):
            try:
                await member.remove_roles(r, reason="Angel title revoked")
                if len(r.members) == 0 and me.top_role > r:
                    await r.delete(reason="Clean up revoked Angel title role")
            except Exception as exc:
                return f"Error removing role: {exc}"

    return None


async def sync_beyonder_role(
    db, member_or_user: discord.Member | discord.User | int, pathway_key: str, sequence: int,
    guild: Optional[discord.Guild] = None,
) -> Tuple[Optional[discord.Role], Optional[str]]:
    """Synchronize a member's Pathway allegiance and Sequence rank roles.

    Returns:
        (sequence_role, None) on success.
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

    data = pathways.get_pathway(pathway_key) or {}
    group_name = data.get("group", "")
    target_color = discord.Color(_GROUP_COLORS.get(group_name, 0x8A8A9A))

    # --- 1. Ensure and Assign Pathway Allegiance Role ('Pathway · {Name}') ---
    p_role_name = pathway_role_name(pathway_key)
    path_role = discord.utils.get(target_guild.roles, name=p_role_name)
    if path_role is None:
        try:
            path_role = await target_guild.create_role(
                name=p_role_name,
                color=target_color,
                hoist=False,
                mentionable=True,
                reason="Pathway allegiance role creation",
            )
        except Exception:
            pass

    if path_role and path_role not in member.roles:
        if me.top_role > path_role:
            try:
                await member.add_roles(path_role, reason="Beyonder Pathway allegiance")
            except Exception:
                pass

    # Remove any other pathway roles the member might hold from a previous choice
    for r in list(member.roles):
        if r.name.startswith("Pathway · ") and (path_role is None or r.id != path_role.id):
            if me.top_role > r:
                try:
                    await member.remove_roles(r, reason="Pathway re-alignment")
                except Exception:
                    pass

    # --- 2. Ensure and Assign Sequence Rank Role ('{Pathway} · Seq {N} {Title}') ---
    target_name = role_name(pathway_key, sequence)
    legacy_name = legacy_role_name(pathway_key, sequence)
    should_hoist = sequence <= 4  # Demigods, Angels, and True Gods are hoisted

    # Look for existing target role or rename legacy role in-place
    role = discord.utils.get(target_guild.roles, name=target_name)
    if role is None:
        legacy_role = discord.utils.get(target_guild.roles, name=legacy_name)
        if legacy_role is not None:
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
                reason="Beyonder Sequence role creation",
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
                if len(old_role.members) == 0 and (" · Seq " in old_role.name or " · " in old_role.name):
                    if me.top_role > old_role:
                        await old_role.delete(reason="Deleting unused Sequence role")
            except (discord.Forbidden, discord.HTTPException):
                pass

    # Clean up any other sequence roles for this member
    for r in list(member.roles):
        if r.id != role.id and (" · Seq " in r.name or " · " in r.name):
            for p in pathways.PATHWAYS.values():
                if r.name.startswith(f"{p['name']} · "):
                    if me.top_role > r:
                        try:
                            await member.remove_roles(r, reason="Beyonder sequence transition")
                        except (discord.Forbidden, discord.HTTPException):
                            pass
                    break

    # Assign new sequence role to member
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

    # --- 3. If member is an Administrator / has an Angel Title, also sync their title role ---
    if member.guild_permissions.administrator or db.get_angel_title(member.id):
        try:
            await sync_angel_title_role(db, member)
        except Exception:
            pass

    return role, None


async def sync_all_guild_roles(bot: discord.Client, guild: discord.Guild) -> dict[str, int]:
    """Sync Beyonder roles and Angel titles for all registered members in a guild."""
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

    # Also sync angel titles for administrators
    for title_row in db.all_angel_titles():
        uid = int(title_row["user_id"])
        member = await resolve_member(guild, uid)
        if member:
            await sync_angel_title_role(db, member, title_row["title"])

    return metrics

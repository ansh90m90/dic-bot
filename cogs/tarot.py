"""The Tarot Club — anonymous gatherings under Major Arcana aliases."""
from __future__ import annotations

import random
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from settings import settings
from utils import persona, checks
from utils.roles import resolve_member
from db.database import Database

TAROT_DEFAULT_CHANNEL_NAME = "tarot-club"


class TarotCog(commands.Cog):
    tarot = app_commands.Group(
        name="tarot", description="The anonymous Tarot Club gathering."
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._webhooks: dict[int, discord.Webhook] = {}

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    def _unused_cards(self) -> list[str]:
        used = {r["card"] for r in self.db._fetchall("SELECT card FROM tarot_aliases")}
        return [c for c in config.TAROT_CARDS if c not in used]

    async def _ensure_tarot_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        """Fetch or automatically create the Tarot Club Discord role."""
        role_name = settings.get("tarot_role", config.TAROT_ROLE)
        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            if not guild.me.guild_permissions.manage_roles:
                return None
            try:
                role = await guild.create_role(
                    name=role_name,
                    color=discord.Color(0x9B86C9),
                    hoist=False,
                    mentionable=False,
                    reason="Auto-created Tarot Club member role",
                )
            except (discord.Forbidden, discord.HTTPException):
                return None
        return role

    # --- join -------------------------------------------------------------
    @tarot.command(name="join")
    @checks.beyonder_only
    async def tarot_join(self, interaction: discord.Interaction) -> None:
        """Join the Tarot Club, receive an anonymous Major Arcana alias, and grant the Tarot role."""
        if not settings.get("features_tarot", True):
            await interaction.response.send_message(
                embed=persona.error_embed("The Tarot Club is sealed by the gray fog."),
                ephemeral=True,
            )
            return

        guild = interaction.guild
        if guild is None:
            return

        if self.db.get_tarot_alias(interaction.user.id) is not None:
            await interaction.response.send_message(
                embed=persona.error_embed("You are already seated at the Tarot Club."),
                ephemeral=True,
            )
            return

        unused = self._unused_cards()
        if not unused:
            await interaction.response.send_message(
                embed=persona.error_embed("Every seat at the Tarot Club is taken."),
                ephemeral=True,
            )
            return

        card = random.choice(unused)
        self.db.set_tarot_alias(interaction.user.id, card, card)

        # Auto-grant Tarot role
        role_error = None
        role = await self._ensure_tarot_role(guild)
        member = await resolve_member(guild, interaction.user.id)
        if role and member:
            try:
                await member.add_roles(role, reason="Joined the Tarot Club")
            except (discord.Forbidden, discord.HTTPException) as exc:
                role_error = f"Could not grant role **{role.name}**: {exc}"
        elif not role:
            role_error = "Could not find or create the Tarot role (check bot permissions)."

        embed = persona.success_embed(
            "A Seat at the Table",
            f"You are seated, **{interaction.user.display_name}**. Henceforth, within "
            f"the Club you are known only as **{card}**. Speak through `/tarot speak` "
            f"and your true name shall remain hidden.",
        )
        if role_error:
            embed.add_field(name="⚠️ Tarot Role Status", value=role_error, inline=False)

        await interaction.response.send_message(embed=embed)

    # --- speak ------------------------------------------------------------
    @tarot.command(name="speak")
    @checks.beyonder_only
    @app_commands.describe(message="What you wish to say, anonymously.")
    async def tarot_speak(self, interaction: discord.Interaction, message: str) -> None:
        """Speak anonymously as your Tarot alias in the Club channel."""
        alias = self.db.get_tarot_alias(interaction.user.id)
        if alias is None:
            await interaction.response.send_message(
                embed=persona.error_embed("You must `/tarot join` before you may speak."),
                ephemeral=True,
            )
            return
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=persona.error_embed("This may only be spoken in a text channel."),
                ephemeral=True,
            )
            return

        sent = await self._speak(channel, alias["alias"], message)
        if not sent:
            await interaction.response.send_message(
                embed=persona.error_embed("The gray fog could not relay your words here."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=persona.fog_embed("Spoken", "Your words vanish into the Club's anonymity."),
            ephemeral=True,
        )

    async def _speak(self, channel: discord.TextChannel, alias: str, message: str) -> bool:
        webhook = self._webhooks.get(channel.id)
        if webhook is None:
            try:
                hooks = await channel.webhooks()
                webhook = next((h for h in hooks if h.name == "The Fool's Attendant"), None)
                if webhook is None:
                    webhook = await channel.create_webhook(name="The Fool's Attendant")
                self._webhooks[channel.id] = webhook
            except (discord.Forbidden, discord.HTTPException):
                webhook = None
        if webhook is not None:
            try:
                await webhook.send(content=message, username=alias)
                return True
            except (discord.Forbidden, discord.HTTPException):
                pass
        try:
            await channel.send(f"**[{alias}]** {message}")
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    # --- leave ------------------------------------------------------------
    @tarot.command(name="leave")
    @checks.beyonder_only
    async def tarot_leave(self, interaction: discord.Interaction) -> None:
        """Vacate your seat at the Tarot Club and revoke the Tarot role."""
        if self.db.get_tarot_alias(interaction.user.id) is None:
            await interaction.response.send_message(
                embed=persona.error_embed("You hold no seat at the Tarot Club."),
                ephemeral=True,
            )
            return
        self.db.clear_tarot_alias(interaction.user.id)

        # Revoke Tarot role
        guild = interaction.guild
        if guild:
            role = await self._ensure_tarot_role(guild)
            member = await resolve_member(guild, interaction.user.id)
            if role and member and role in member.roles:
                try:
                    await member.remove_roles(role, reason="Vacated Tarot Club seat")
                except (discord.Forbidden, discord.HTTPException):
                    pass

        await interaction.response.send_message(
            embed=persona.fog_embed(
                "Seat Vacated", "You fade back into the gray fog, nameless once more."
            )
        )

    # --- open / close (admin) --------------------------------------------
    @tarot.command(name="open")
    @checks.admin_only
    @app_commands.describe(channel_name="Optional custom name for the Tarot Club channel.")
    async def tarot_open(
        self, interaction: discord.Interaction, channel_name: Optional[str] = None
    ) -> None:
        """Open or auto-create the restricted Tarot Club channel with custom name."""
        if not settings.get("features_tarot", True):
            await interaction.response.send_message(
                embed=persona.error_embed("The Tarot Club is disabled in /settings."),
                ephemeral=True,
            )
            return
        guild = interaction.guild
        if guild is None:
            return

        target_name = (channel_name or TAROT_DEFAULT_CHANNEL_NAME).strip().lower().replace(" ", "-")
        tarot_role = await self._ensure_tarot_role(guild)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_messages=True, manage_webhooks=True
            ),
        }
        if tarot_role:
            overwrites[tarot_role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            )

        channel = discord.utils.get(guild.text_channels, name=target_name)
        was_created = False
        if channel is None:
            try:
                channel = await guild.create_text_channel(
                    target_name,
                    overwrites=overwrites,
                    topic="The weekly Tarot Club — anonymous trading and secrets.",
                )
                was_created = True
            except discord.Forbidden:
                await interaction.response.send_message(
                    embed=persona.error_embed(
                        f"Missing permissions to create channel **#{target_name}**. "
                        "Please grant the bot **Manage Channels** permission."
                    ),
                    ephemeral=True,
                )
                return
        else:
            # Channel exists: apply/update overwrites
            try:
                if tarot_role:
                    await channel.set_permissions(
                        tarot_role, read_messages=True, send_messages=True
                    )
                await channel.set_permissions(
                    guild.default_role, read_messages=False
                )
            except discord.Forbidden:
                pass

        action_desc = "has been forged and opened" if was_created else "is now open"
        await interaction.response.send_message(
            embed=persona.success_embed(
                "The Tarot Club Gathers",
                f"The private chamber **{channel.mention}** {action_desc}. Members with the "
                f"**{tarot_role.name if tarot_role else 'Tarot'}** role may enter. "
                f"Use `/tarot join` to receive a seat and an anonymous Major Arcana alias.",
            )
        )

    @tarot.command(name="close")
    @checks.admin_only
    async def tarot_close(self, interaction: discord.Interaction) -> None:
        """Close the Tarot Club, stripping all aliases and revoking the Tarot role."""
        guild = interaction.guild
        tarot_role = await self._ensure_tarot_role(guild) if guild else None

        for row in self.db._fetchall("SELECT user_id FROM tarot_aliases"):
            uid = int(row["user_id"])
            self.db.clear_tarot_alias(uid)
            if guild and tarot_role:
                member = await resolve_member(guild, uid)
                if member and tarot_role in member.roles:
                    try:
                        await member.remove_roles(tarot_role, reason="Tarot Club closed")
                    except (discord.Forbidden, discord.HTTPException):
                        pass

        self._webhooks.clear()
        await interaction.response.send_message(
            embed=persona.fog_embed(
                "The Gathering Disperses",
                "The Tarot Club dissolves back into the gray fog. All aliases are forgotten "
                "and roles have been revoked.",
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TarotCog(bot))

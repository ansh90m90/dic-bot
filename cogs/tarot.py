"""The Tarot Club — anonymous gatherings under Major Arcana aliases."""
from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

import config
from settings import settings
from utils import persona, checks
from db.database import Database

TAROT_CHANNEL_NAME = "tarot-club"


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

    # --- join -------------------------------------------------------------
    @tarot.command(name="join")
    async def tarot_join(self, interaction: discord.Interaction) -> None:
        """Join the Tarot Club and receive an anonymous Major Arcana alias."""
        if not settings.get("features_tarot", True):
            await interaction.response.send_message(
                embed=persona.error_embed("The Tarot Club is sealed by the gray fog."),
                ephemeral=True,
            )
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
        await interaction.response.send_message(
            embed=persona.success_embed(
                "A Seat at the Table",
                f"You are seated, **{interaction.user.display_name}**. Henceforth, within "
                f"the Club you are known only as **{card}**. Speak through `/tarot speak` "
                f"and your true name shall remain hidden.",
            )
        )

    # --- speak ------------------------------------------------------------
    @tarot.command(name="speak")
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
                embed=persona.error_embed("This may only be spoken in the Tarot Club channel."),
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
    async def tarot_leave(self, interaction: discord.Interaction) -> None:
        """Vacate your seat at the Tarot Club."""
        if self.db.get_tarot_alias(interaction.user.id) is None:
            await interaction.response.send_message(
                embed=persona.error_embed("You hold no seat at the Tarot Club."),
                ephemeral=True,
            )
            return
        self.db.clear_tarot_alias(interaction.user.id)
        await interaction.response.send_message(
            embed=persona.fog_embed(
                "Seat Vacated", "You fade back into the gray fog, nameless once more."
            )
        )

    # --- open / close (admin) --------------------------------------------
    @tarot.command(name="open")
    @checks.admin_only
    async def tarot_open(self, interaction: discord.Interaction) -> None:
        """Open (or reveal) the restricted Tarot Club channel."""
        if not settings.get("features_tarot", True):
            await interaction.response.send_message(
                embed=persona.error_embed("The Tarot Club is disabled in /settings."),
                ephemeral=True,
            )
            return
        guild = interaction.guild
        if guild is None:
            return
        channel = discord.utils.get(guild.text_channels, name=TAROT_CHANNEL_NAME)
        if channel is None:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            try:
                channel = await guild.create_text_channel(
                    TAROT_CHANNEL_NAME, overwrites=overwrites,
                    topic="The weekly Tarot Club — anonymous trading and secrets.",
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    embed=persona.error_embed("I lack the power to raise the Club's chamber."),
                    ephemeral=True,
                )
                return
        await interaction.response.send_message(
            embed=persona.success_embed(
                "The Tarot Club Gathers",
                f"The chamber **{channel.mention}** has opened. Members may `/tarot join` "
                f"to receive an anonymous Major Arcana alias and trade secrets without "
                f"revealing their Discord identities.",
            )
        )

    @tarot.command(name="close")
    @checks.admin_only
    async def tarot_close(self, interaction: discord.Interaction) -> None:
        """Close the Tarot Club, stripping all aliases."""
        for row in self.db._fetchall("SELECT user_id FROM tarot_aliases"):
            self.db.clear_tarot_alias(int(row["user_id"]))
        self._webhooks.clear()
        await interaction.response.send_message(
            embed=persona.fog_embed(
                "The Gathering Disperses",
                "The Tarot Club dissolves back into the gray fog. All aliases are forgotten.",
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TarotCog(bot))

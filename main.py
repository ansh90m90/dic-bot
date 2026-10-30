"""The Fool's Attendant — entry point."""
from __future__ import annotations

import asyncio
import sys

import discord
from discord.ext import commands

import config
from db.database import Database
from utils.roles import sync_beyonder_role, sync_all_guild_roles

COGS: tuple[str, ...] = (
    "progression",
    "oracle",
    "economy",
    "apotheosis",
    "tarot",
    "anomalies",
    "madness",
    "admin",
    "features",
    "meta",
)


class FoolsAttendant(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True  # Required for voice channel digestion
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database(config.DATABASE_PATH)
        self.tree.error(self._on_tree_error)

    async def _on_tree_error(
        self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError
    ) -> None:
        if isinstance(error, discord.app_commands.errors.CheckFailure):
            msg = str(error) or "You lack the authority or Beyonder status to perform this action."
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="The Fog Rebuffs You",
                            description=msg,
                            color=0x7A1F2B,
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="The Fog Rebuffs You",
                            description=msg,
                            color=0x7A1F2B,
                        ),
                        ephemeral=True,
                    )
            except discord.HTTPException:
                pass
            return
        if isinstance(error, discord.app_commands.errors.CommandInvokeError):
            print(f"[The Fool's Attendant] Command error: {error.original!r}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="The Fog Rebuffs You",
                            description="An unforeseen disturbance wracks the Spirit World.",
                            color=0x7A1F2B,
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        "The Spirit World grows turbulent. Try again, Mortal.", ephemeral=True
                    )
            except discord.HTTPException:
                pass

    async def setup_hook(self) -> None:
        for name in COGS:
            await self.load_extension(f"cogs.{name}")

    async def on_ready(self) -> None:
        print(
            f"[The Fool's Attendant] Logged in as {self.user} ({self.user.id})"
            if self.user
            else "[The Fool's Attendant] Ready"
        )
        try:
            synced = await self.tree.sync()
            print(f"[The Fool's Attendant] Synced {len(synced)} slash commands.")
        except discord.HTTPException as exc:
            print(f"[The Fool's Attendant] Command sync failed: {exc}")

        # Synchronize Beyonder roles across all connected guilds
        for guild in self.guilds:
            try:
                metrics = await sync_all_guild_roles(self, guild)
                print(f"[The Fool's Attendant] Role sync for guild '{guild.name}': {metrics}")
            except Exception as exc:
                print(f"[The Fool's Attendant] Initial role sync error for '{guild.name}': {exc}")

    async def on_member_join(self, member: discord.Member) -> None:
        """Restore Beyonder role when an existing member rejoins the guild."""
        if member.bot or not member.guild:
            return
        self.db.touch_active(member.id)
        user = self.db.get_user(member.id)
        if user and user.get("pathway") and user.get("sequence") is not None:
            await sync_beyonder_role(
                self.db, member, user["pathway"], int(user["sequence"]), guild=member.guild
            )

    async def close(self) -> None:
        self.db.close()
        await super().close()


async def main() -> None:
    if not config.DISCORD_TOKEN:
        print(
            "The gray fog is silent: DISCORD_TOKEN is not set.\n"
            "Copy `.env.example` to `.env` and fill in your bot token.",
            file=sys.stderr,
        )
        sys.exit(1)

    if config.HA_ENABLED:
        from ha.runtime import run_ha

        await run_ha(FoolsAttendant)
        return

    bot = FoolsAttendant()
    try:
        await bot.start(config.DISCORD_TOKEN)
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())

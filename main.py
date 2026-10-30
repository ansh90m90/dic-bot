"""The Fool's Attendant — entry point.

Normal mode runs the bot directly. With ``HA_ENABLED=true`` it runs in
active–passive failover mode: a Firestore lease elects exactly one leader, and
the SQLite DB is snapshotted to Firebase Cloud Storage so a standby can take
over automatically.
"""
from __future__ import annotations

import asyncio
import sys

import discord
from discord.ext import commands

import config
from db.database import Database

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
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database(config.DATABASE_PATH)
        self.tree.error(self._on_tree_error)

    async def _on_tree_error(
        self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError
    ) -> None:
        # CheckFailures carry persona messages and are shown by discord.py.
        if isinstance(error, discord.app_commands.errors.CheckFailure):
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

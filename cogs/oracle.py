"""The Mystical Oracle — `/ask-oracle`, a Gemini-powered Spirit World guide."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import config
from settings import settings
from utils import gemini, persona
from db.database import Database


def oracle_limit(sequence: int | None) -> int:
    """Daily (rolling 24h) inquiry limit by Sequence."""
    if sequence is None or sequence >= 8:
        return int(settings.get("oracle_daily_limit", config.ORACLE_DAILY_LIMIT))  # Mortals: strictly 3
    if sequence >= 5:
        return 5
    if sequence >= 2:
        return 10
    return -1  # Kings of Angels and Deities: unlimited


class OracleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @app_commands.command(name="ask-oracle")
    @app_commands.describe(
        question="Your inquiry to the Spirit World.",
        spoiler="Set to true to permit major novel spoilers.",
    )
    async def ask_oracle(
        self,
        interaction: discord.Interaction,
        question: str,
        spoiler: bool = False,
    ) -> None:
        """Consult the Mystical Oracle (consumes 1 of your daily inquiries)."""
        row = self.db.ensure_user(interaction.user.id)
        seq = row["sequence"] if row["sequence"] is not None else None
        limit = oracle_limit(seq)

        if limit != -1:
            used = self.db.oracle_queries_since(interaction.user.id, 86400)
            if used >= limit:
                await interaction.response.send_message(
                    embed=persona.error_embed(persona.ORACLE_SPIRIT_DEPLETED),
                    ephemeral=True,
                )
                return

        await interaction.response.defer()
        self.db.record_oracle_query(interaction.user.id)
        answer = await gemini.ask_oracle(question, spoiler=spoiler)

        addr = "Mortal"
        if seq is not None:
            from data.pathways import address
            addr = address(seq)

        embed = persona.fog_embed(f"The Oracle Speaks — to the {addr}", answer)
        if limit != -1:
            used = self.db.oracle_queries_since(interaction.user.id, 86400)
            embed.set_footer(
                text=f"Inquiries used today: {used}/{limit} · the gray fog watches"
            )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OracleCog(bot))

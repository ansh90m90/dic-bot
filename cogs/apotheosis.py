"""Apotheosis — the trial to ascend from Sequence 1 to Sequence 0."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from data import ingredients, pathways
from utils import persona
from db.database import Database


def uniqueness_key(pathway_key: str) -> str:
    """Inventory key for a Pathway's Uniqueness."""
    return f"uniqueness:{pathway_key}"


class ApotheosisCog(commands.Cog):
    apotheosis = app_commands.Group(
        name="apotheosis", description="The trial to ascend to Sequence 0."
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @apotheosis.command(name="initiate")
    async def apotheosis_initiate(self, interaction: discord.Interaction) -> None:
        """(Sequence 1 only) Begin the server-wide trial to ascend to Sequence 0."""
        row = self.db.ensure_user(interaction.user.id)
        if row["pathway"] is None or int(row["sequence"]) != 1:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    "Only a **King of Angels** (Sequence 1) may initiate the Apotheosis."
                ),
                ephemeral=True,
            )
            return

        pathway_key = row["pathway"]
        data = pathways.get_pathway(pathway_key)

        if self.db.get_god(pathway_key) is not None:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    f"A **{data['name']}** already sits upon this Path. There may be only "
                    f"ONE Sequence 0 per Pathway."
                ),
                ephemeral=True,
            )
            return

        # Verification of full Apotheosis requirements:
        failures = []
        if float(row["digestion"]) < 100.0:
            failures.append(f"Digestion at {float(row['digestion']):.1f}% (demands 100%)")
        if float(row["sanity"]) < 90.0:
            failures.append(f"Sanity ≥ 90.0% (current: {float(row['sanity']):.1f}%)")
        if float(row["corruption"]) > 10.0:
            failures.append(f"Corruption ≤ 10.0% (current: {float(row['corruption']):.1f}%)")
        if int(row.get("tarot_coins", 0)) < 25:
            failures.append(f"25 Tarot Coins (you hold {int(row.get('tarot_coins', 0))})")

        u_key = uniqueness_key(pathway_key)
        if self.db.count_item(interaction.user.id, u_key) < 1:
            failures.append(f"the **Uniqueness of {data['name']}**")

        char_key = ingredients.characteristic_key(pathway_key, 1)
        held_char = self.db.count_item(interaction.user.id, char_key)
        if held_char < 3:
            failures.append(f"3× Sequence 1 Characteristics (you hold {held_char})")

        if failures:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    "The Uniqueness rejects your call. You lack the divine prerequisites:\n"
                    + "\n".join(f"• {f}" for f in failures)
                ),
                ephemeral=True,
            )
            return

        self.db.set_trial(interaction.user.id, 0, "apotheosis")
        await interaction.response.send_message(
            embed=persona.fog_embed(
                f"The Apotheosis of {data['name']} Begins",
                f"**{interaction.user.display_name}**, "
                f"{pathways.sequence_name(pathway_key, 1)} of the Path of **{data['name']}**, "
                f"has invoked the Uniqueness and declared their Apotheosis.\n\n"
                f"The server must bear witness. When the trial is met, an Archangel of the "
                f"Council shall crown them with `/angel apotheosis crown <user>`. Should "
                f"they fail, the Uniqueness devours them and their corruption shall be absolute.",
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ApotheosisCog(bot))

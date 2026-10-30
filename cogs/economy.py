"""Inventory, the market, and Sealed Artifact equip/unequip."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from data import ingredients, pathways
from utils import persona
from db.database import Database


class EconomyCog(commands.Cog):
    market = app_commands.Group(
        name="market", description="Trade ingredients and Gold Pounds."
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    # --- /inventory -------------------------------------------------------
    @app_commands.command(name="inventory")
    async def inventory(self, interaction: discord.Interaction) -> None:
        """View your ingredients, formulas, characteristics, and artifacts."""
        row = self.db.ensure_user(interaction.user.id)
        inv = self.db.get_inventory(interaction.user.id)
        arts = self.db.get_artifacts(interaction.user.id)

        embed = persona.fog_embed(
            f"{interaction.user.display_name}'s Inventory",
            f"Wealth: {persona.format_money(int(row['gold']), int(row['tarot_coins']))}",
        )

        formulas = [k for k in inv if ingredients.is_formula(k)]
        characteristics = [k for k in inv if ingredients.is_characteristic(k)]
        mats = {k: v for k, v in inv.items() if ingredients.is_ingredient(k)}

        if formulas:
            embed.add_field(
                name="Potion Formulas",
                value="\n".join(f"{self._pretty_key(k)} ×{v}" for k, v in sorted(formulas)),
                inline=False,
            )
        if characteristics:
            embed.add_field(
                name="Beyonder Characteristics",
                value="\n".join(f"{self._pretty_key(k)} ×{v}" for k, v in sorted(characteristics)),
                inline=False,
            )
        if mats:
            embed.add_field(
                name="Ingredients",
                value="\n".join(
                    f"{k} ×{v} ({ingredients.rarity_of(k)})" for k, v in sorted(mats)
                ),
                inline=False,
            )

        if arts:
            art_lines = []
            for a in arts:
                marker = " **[equipped]**" if int(a["equipped"]) else ""
                art_lines.append(f"`{a['artifact_id']}` {a['name']} (Grade {a['grade']}){marker}")
            embed.add_field(name="Sealed Artifacts", value="\n".join(art_lines), inline=False)

        if not formulas and not characteristics and not mats and not arts:
            embed.add_field(
                name="Empty",
                value="Your satchel holds nothing but dust. Participate in raids and "
                      "anomalies to gather ingredients.",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    # --- /market trade ----------------------------------------------------
    @market.command(name="trade")
    @app_commands.describe(
        target="Who receives the goods.",
        item="The ingredient/formula to transfer, or 'gold'.",
        amount="Quantity to transfer.",
    )
    async def market_trade(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        item: str,
        amount: int = 1,
    ) -> None:
        """Safely transfer ingredients or Gold Pounds to another Beyonder."""
        if target.id == interaction.user.id:
            await interaction.response.send_message(
                embed=persona.error_embed("You cannot trade with yourself, Mortal."),
                ephemeral=True,
            )
            return
        if amount < 1:
            await interaction.response.send_message(
                embed=persona.error_embed("The quantity must be positive."),
                ephemeral=True,
            )
            return

        item_lower = item.lower().strip()
        if item_lower in ("gold", "gold pounds", "gold pound", "pounds"):
            sender = self.db.ensure_user(interaction.user.id)
            if int(sender["gold"]) < amount:
                await interaction.response.send_message(
                    embed=persona.error_embed("You do not hold that many Gold Pounds."),
                    ephemeral=True,
                )
                return
            self.db.add_gold(interaction.user.id, -amount)
            self.db.add_gold(target.id, amount)
            await interaction.response.send_message(
                embed=persona.success_embed(
                    "Trade Sealed",
                    f"**{interaction.user.display_name}** has paid "
                    f"**{amount:,} Gold Pounds** to **{target.display_name}**.",
                )
            )
            return

        key = self._resolve_item_key(interaction.user.id, item)
        if key is None:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    f"You hold no item matching **{item}**. Check `/inventory`."
                ),
                ephemeral=True,
            )
            return
        if not self.db.remove_item(interaction.user.id, key, amount):
            await interaction.response.send_message(
                embed=persona.error_embed(f"You do not hold {amount}× of that item."),
                ephemeral=True,
            )
            return
        self.db.add_item(target.id, key, amount)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Trade Sealed",
                f"**{interaction.user.display_name}** has passed **{amount}× "
                f"{self._pretty_key(key)}** to **{target.display_name}** under the watch "
                f"of the gray fog.",
            )
        )

    def _resolve_item_key(self, user_id: int, item: str) -> str | None:
        inv = self.db.get_inventory(user_id)
        target = item.strip().lower().replace(" ", "_")
        for key in inv:
            if key.lower() == target or key.lower() == item.strip().lower():
                return key
        for key in inv:
            if target in key.lower():
                return key
        return None

    def _pretty_key(self, key: str) -> str:
        if ingredients.is_formula(key):
            _, pkey, s = key.split(":")
            return f"{pathways.sequence_name(pkey, int(s))} formula"
        if ingredients.is_characteristic(key):
            _, pkey, s = key.split(":")
            return f"{pathways.sequence_name(pkey, int(s))} characteristic"
        if key.startswith("uniqueness:"):
            _, pkey = key.split(":")
            return f"Uniqueness of {pathways.get_pathway(pkey)['name']}"
        return key

    # --- /equip & /unequip ------------------------------------------------
    @app_commands.command(name="equip")
    @app_commands.describe(artifact_id="The Sealed Artifact's id (see /inventory).")
    async def equip(self, interaction: discord.Interaction, artifact_id: str) -> None:
        """Equip a Sealed Artifact — accepting its curse."""
        art = self.db.get_artifact(artifact_id)
        if art is None or int(art["owner_id"]) != interaction.user.id:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    f"You hold no Sealed Artifact with the id **{artifact_id}**."
                ),
                ephemeral=True,
            )
            return
        self.db.equip_artifact(interaction.user.id, artifact_id)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Artifact Equipped",
                f"You have equipped **{art['name']}** (Grade {art['grade']}).\n"
                f"*Perk:* {art['effect']}\n*Curse:* {art['curse']}\n\n"
                f"The curse is now upon you. Seal it (`/unequip`) before you rest, lest "
                f"it drain your sanity while you sleep.",
            )
        )

    @app_commands.command(name="unequip")
    async def unequip(self, interaction: discord.Interaction) -> None:
        """Seal (unequip) your currently equipped Sealed Artifact."""
        art_id = self.db.unequip_artifact(interaction.user.id)
        if art_id is None:
            await interaction.response.send_message(
                embed=persona.error_embed("You have no Sealed Artifact equipped."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Artifact Sealed",
                f"The artifact **{art_id}** is sealed once more. Its curse recedes — for now.",
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EconomyCog(bot))

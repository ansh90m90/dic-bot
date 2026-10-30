"""Inventory and player-to-player market trading."""
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
        """View your ingredients, formulas, characteristics, and currencies."""
        row = self.db.ensure_user(interaction.user.id)
        if row["pathway"] is None:
            await interaction.response.send_message(
                embed=persona.fog_embed(
                    "Ordinary Mortal Pouch",
                    "You are an ordinary mortal without Beyonder spirituality or ingredients.\n\n"
                    "In this server, only members seeking power and authority brew and drink their Sequence 9 potion "
                    "(`/pathway choose <pathway>`) to awaken as a Beyonder.",
                ),
                ephemeral=True,
            )
            return

        inv = self.db.get_inventory(interaction.user.id)

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

        if not formulas and not characteristics and not mats:
            embed.add_field(
                name="Empty",
                value="Your satchel holds nothing but dust. Participate in raids, anomalies, "
                      "and the shop to gather ingredients.",
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EconomyCog(bot))

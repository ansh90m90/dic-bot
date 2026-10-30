"""Daily reward, the leaderboard, and the ingredient/formula shop."""
from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from data import ingredients, pathways
from utils import persona
from db.database import Database
from settings import settings

_FORMULA_PRICES = {8: 100, 7: 200, 6: 500, 5: 1000, 4: 3000, 3: 8000, 2: 20000, 1: 50000}


class FeaturesCog(commands.Cog):
    shop = app_commands.Group(
        name="shop", description="Buy potion ingredients and formulas."
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    # --- /daily -----------------------------------------------------------
    @app_commands.command(name="daily")
    async def daily(self, interaction: discord.Interaction) -> None:
        """Claim your daily reward of Gold Pounds and a Tarot Coin."""
        if not settings.get("features_daily", True):
            await interaction.response.send_message(
                embed=persona.error_embed("The daily boon is sealed."), ephemeral=True
            )
            return
        if not self.db.claim_daily(interaction.user.id):
            await interaction.response.send_message(
                embed=persona.error_embed(
                    "You have already received today's boon. Return after midnight (00:00 UTC)."
                ),
                ephemeral=True,
            )
            return
        gold = int(settings.get("daily_gold", 50))
        tarot = int(settings.get("daily_tarot", 1))
        self.db.add_gold(interaction.user.id, gold)
        self.db.add_tarot(interaction.user.id, tarot)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Daily Boon",
                f"The gray fog grants you **{gold} Gold Pounds** and **{tarot} Tarot "
                f"Coin{'s' if tarot != 1 else ''}**.",
            )
        )

    # --- /leaderboard -----------------------------------------------------
    @app_commands.command(name="leaderboard")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        """Rank the most advanced Beyonders of the server."""
        rows = self.db.leaderboard(10)
        if not rows:
            await interaction.response.send_message(
                embed=persona.fog_embed(
                    "The Ladder", "No Beyonder has yet sworn fealty to a Pathway."
                )
            )
            return
        guild = interaction.guild
        lines = []
        for i, r in enumerate(rows, 1):
            member = guild.get_member(int(r["user_id"])) if guild else None
            name = member.display_name if member else f"<@{r['user_id']}>"
            title = pathways.sequence_name(r["pathway"], int(r["sequence"]))
            lines.append(
                f"**{i}.** {name} — {title} (Seq {r['sequence']}) · "
                f"{float(r['digestion']):.0f}% digestion"
            )
        embed = persona.fog_embed("The Ladder of the 22 Pathways", "\n".join(lines))
        await interaction.response.send_message(embed=embed)

    # --- /shop ------------------------------------------------------------
    @shop.command(name="list")
    async def shop_list(self, interaction: discord.Interaction) -> None:
        """List shop prices."""
        if not settings.get("features_shop", True):
            await interaction.response.send_message(
                embed=persona.error_embed("The shop is sealed by the gray fog."),
                ephemeral=True,
            )
            return
        p = {
            "common": settings.get("shop_common_price", 25),
            "uncommon": settings.get("shop_uncommon_price", 100),
            "rare": settings.get("shop_rare_price", 400),
            "legendary": settings.get("shop_legendary_price", 1500),
        }
        lines = [f"`{k}` ingredient — **{v}** Gold" for k, v in p.items()]
        lines.append("`formula` — the formula for your **next Sequence** (price varies)")
        embed = persona.fog_embed("The Hidden Shop", "\n".join(lines))
        embed.set_footer(text="Buy with /shop buy <item>")
        await interaction.response.send_message(embed=embed)

    @shop.command(name="buy")
    @app_commands.describe(item="What to buy: common / uncommon / rare / legendary / formula.")
    async def shop_buy(self, interaction: discord.Interaction, item: str) -> None:
        """Purchase a potion ingredient or your next-sequence formula."""
        if not settings.get("features_shop", True):
            await interaction.response.send_message(
                embed=persona.error_embed("The shop is sealed by the gray fog."),
                ephemeral=True,
            )
            return
        item = item.strip().lower()
        row = self.db.ensure_user(interaction.user.id)

        if item == "formula":
            if row["pathway"] is None or int(row["sequence"]) <= 0:
                await interaction.response.send_message(
                    embed=persona.error_embed(
                        "Swear fealty with `/pathway choose` first — and you cannot buy a "
                        "formula beyond Sequence 0."
                    ),
                    ephemeral=True,
                )
                return
            target = int(row["sequence"]) - 1
            price = _FORMULA_PRICES.get(target, 0)
            if int(row["gold"]) < price:
                await interaction.response.send_message(
                    embed=persona.error_embed(
                        f"That formula costs **{price:,}** Gold; you hold {int(row['gold']):,}."
                    ),
                    ephemeral=True,
                )
                return
            self.db.add_gold(interaction.user.id, -price)
            fkey = ingredients.formula_key(row["pathway"], target)
            self.db.add_item(interaction.user.id, fkey, 1)
            await interaction.response.send_message(
                embed=persona.success_embed(
                    "Formula Acquired",
                    f"You purchased the **{pathways.sequence_name(row['pathway'], target)}** "
                    f"formula for {price:,} Gold.",
                )
            )
            return

        price_key = {
            "common": "shop_common_price",
            "uncommon": "shop_uncommon_price",
            "rare": "shop_rare_price",
            "legendary": "shop_legendary_price",
        }.get(item)
        if price_key is None:
            await interaction.response.send_message(
                embed=persona.error_embed("Choose: common / uncommon / rare / legendary / formula."),
                ephemeral=True,
            )
            return
        price = int(settings.get(price_key, 25))
        if int(row["gold"]) < price:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    f"That costs **{price}** Gold; you hold {int(row['gold']):,}."
                ),
                ephemeral=True,
            )
            return
        self.db.add_gold(interaction.user.id, -price)
        ing = random.choice(ingredients.INGREDIENT_NAMES[item])
        self.db.add_item(interaction.user.id, ing, 1)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Purchased", f"You bought a **{ing}** ({item}) for {price} Gold."
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FeaturesCog(bot))

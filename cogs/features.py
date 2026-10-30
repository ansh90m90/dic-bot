"""Daily reward, leaderboard, shop, and interactive money/tarot earning features."""
from __future__ import annotations

import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from data import ingredients, pathways
from utils import checks, persona
from db.database import Database
from settings import settings

# Scaled formula and characteristic prices
_FORMULA_PRICES = {
    8: 250,
    7: 750,
    6: 2000,
    5: 6000,
    4: 18000,
    3: 45000,
    2: 100000,
    1: 250000,
}

_CHAR_PRICES = {
    8: 500,
    7: 1500,
    6: 4000,
    5: 12000,
    4: 36000,
    3: 90000,
    2: 200000,
    1: 500000,
}

BOUNTIES = {
    "wraith": {
        "title": "Roaming Wraith of Backlund",
        "desc": "A spirit wracked by resentment haunts the gas-lit streets.",
        "difficulty": "Moderate",
        "gold_min": 250,
        "gold_max": 500,
        "tarot": 1,
        "success_rate": 0.85,
    },
    "werewolf": {
        "title": "Rampaging Werewolf",
        "desc": "A Sequence 7 Werewolf of the Chained pathway has succumbed to bloodlust.",
        "difficulty": "Demanding",
        "gold_min": 500,
        "gold_max": 1000,
        "tarot": 2,
        "success_rate": 0.75,
    },
    "spectator": {
        "title": "Corrupted Telepathist Cult",
        "desc": "Heretics weaving manipulative mental illusions across the docks.",
        "difficulty": "Perilous",
        "gold_min": 1000,
        "gold_max": 2000,
        "tarot": 3,
        "success_rate": 0.65,
    },
    "abyss_fiend": {
        "title": "Demon of the Abyss",
        "desc": "A foul emissary radiating sulfur and abyssal corruption.",
        "difficulty": "Nightmarish",
        "gold_min": 2000,
        "gold_max": 4000,
        "tarot": 5,
        "success_rate": 0.55,
    },
}


class FeaturesCog(commands.Cog):
    shop = app_commands.Group(
        name="shop", description="Buy potion ingredients, formulas, and characteristics."
    )
    bounty = app_commands.Group(
        name="bounty", description="Undertake Spirit World bounties for Gold and Tarot Coins."
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_bounty: dict[int, float] = {}
        self._last_divine: dict[int, float] = {}

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    # --- /daily -----------------------------------------------------------
    @app_commands.command(name="daily")
    @checks.beyonder_only
    async def daily(self, interaction: discord.Interaction) -> None:
        """Claim your daily reward of Gold Pounds and Tarot Coins."""
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

    # --- /divine ----------------------------------------------------------
    @app_commands.command(name="divine")
    @checks.beyonder_only
    @app_commands.describe(inquiry="What fortune or spirit question you wish to divine.")
    async def divine(self, interaction: discord.Interaction, inquiry: str) -> None:
        """Perform a Spirit Pendulum divination to reveal omens and earn Gold & Tarot Coins."""
        user_id = interaction.user.id
        now = time.time()
        last = self._last_divine.get(user_id, 0.0)
        cooldown = 1800  # 30 minute cooldown
        if now - last < cooldown:
            rem = int(cooldown - (now - last))
            mins = rem // 60
            secs = rem % 60
            await interaction.response.send_message(
                embed=persona.fog_embed(
                    "Spirit World Turbulence",
                    f"Your spirituality has not yet stabilized from your last divination. "
                    f"Wait **{mins}m {secs}s** before inquiring again.",
                ),
                ephemeral=True,
            )
            return

        self._last_divine[user_id] = now
        self.db.touch_active(user_id)
        user = self.db.ensure_user(user_id)

        roll = random.random()
        # Scale fortune by sanity
        sanity = float(user.get("sanity") or 100.0)
        bonus = (sanity / 100.0) * 0.15

        if roll + bonus > 0.85:
            # Celestial Revelation: huge bounty
            gold_won = random.randint(300, 750)
            tarot_won = random.randint(2, 4)
            self.db.add_gold(user_id, gold_won)
            self.db.add_tarot(user_id, tarot_won)
            await interaction.response.send_message(
                embed=persona.success_embed(
                    "Auspicious Revelation",
                    f"The spirit pendulum swings clockwise in vigorous harmony!\n\n"
                    f"**Inquiry:** *\"{inquiry}\"*\n"
                    f"**Omen:** *The stars align in favor of the Fool. A hidden benefactor leaves a purse.*\n"
                    f"✦ **Rewards:** **+{gold_won:,} Gold Pounds** & **+{tarot_won} Tarot Coins**!",
                )
            )
        elif roll + bonus > 0.40:
            # Spirit World Whisper: moderate gold
            gold_won = random.randint(100, 300)
            tarot_won = 1
            self.db.add_gold(user_id, gold_won)
            self.db.add_tarot(user_id, tarot_won)
            await interaction.response.send_message(
                embed=persona.success_embed(
                    "Favorable Omens",
                    f"The pendulum circles gently, catching the light of the crimson moon.\n\n"
                    f"**Inquiry:** *\"{inquiry}\"*\n"
                    f"**Omen:** *The spirits whisper secrets of forgotten coin and fate.*\n"
                    f"✦ **Rewards:** **+{gold_won:,} Gold Pounds** & **+{tarot_won} Tarot Coin**.",
                )
            )
        elif roll > 0.15:
            # Small whisper
            gold_won = random.randint(40, 100)
            self.db.add_gold(user_id, gold_won)
            await interaction.response.send_message(
                embed=persona.fog_embed(
                    "Murmurs in the Mist",
                    f"The pendulum oscillates irregularly.\n\n"
                    f"**Inquiry:** *\"{inquiry}\"*\n"
                    f"**Omen:** *A fleeting whisper guides you to a modest discovery.*\n"
                    f"✦ **Rewards:** **+{gold_won} Gold Pounds**.",
                )
            )
        else:
            # Bad omen
            new_c = self.db.add_corruption(user_id, 3.0)
            await interaction.response.send_message(
                embed=persona.error_embed(
                    f"The pendulum twitches violently counter-clockwise!\n\n"
                    f"**Inquiry:** *\"{inquiry}\"*\n"
                    f"**Omen:** *A horrifying gaze brushes past your spirituality from the void.*\n"
                    f"• **+3.0% Corruption** (now {new_c:.1f}%)."
                )
            )

    # --- /bounty ----------------------------------------------------------
    @bounty.command(name="list")
    async def bounty_list(self, interaction: discord.Interaction) -> None:
        """View available Spirit World hunting contracts."""
        embed = persona.fog_embed(
            "Spirit World Bounty Board",
            "Accept dangerous hunting contracts to reap Gold Pounds and rare Tarot Coins.\n"
            "Hunt a target using `/bounty hunt <key>`.",
        )
        for k, v in BOUNTIES.items():
            embed.add_field(
                name=f"`{k}` — {v['title']} ({v['difficulty']})",
                value=(
                    f"{v['desc']}\n"
                    f"**Reward:** {v['gold_min']:,}–{v['gold_max']:,} Gold · **{v['tarot']} Tarot Coins**\n"
                    f"**Survival Chance:** {int(v['success_rate'] * 100)}%"
                ),
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    @bounty.command(name="hunt")
    @checks.beyonder_only
    @app_commands.describe(target="The contract key to hunt: wraith / werewolf / spectator / abyss_fiend.")
    async def bounty_hunt(self, interaction: discord.Interaction, target: str) -> None:
        """Undertake a bounty contract to slay a target for Gold & Tarot Coins."""
        key = target.strip().lower()
        if key not in BOUNTIES:
            await interaction.response.send_message(
                embed=persona.error_embed(f"Unknown contract: `{target}`. Check `/bounty list`."),
                ephemeral=True,
            )
            return

        user_id = interaction.user.id
        now = time.time()
        last = self._last_bounty.get(user_id, 0.0)
        cooldown = 1800  # 30 minutes
        if now - last < cooldown:
            rem = int(cooldown - (now - last))
            await interaction.response.send_message(
                embed=persona.fog_embed(
                    "Exhausted Spirituality",
                    f"You must rest before taking another bounty contract. Available in **{rem // 60}m {rem % 60}s**.",
                ),
                ephemeral=True,
            )
            return

        self._last_bounty[user_id] = now
        self.db.touch_active(user_id)
        b = BOUNTIES[key]
        user = self.db.ensure_user(user_id)

        # Scale victory chance by sequence rank
        seq = int(user.get("sequence") if user.get("sequence") is not None else 9)
        rank_bonus = max(0.0, (9 - seq) * 0.03)  # High sequences get up to +27% bonus
        success = random.random() < (b["success_rate"] + rank_bonus)

        if success:
            gold_won = random.randint(b["gold_min"], b["gold_max"])
            tarot_won = b["tarot"]
            self.db.add_gold(user_id, gold_won)
            self.db.add_tarot(user_id, tarot_won)

            # Chance of random monster ingredient drop
            loot = ""
            if random.random() < 0.60:
                ing = ingredients.roll_ingredient()
                self.db.add_item(user_id, ing, 1)
                loot = f"\n• **Loot:** Salvaged 1× **{ing}** from the remains!"

            await interaction.response.send_message(
                embed=persona.success_embed(
                    f"Bounty Claimed: {b['title']}",
                    f"You have vanquished the **{b['title']}** in mortal combat!\n\n"
                    f"✦ **Bounty Paid:** **+{gold_won:,} Gold Pounds** & **+{tarot_won} Tarot Coins**"
                    f"{loot}",
                )
            )
        else:
            # Hunt failure
            corr_add = random.uniform(4.0, 10.0)
            sanity_loss = random.uniform(5.0, 12.0)
            self.db.add_corruption(user_id, corr_add)
            self.db.add_sanity(user_id, -sanity_loss)
            await interaction.response.send_message(
                embed=persona.error_embed(
                    f"**Hunt Failed: {b['title']}!**\n\n"
                    f"The target overpowered your spiritual defense! You were forced to flee through the fog.\n"
                    f"• **+{corr_add:.1f}% Corruption**\n"
                    f"• **-{sanity_loss:.1f}% Sanity**"
                )
            )

    # --- /sacrifice -------------------------------------------------------
    @app_commands.command(name="sacrifice")
    @checks.beyonder_only
    @app_commands.describe(
        item="Ingredient to sacrifice to the gray fog.",
        qty="Quantity to sacrifice (default: 1)."
    )
    async def sacrifice(self, interaction: discord.Interaction, item: str, qty: int = 1) -> None:
        """Sacrifice monster ingredients to the gray fog in exchange for Gold and Tarot Coins."""
        if qty < 1:
            qty = 1
        user_id = interaction.user.id
        self.db.touch_active(user_id)

        # Resolve inventory item
        inv = self.db.get_inventory(user_id)
        target = item.strip().lower()
        matched_key = next((k for k in inv if k.lower() == target), None)
        if matched_key is None:
            matched_key = next((k for k in inv if target in k.lower()), None)

        if matched_key is None:
            await interaction.response.send_message(
                embed=persona.error_embed(f"You do not possess `{item}` in your inventory."),
                ephemeral=True,
            )
            return

        held = inv[matched_key]
        if held < qty:
            await interaction.response.send_message(
                embed=persona.error_embed(f"You only hold {held}× of **{matched_key}**."),
                ephemeral=True,
            )
            return

        rarity = ingredients.rarity_of(matched_key)
        gold_per_unit = {
            "common": 50,
            "uncommon": 180,
            "rare": 700,
            "legendary": 2500,
        }.get(rarity, 30)

        tarot_per_unit = {
            "common": 0,
            "uncommon": 0,
            "rare": 1,
            "legendary": 3,
        }.get(rarity, 0)

        total_gold = gold_per_unit * qty
        total_tarot = tarot_per_unit * qty

        self.db.remove_item(user_id, matched_key, qty)
        self.db.add_gold(user_id, total_gold)
        if total_tarot > 0:
            self.db.add_tarot(user_id, total_tarot)

        tarot_line = f" and **+{total_tarot} Tarot Coins**" if total_tarot > 0 else ""
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Sacrifice Accepted",
                f"You offer **{qty}× {matched_key}** ({rarity}) upon the sacrificial altar.\n"
                f"The gray fog consumes the offering and leaves behind **+{total_gold:,} Gold Pounds**{tarot_line}.",
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
            vc_hrs = int(r.get("vc_minutes") or 0) / 60.0
            lines.append(
                f"**{i}.** {name} — {title} (Seq {r['sequence']}) · "
                f"{float(r['digestion']):.0f}% digestion · {vc_hrs:.1f}h VC"
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
            "common": settings.get("shop_common_price", 50),
            "uncommon": settings.get("shop_uncommon_price", 200),
            "rare": settings.get("shop_rare_price", 800),
            "legendary": settings.get("shop_legendary_price", 3000),
        }
        lines = [f"`{k}` ingredient — **{v}** Gold" for k, v in p.items()]
        lines.append("`formula` — the potion formula for your **next Sequence**")
        lines.append("`characteristic` — the Beyonder characteristic for your **next Sequence**")
        embed = persona.fog_embed("The Hidden Shop", "\n".join(lines))
        embed.set_footer(text="Buy with /shop buy <item>")
        await interaction.response.send_message(embed=embed)

    @shop.command(name="buy")
    @app_commands.describe(
        item="What to buy: common / uncommon / rare / legendary / formula / characteristic."
    )
    async def shop_buy(self, interaction: discord.Interaction, item: str) -> None:
        """Purchase potion ingredients, formulas, or characteristics."""
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

        if item == "characteristic":
            if row["pathway"] is None or int(row["sequence"]) <= 0:
                await interaction.response.send_message(
                    embed=persona.error_embed(
                        "Swear fealty with `/pathway choose` first — and you cannot buy a "
                        "characteristic beyond Sequence 0."
                    ),
                    ephemeral=True,
                )
                return
            target = int(row["sequence"]) - 1
            price = _CHAR_PRICES.get(target, 0)
            if int(row["gold"]) < price:
                await interaction.response.send_message(
                    embed=persona.error_embed(
                        f"That characteristic costs **{price:,}** Gold; you hold {int(row['gold']):,}."
                    ),
                    ephemeral=True,
                )
                return
            self.db.add_gold(interaction.user.id, -price)
            ckey = ingredients.characteristic_key(row["pathway"], target)
            self.db.add_item(interaction.user.id, ckey, 1)
            await interaction.response.send_message(
                embed=persona.success_embed(
                    "Characteristic Acquired",
                    f"You purchased the **{pathways.sequence_name(row['pathway'], target)}** "
                    f"characteristic for {price:,} Gold.",
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
                embed=persona.error_embed("Choose: common / uncommon / rare / legendary / formula / characteristic."),
                ephemeral=True,
            )
            return
        price = int(settings.get(price_key, 50))
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

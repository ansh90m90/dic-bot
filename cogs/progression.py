"""Beyonder progression: pathway fealty, status, advancement, and digestion."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import config
from settings import settings

from data import ingredients, pathways
from data.artifacts import get_artifact
from utils import persona
from utils.roles import sync_beyonder_role
from db.database import Database


class ProgressionCog(commands.Cog):
    pathway = app_commands.Group(
        name="pathway", description="Swear fealty to a Beyonder Pathway."
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    # --- digestion from activity -----------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        user_id = message.author.id
        user = self.db.ensure_user(user_id)  # one fetch (INSERT only on first sight)
        if user["pathway"] is None or user["sequence"] is None:
            return

        today = datetime.now(timezone.utc).date().isoformat()
        days = int(user["active_days"]) + (1 if user["last_activity_date"] != today else 0)
        digestion = float(user["digestion"])
        last_ts = float(user["last_digest_ts"])

        if settings.get("features_digestion", True):
            cooldown = int(settings.get("activity_digest_cooldown", config.ACTIVITY_DIGEST_COOLDOWN))
            now = time.time()
            if now - last_ts >= cooldown:
                seq = int(user["sequence"])
                base = float(settings.get("digest_per_message", config.DIGEST_PER_MESSAGE))
                mult = {9: 1.0, 8: 1.0, 7: 0.5, 6: 0.5, 5: 0.375,
                        4: 0.25, 3: 0.2, 2: 0.125, 1: 0.075}.get(seq, 1.0)
                gain = base * mult
                if not int(user["corrupted_state"]):
                    equipped = self.db.get_equipped(user_id)
                    if equipped and equipped["definition_key"]:
                        art = get_artifact(equipped["definition_key"])
                        if art and art["modifiers"].get("digestion_multiplier"):
                            gain *= art["modifiers"]["digestion_multiplier"]
                digestion = min(100.0, float(user["digestion"]) + gain)
                last_ts = now

        self.db.activity_tick(user_id, digestion, last_ts, days, today)

    # --- /pathway choose --------------------------------------------------
    @pathway.command(name="choose")
    @app_commands.describe(pathway_name="The Pathway to swear fealty to (e.g. Fool).")
    async def pathway_choose(self, interaction: discord.Interaction, pathway_name: str) -> None:
        """Swear fealty to a Pathway at Sequence 9."""
        key = pathways.resolve_pathway(pathway_name)
        if key is None:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    f"No such Pathway is known to the gray fog: **{pathway_name}**. "
                    "Use `/pathway list` to see the 22 Paths."
                ),
                ephemeral=True,
            )
            return

        user = self.db.ensure_user(interaction.user.id)
        if user["pathway"] is not None:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    "You are already sworn to a Pathway. The Beyonders' path is "
                    "singular — there is no turning back once the potion is drunk."
                ),
                ephemeral=True,
            )
            return

        self.db.register_pathway(interaction.user.id, key)
        await sync_beyonder_role(self.db, interaction.user, key, 9)
        seq9 = pathways.sequence_name(key, 9)
        data = pathways.get_pathway(key)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Fealty Sworn",
                f"Welcome, **{seq9}**, newly risen upon the Path of **{data['name']}**. "
                f"Your potion is drunk, your digestion begins, and the gray fog watches. "
                f"Address yourself to the **{data['above']}**."
            ),
        )

    @pathway.command(name="list")
    async def pathway_list(self, interaction: discord.Interaction) -> None:
        """List the 22 Pathways and their groups."""
        lines: list[str] = []
        for group, keys in pathways.GROUPS.items():
            names = ", ".join(pathways.get_pathway(k)["name"] for k in keys)
            lines.append(f"**{group}** — {names}")
        embed = persona.fog_embed("The 22 Pathways", "\n".join(lines))
        embed.add_field(
            name="Swear Fealty",
            value="Use `/pathway choose <name>` to begin at Sequence 9.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    # --- /status ----------------------------------------------------------
    @app_commands.command(name="status")
    @app_commands.describe(user="Whose status to inspect (defaults to you).")
    async def status(self, interaction: discord.Interaction,
                     user: discord.Member | None = None) -> None:
        """Inspect Sequence, Digestion, Sanity, Corruption, and equipped artifacts."""
        target = user or interaction.user
        row = self.db.ensure_user(target.id)
        if row["pathway"] is None:
            await interaction.response.send_message(
                embed=persona.fog_embed(
                    f"{target.display_name}",
                    "This one has not yet sworn fealty to a Pathway. They remain an "
                    "uninitiated Mortal.",
                )
            )
            return

        data = pathways.get_pathway(row["pathway"])
        seq = int(row["sequence"])
        title = pathways.sequence_name(row["pathway"], seq)
        rank = pathways.rank_title(seq)

        equipped = self.db.get_equipped(target.id)
        equipped_line = (
            f"**{equipped['name']}** (Grade {equipped['grade']})" if equipped else "None"
        )

        embed = persona.fog_embed(
            f"{target.display_name} — {title}",
            f"**Pathway:** {data['name']}  ·  **Sequence {seq}** ({rank})\n"
            f"**Above the Sequences:** {data['above']}",
        )
        embed.add_field(name="Digestion", value=f"{float(row['digestion']):.1f}%", inline=True)
        embed.add_field(
            name="Sanity",
            value=f"{float(row['sanity']):.1f}% ({persona.sanity_label(float(row['sanity']))})",
            inline=True,
        )
        embed.add_field(
            name="Corruption",
            value=f"{float(row['corruption']):.1f}% "
                  f"({persona.corruption_label(float(row['corruption']))})",
            inline=True,
        )
        embed.add_field(
            name="Wealth",
            value=persona.format_money(int(row["gold"]), int(row["tarot_coins"])),
            inline=True,
        )
        embed.add_field(name="Active Days", value=str(int(row["active_days"])), inline=True)
        embed.add_field(name="Equipped Artifact", value=equipped_line, inline=False)
        await interaction.response.send_message(embed=embed)

    # --- /digest ----------------------------------------------------------
    @app_commands.command(name="digest")
    async def digest(self, interaction: discord.Interaction) -> None:
        """View your current digestion and the Acting Method of your Sequence."""
        row = self.db.ensure_user(interaction.user.id)
        if row["pathway"] is None:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    "You have not sworn fealty to a Pathway. Use `/pathway choose` first."
                ),
                ephemeral=True,
            )
            return
        seq = int(row["sequence"])
        title = pathways.sequence_name(row["pathway"], seq)
        next_title = pathways.sequence_name(row["pathway"], seq - 1) if seq > 0 else "True God"
        embed = persona.fog_embed(
            f"Digestion — {title}",
            f"**Current digestion:** {float(row['digestion']):.1f}% / 100%\n"
            f"**Next Sequence:** {next_title}",
        )
        embed.add_field(
            name="Acting Method",
            value=(
                f"Embody the essence of the **{title}**. Speak as one, act as one, and "
                f"the potion's madness shall become your power. Activity in the server "
                f"feeds your digestion — but true Beyonders act their role, not merely "
                f"their posts."
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    # --- /advance ---------------------------------------------------------
    @app_commands.command(name="advance")
    async def advance(self, interaction: discord.Interaction) -> None:
        """Attempt to advance to the next Sequence along your Pathway."""
        row = self.db.ensure_user(interaction.user.id)
        if row["pathway"] is None:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    "You have no Pathway. Swear fealty with `/pathway choose`."
                ),
                ephemeral=True,
            )
            return
        seq = int(row["sequence"])
        if seq == 0:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    "You already stand at the apex. There is nothing above Sequence 0."
                ),
                ephemeral=True,
            )
            return

        target = seq - 1
        req = pathways.advancement_requirements(target)
        if req.get("apotheosis"):
            await interaction.response.send_message(
                embed=persona.fog_embed(
                    "The Final Threshold",
                    "Sequence 0 is not reached by potion alone. Only a King of Angels "
                    "may **initiate the Apotheosis** — use `/apotheosis initiate`.",
                ),
                ephemeral=True,
            )
            return

        failures: list[str] = []
        if float(row["digestion"]) < 100.0:
            failures.append(f"digestion at {float(row['digestion']):.1f}% (need 100%)")
        if int(row["gold"]) < req["gold"]:
            failures.append(f"{req['gold']:,} Gold Pounds (you hold {int(row['gold']):,})")
        if int(row["active_days"]) < req["min_active_days"]:
            failures.append(
                f"{req['min_active_days']} days of sustained presence "
                f"(you have {int(row['active_days'])})"
            )

        formula = ingredients.formula_key(row["pathway"], target)
        characteristic = ingredients.characteristic_key(row["pathway"], target)
        checks = (
            (formula, f"the **{pathways.sequence_name(row['pathway'], target)}** formula"),
            (characteristic, f"the **{pathways.sequence_name(row['pathway'], target)}** characteristic"),
        )
        for key, label in checks:
            if self.db.count_item(interaction.user.id, key) < 1:
                failures.append(label)

        for rarity, count in req["ingredients"].items():
            held = sum(
                qty for k, qty in self.db.get_inventory(interaction.user.id).items()
                if ingredients.rarity_of(k) == rarity
            )
            if held < count:
                failures.append(f"{count}× {rarity} ingredients (you hold {held})")

        if req.get("slot_capped"):
            cap = 3  # Sequence 1 characteristics per pathway
            if self.db.count_at_sequence(row["pathway"], 1) >= cap:
                failures.append("a vacant King of Angels slot (Sequence 1 slots are full)")

        if failures:
            await interaction.response.send_message(
                embed=persona.error_embed(
                    "The potion rejects you. You still lack:\n"
                    + "\n".join(f"• {f}" for f in failures)
                ),
                ephemeral=True,
            )
            return

        if req.get("trial"):
            pending = self.db.get_trial(interaction.user.id)
            if pending is None or int(pending["target_sequence"]) != target:
                self.db.set_trial(interaction.user.id, target, req["trial"])
                kind = {
                    "demigod": "Demigod Trial", "angel": "Angel's Acting Trial",
                    "acting": "Acting Trial",
                }[req["trial"]]
                await interaction.response.send_message(
                    embed=persona.fog_embed(
                        f"The {kind} Awaits",
                        f"Your resources are sufficient, but the path to "
                        f"**{pathways.sequence_name(row['pathway'], target)}** demands a "
                        f"{kind}. An Archangel of the Council must adjudicate your trial "
                        f"and pass you with `/angel trial pass <user>`. Survive it, or be "
                        f"consumed by corruption.",
                    )
                )
                return

        self.db.add_gold(interaction.user.id, -req["gold"])
        self.db.remove_item(interaction.user.id, formula, 1)
        self.db.remove_item(interaction.user.id, characteristic, 1)
        for rarity, count in req["ingredients"].items():
            inventory = self.db.get_inventory(interaction.user.id)
            remaining = count
            for k, qty in inventory.items():
                if remaining <= 0:
                    break
                if ingredients.rarity_of(k) == rarity:
                    take = min(qty, remaining)
                    self.db.remove_item(interaction.user.id, k, take)
                    remaining -= take

        self.db.clear_trial(interaction.user.id)
        self.db.set_sequence(interaction.user.id, row["pathway"], target)
        await sync_beyonder_role(self.db, interaction.user, row["pathway"], target)
        new_title = pathways.sequence_name(row["pathway"], target)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Ascension",
                f"**{interaction.user.display_name}** has drunk the potion and risen to "
                f"**{new_title}** (Sequence {target}) upon the Path of "
                f"**{pathways.get_pathway(row['pathway'])['name']}**. May the fog have mercy "
                f"on what you become.",
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProgressionCog(bot))

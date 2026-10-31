"""Beyonder progression: pathway fealty, status, advancement, profile visuals, and voice digestion."""
from __future__ import annotations

import random
import time
from datetime import datetime, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from settings import settings
from data import ingredients, pathways
from utils import checks, persona
from utils.roles import sync_beyonder_role
from utils.profile_card import render_profile_card
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

    async def cog_load(self) -> None:
        self.vc_digestion_loop.start()

    async def cog_unload(self) -> None:
        self.vc_digestion_loop.cancel()

    # --- chat digestion from activity ------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        user_id = message.author.id

        # Update last_active_ts on every message
        self.db.touch_active(user_id)

        user = self.db.ensure_user(user_id)
        if user["pathway"] is None or user["sequence"] is None:
            return

        min_len = int(settings.get("min_digest_message_len", config.MIN_DIGEST_MESSAGE_LEN))
        if len(message.content.strip()) < min_len:
            return

        today = datetime.now(timezone.utc).date().isoformat()
        days = int(user["active_days"]) + (1 if user["last_activity_date"] != today else 0)
        digestion = float(user["digestion"])
        last_ts = float(user["last_digest_ts"])

        if settings.get("features_digestion", True):
            seq = int(user["sequence"])
            base_cooldown = int(
                settings.get("activity_digest_cooldown", config.ACTIVITY_DIGEST_COOLDOWN)
            )
            # Scaled cooldown: x1.25 for Seq 4-3, x1.5 for Seq 2-1
            if seq in (3, 4):
                cooldown = int(base_cooldown * 1.25)
            elif seq in (1, 2):
                cooldown = int(base_cooldown * 1.5)
            else:
                cooldown = base_cooldown

            now = time.time()
            if now - last_ts >= cooldown:
                mult = pathways.DIGESTION_MULTIPLIERS.get(seq, 0.0)
                base = float(settings.get("digest_per_message", config.DIGEST_PER_MESSAGE))

                sanity = float(user["sanity"])
                corruption = float(user["corruption"])
                sanity_factor = max(0.25, sanity / 100.0)
                corruption_penalty = max(0.2, 1.0 - corruption / 120.0)

                gain = base * mult * sanity_factor * corruption_penalty
                digestion = min(100.0, float(user["digestion"]) + gain)
                last_ts = now

        self.db.activity_tick(user_id, digestion, last_ts, days, today)

    # --- voice channel digestion loop (60s tick) -------------------------
    @tasks.loop(seconds=60)
    async def vc_digestion_loop(self) -> None:
        """Every 60s, award digestion XP to active human members in voice channels."""
        if not settings.get("features_digestion", True):
            return

        for guild in self.bot.guilds:
            afk_channel = guild.afk_channel
            for vc in guild.voice_channels:
                if afk_channel and vc.id == afk_channel.id:
                    continue

                human_members = [m for m in vc.members if not m.bot]
                if not human_members:
                    continue

                for member in human_members:
                    voice = member.voice
                    # Must be active and not deafened
                    if not voice or voice.self_deaf or voice.deaf:
                        continue

                    # Record voice channel presence
                    self.db.add_vc_minutes(member.id, 1)

                    user = self.db.get_user(member.id)
                    if not user or user["pathway"] is None or user["sequence"] is None:
                        continue

                    seq = int(user["sequence"])
                    mult = pathways.DIGESTION_MULTIPLIERS.get(seq, 0.0)
                    if mult <= 0:
                        continue

                    sanity = float(user["sanity"])
                    corruption = float(user["corruption"])
                    sanity_factor = max(0.25, sanity / 100.0)
                    corruption_penalty = max(0.2, 1.0 - corruption / 120.0)

                    # Base rate calibrated so Seq 9 takes 72h (3 continuous days) of VC
                    base_rate = 100.0 / pathways.BASE_VC_MINUTES_SEQ9
                    rate = base_rate * mult
                    # +25% bonus if unmuted with others present
                    if not voice.self_mute and not voice.mute and len(human_members) > 1:
                        rate *= 1.25

                    gain = rate * sanity_factor * corruption_penalty
                    self.db.add_digestion(member.id, gain)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        """Refresh activity timestamp and re-sync role on voice activity."""
        if member.bot or not member.guild:
            return
        self.db.touch_active(member.id)
        user = self.db.get_user(member.id)
        if user and user.get("pathway") and user.get("sequence") is not None:
            await sync_beyonder_role(
                self.db, member, user["pathway"], int(user["sequence"]), guild=member.guild
            )

    # --- /pathway choose & list -------------------------------------------
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
        role, error_diag = await sync_beyonder_role(
            self.db, interaction.user, key, 9, guild=interaction.guild
        )
        seq9 = pathways.sequence_name(key, 9)
        data = pathways.get_pathway(key)

        embed = persona.success_embed(
            "Potion Consumed — Awakened as Beyonder",
            f"You have brewed and consumed the **{seq9}** potion, stepping out of ordinary mortality to awaken "
            f"your spirituality upon the Path of **{data['name']}**!\n\n"
            f"Your potion digestion begins now through voice presence and deeds. "
            f"Walk the ladder toward demigod authority and server power, and address yourself to the **{data['above']}**.",
        )
        if error_diag:
            embed.add_field(name="⚠️ Role Diagnostics", value=error_diag, inline=False)

        await interaction.response.send_message(embed=embed)

    @pathway.command(name="list")
    async def pathway_list(self, interaction: discord.Interaction) -> None:
        """List the 22 Pathways and their groups."""
        lines: list[str] = []
        for group, keys in pathways.GROUPS.items():
            names = ", ".join(pathways.get_pathway(k)["name"] for k in keys)
            lines.append(f"**{group}** — {names}")
        embed = persona.fog_embed("The 22 Pathways", "\n".join(lines))
        embed.add_field(
            name="Awaken as a Beyonder",
            value="Only members who seek power in this server brew their potion. Run `/pathway choose <name>` to step onto a Pathway.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    # --- /profile & /status -----------------------------------------------
    async def _render_and_send_profile(
        self, interaction: discord.Interaction, target: discord.Member
    ) -> None:
        row = self.db.ensure_user(target.id)
        if row["pathway"] is None:
            if target.id == interaction.user.id:
                await interaction.response.send_message(
                    embed=persona.fog_embed(
                        "Ordinary Mortal",
                        "You are an ordinary mortal who has not drunk a potion or stepped onto a Pathway.\n\n"
                        "In this realm, only members who seek supernatural power, divine rank, and server authority "
                        "brew and drink their initial Sequence 9 potion (`/pathway choose <pathway>`) to awaken as a Beyonder. "
                        "Mortals cannot view a Beyonder profile.",
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=persona.fog_embed(
                        f"{target.display_name} — Mortal",
                        f"**{target.display_name}** has not drunk a potion or stepped onto a Pathway. They remain an ordinary mortal.",
                    ),
                    ephemeral=True,
                )
            return

        # Fetch avatar bytes
        avatar_bytes = None
        if target.display_avatar:
            try:
                avatar_bytes = await target.display_avatar.read()
            except Exception:
                pass

        tarot_alias = self.db.get_tarot_alias(target.id)
        tarot_card = tarot_alias.get("card") if tarot_alias else None

        angel_row = self.db.get_angel_title(target.id)
        angel_title = angel_row["title"] if angel_row else None

        # Re-sync role and capture diagnostics
        role, error_diag = await sync_beyonder_role(
            self.db, target, row["pathway"], int(row["sequence"]), guild=interaction.guild
        )

        # Generate Pillow card if Pillow is installed
        card_buf = render_profile_card(
            row, target.display_name, avatar_bytes, tarot_card, angel_title=angel_title
        )
        file = discord.File(fp=card_buf, filename="profile.png") if card_buf else None

        seq = int(row["sequence"])
        est_time = pathways.estimated_ascension_time(seq, float(row["digestion"]))

        angel_header = f"🪽 **Divine Authority:** Archangel · {angel_title}\n" if angel_title else ""
        embed = persona.fog_embed(
            f"{target.display_name} — Dossier",
            f"{angel_header}"
            f"**Pathway:** {pathways.get_pathway(row['pathway'])['name']}  ·  "
            f"**Sequence:** {seq} ({pathways.sequence_name(row['pathway'], seq)})\n"
            f"**Next Ascension Est. Time:** {est_time}",
        )
        if file:
            embed.set_image(url="attachment://profile.png")
        else:
            # Fallback text slate when Pillow image is not generated
            digestion = float(row.get("digestion", 0.0))
            sanity = float(row.get("sanity", 100.0))
            corruption = float(row.get("corruption", 0.0))
            gold = int(row.get("gold", 0))
            tarot = int(row.get("tarot_coins", 0))
            angel_field_line = f"• **Divine Title:** 🪽 Archangel · {angel_title}\n" if angel_title else ""
            embed.add_field(
                name="📊 Status Slate",
                value=(
                    f"{angel_field_line}"
                    f"• **Digestion:** {digestion:.1f}%\n"
                    f"• **Sanity:** {sanity:.0f}% | **Corruption:** {corruption:.0f}%\n"
                    f"• **Wealth:** 🪙 {gold:,} Gold | 🎴 {tarot} Tarot Coins"
                ),
                inline=False,
            )

        embed.add_field(
            name="⏳ Ascension Timeline",
            value=f"**{est_time}** *(includes buffer for irregular logins and breaks)*",
            inline=False,
        )
        if error_diag:
            embed.add_field(name="⚠️ Role Diagnostics", value=error_diag, inline=False)

        if file:
            await interaction.response.send_message(embed=embed, file=file)
        else:
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="profile")
    @app_commands.describe(user="Whose profile card to inspect (defaults to you).")
    async def profile(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        """Inspect your visual Beyonder profile card slate."""
        target = user or interaction.user
        await self._render_and_send_profile(interaction, target)

    @app_commands.command(name="status")
    @app_commands.describe(user="Whose status to inspect (defaults to you).")
    async def status(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        """Inspect Sequence, Digestion, Sanity, Corruption, and wealth visual slate."""
        target = user or interaction.user
        await self._render_and_send_profile(interaction, target)

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
        mult = pathways.DIGESTION_MULTIPLIERS.get(seq, 0.0)

        embed = persona.fog_embed(
            f"Digestion — {title}",
            f"**Current digestion:** {float(row['digestion']):.1f}% / 100%\n"
            f"**Digestion Multiplier:** {mult:.3f}x\n"
            f"**Next Sequence:** {next_title}",
        )
        embed.add_field(
            name="Acting Method",
            value=(
                f"Embody the essence of the **{title}**. Speak as one, act as one, and "
                f"the potion's madness shall become your power.\n\n"
                f"• **Voice Channel Presence:** Grants active digestion XP every 60s (+25% unmuted bonus).\n"
                f"• **Text Chat Activity:** Messages with ≥15 chars grant digestion periodically."
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    # --- /advance ---------------------------------------------------------
    @app_commands.command(name="advance")
    @checks.beyonder_only
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
                    "may initiate the Apotheosis — use `/apotheosis initiate`.",
                ),
                ephemeral=True,
            )
            return

        failures: list[str] = []
        if float(row["digestion"]) < 100.0:
            failures.append(f"digestion at {float(row['digestion']):.1f}% (need 100%)")
        if int(row["gold"]) < req["gold"]:
            failures.append(f"{req['gold']:,} Gold Pounds (you hold {int(row['gold']):,})")
        if int(row.get("tarot_coins", 0)) < req.get("tarot", 0):
            failures.append(f"{req['tarot']} Tarot Coins (you hold {int(row.get('tarot_coins', 0))})")
        if int(row["active_days"]) < req["min_active_days"]:
            failures.append(
                f"{req['min_active_days']} days of sustained presence "
                f"(you have {int(row['active_days'])})"
            )
        if float(row["sanity"]) < req.get("min_sanity", 0.0):
            failures.append(f"Sanity ≥ {req['min_sanity']:.0f}% (current: {float(row['sanity']):.1f}%)")
        if float(row["corruption"]) > req.get("max_corruption", 100.0):
            failures.append(f"Corruption ≤ {req['max_corruption']:.0f}% (current: {float(row['corruption']):.1f}%)")

        formula = ingredients.formula_key(row["pathway"], target)
        char_seq = req.get("char_sequence", target)
        char_count = req.get("characteristics", 1)
        characteristic = ingredients.characteristic_key(row["pathway"], char_seq)

        if self.db.count_item(interaction.user.id, formula) < 1:
            failures.append(f"the **{pathways.sequence_name(row['pathway'], target)}** formula")

        held_char = self.db.count_item(interaction.user.id, characteristic)
        if held_char < char_count:
            failures.append(
                f"{char_count}× **{pathways.sequence_name(row['pathway'], char_seq)}** characteristic "
                f"(you hold {held_char})"
            )

        for rarity, count in req["ingredients"].items():
            held = sum(
                qty for k, qty in self.db.get_inventory(interaction.user.id).items()
                if ingredients.rarity_of(k) == rarity
            )
            if held < count:
                failures.append(f"{count}× {rarity} ingredients (you hold {held})")

        if req.get("slot_capped"):
            cap = req.get("max_slots", 3)
            current_holders = self.db.count_at_sequence(row["pathway"], target)
            if current_holders >= cap:
                failures.append(
                    f"a vacant slot (all {cap} slots for Sequence {target} upon this Pathway are filled)"
                )

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
                    "demigod": "Demigod Trial",
                    "angel": "Angel's Acting Trial",
                    "acting": "Acting Trial",
                }.get(req["trial"], "Ascension Trial")
                await interaction.response.send_message(
                    embed=persona.fog_embed(
                        f"The {kind} Awaits",
                        f"Your resources are sufficient, but the path to "
                        f"**{pathways.sequence_name(row['pathway'], target)}** demands a "
                        f"{kind}. An Archangel of the Council must adjudicate your trial "
                        f"and pass you with `/angel trial <user>`. Survive it, or be "
                        f"consumed by corruption.",
                    )
                )
                return

        # Ritual Backlash Calculation
        if settings.get("advancement_hazard_enabled", True):
            base_hazard = float(req.get("hazard_percent", 0.0))
            sanity = float(row["sanity"])
            corruption = float(row["corruption"])
            # Risk reduced by high Sanity, increased by Corruption
            effective_hazard = base_hazard * (1.0 + (corruption / 100.0) - (sanity / 100.0))
            effective_hazard = max(1.0, min(95.0, effective_hazard))

            if random.uniform(0, 100) < effective_hazard:
                # Backlash triggered!
                # Consume Gold, Tarot, Formula, and Ingredients (keep main Characteristic)
                self.db.add_gold(interaction.user.id, -req["gold"])
                if req.get("tarot", 0) > 0:
                    self.db.add_tarot(interaction.user.id, -req["tarot"])
                self.db.remove_item(interaction.user.id, formula, 1)

                for rarity, count in req["ingredients"].items():
                    inv = self.db.get_inventory(interaction.user.id)
                    remaining = count
                    for k, qty in inv.items():
                        if remaining <= 0:
                            break
                        if ingredients.rarity_of(k) == rarity:
                            take = min(qty, remaining)
                            self.db.remove_item(interaction.user.id, k, take)
                            remaining -= take

                # Penalties:
                # Reduce Digestion by 15%-50%
                digest_loss = random.uniform(15.0, 50.0)
                new_digest = self.db.add_digestion(interaction.user.id, -digest_loss)
                # Reduce Sanity by 15%
                new_sanity = self.db.add_sanity(interaction.user.id, -15.0)
                # Add 10%-45% Corruption
                corr_add = random.uniform(10.0, 45.0)
                new_corr = self.db.add_corruption(interaction.user.id, corr_add)

                await interaction.response.send_message(
                    embed=persona.error_embed(
                        f"**RITUAL BACKLASH!** The potion has revolted within your soul!\n\n"
                        f"The ritual failed with an effective hazard of **{effective_hazard:.1f}%**.\n"
                        f"• Consumed: {req['gold']:,} Gold, {req.get('tarot', 0)} Tarot Coins, formula, and ingredients.\n"
                        f"• Retained: Your Beyonder Characteristic was salvaged.\n"
                        f"• Digestion: -{digest_loss:.1f}% (now {new_digest:.1f}%)\n"
                        f"• Sanity: -15.0% (now {new_sanity:.1f}%)\n"
                        f"• Corruption: +{corr_add:.1f}% (now {new_corr:.1f}%)"
                    )
                )
                return

        # Successful advancement: Consume all resources
        self.db.add_gold(interaction.user.id, -req["gold"])
        if req.get("tarot", 0) > 0:
            self.db.add_tarot(interaction.user.id, -req["tarot"])
        self.db.remove_item(interaction.user.id, formula, 1)
        self.db.remove_item(interaction.user.id, characteristic, char_count)

        for rarity, count in req["ingredients"].items():
            inv = self.db.get_inventory(interaction.user.id)
            remaining = count
            for k, qty in inv.items():
                if remaining <= 0:
                    break
                if ingredients.rarity_of(k) == rarity:
                    take = min(qty, remaining)
                    self.db.remove_item(interaction.user.id, k, take)
                    remaining -= take

        self.db.clear_trial(interaction.user.id)
        self.db.set_sequence(interaction.user.id, row["pathway"], target)
        role, error_diag = await sync_beyonder_role(
            self.db, interaction.user, row["pathway"], target, guild=interaction.guild
        )

        new_title = pathways.sequence_name(row["pathway"], target)
        embed = persona.success_embed(
            "Ascension",
            f"**{interaction.user.display_name}** has drunk the potion and ascended to "
            f"**{new_title}** (Sequence {target}) upon the Path of "
            f"**{pathways.get_pathway(row['pathway'])['name']}**. May the gray fog guide what you become.",
        )
        if error_diag:
            embed.add_field(name="⚠️ Role Diagnostics", value=error_diag, inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProgressionCog(bot))

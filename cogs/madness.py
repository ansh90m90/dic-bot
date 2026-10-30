"""The Corruption & Loss of Control (Madness) engine.

Background tick:
* Sealed Artifacts drip corruption / drain sanity while equipped.
* Beyonders whose corruption crosses the threshold suffer a Mental Breakdown
  (Zalgo nickname + banishment to the Fog of History).
* Broken Beyonders recover once the fog releases them.

Message listener:
* The message-devouring curse of certain artifacts deletes a fraction of messages.
* Broken Beyonders' messages are consumed and re-uttered as gibberish.
"""
from __future__ import annotations

import datetime
import random
import time

import discord
from discord.ext import commands, tasks

import config
from settings import settings
from data.artifacts import get_artifact
from utils import persona, zalgo
from db.database import Database

TICK_SECONDS = 600  # 10 minutes (daily drain fractions scale with this)


class MadnessCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    async def cog_load(self) -> None:
        self.madness_loop.start()

    async def cog_unload(self) -> None:
        self.madness_loop.cancel()

    # --- message filter ---------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        user = self.db.get_user(message.author.id)
        if user is None:
            return

        # Gibberish filter during a Mental Breakdown.
        if int(user["corrupted_state"]) == 1:
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                return
            gibberish = zalgo.gibberish(message.content)
            try:
                await message.channel.send(
                    f"*{message.author.display_name}* mutters: {gibberish}"
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            return

        # Artifact curse: devour a fraction of messages (only fetch when equipped).
        art_id = user.get("equipped_artifact")
        if art_id:
            equipped = self.db.get_artifact(art_id)
            if equipped and equipped["definition_key"]:
                art = get_artifact(equipped["definition_key"])
                ratio = (art or {}).get("modifiers", {}).get("message_delete_ratio", 0)
                if ratio and random.random() < ratio:
                    try:
                        await message.delete()
                    except (discord.Forbidden, discord.NotFound):
                        pass

    # --- periodic tick ----------------------------------------------------
    @tasks.loop(seconds=TICK_SECONDS)
    async def madness_loop(self) -> None:
        if not settings.get("features_madness", True):
            return
        self._apply_artifact_effects()
        await self._check_breakdowns()
        await self._check_recoveries()

    def _apply_artifact_effects(self) -> None:
        fraction = TICK_SECONDS / 86400.0
        for art in self.db.equipped_artifacts_all():
            mods = {}
            if art["definition_key"]:
                definition = get_artifact(art["definition_key"])
                mods = (definition or {}).get("modifiers", {})
            else:
                # Custom (owner-forged) artifacts drain sanity by grade.
                grade = int(art["grade"])
                mods = {"sanity_drain_per_day": {0: 8.0, 1: 5.0, 2: 3.0, 3: 1.0}.get(grade, 1.0)}
            owner = int(art["owner_id"])
            if mods.get("corruption_per_day"):
                self.db.add_corruption(owner, mods["corruption_per_day"] * fraction)
            if mods.get("sanity_drain_per_day"):
                self.db.add_sanity(owner, -mods["sanity_drain_per_day"] * fraction)

    async def _check_breakdowns(self) -> None:
        for user in self.db.users_above_corruption(
            float(settings.get("corruption_breakdown_threshold", config.CORRUPTION_BREAKDOWN_THRESHOLD))
        ):
            if int(user["corrupted_state"]) == 1:
                continue
            self.db.set_corrupted(int(user["user_id"]), 1, user.get("nickname_original"))
            self.db.set_fog_until(
                int(user["user_id"]),
                time.time() + float(settings.get("fog_timeout_minutes", config.FOG_TIMEOUT_MINUTES)) * 60,
            )
            await self._distort_and_banish(int(user["user_id"]))

    async def _check_recoveries(self) -> None:
        for user in self.db.corrupted_users():
            user_id = int(user["user_id"])
            if time.time() < float(user["fog_until"]):
                continue
            # The fog releases them; corruption recedes, but never to zero.
            self.db.clear_corrupted(user_id)
            self.db.clear_fog(user_id)
            self.db.set_corruption(
                user_id,
                max(0.0, float(settings.get("corruption_breakdown_threshold", config.CORRUPTION_BREAKDOWN_THRESHOLD)) - 20.0),
            )
            await self._restore_member(user_id)

    async def _distort_and_banish(self, user_id: int) -> None:
        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member is None:
                continue
            try:
                await member.edit(nick=zalgo.zalgo(member.display_name, intensity=2))
            except (discord.Forbidden, discord.HTTPException):
                pass
            until = discord.utils.utcnow() + datetime.timedelta(
                minutes=float(settings.get("fog_timeout_minutes", config.FOG_TIMEOUT_MINUTES))
            )
            try:
                await member.timeout(until, reason="Mental Breakdown — Fog of History")
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def _restore_member(self, user_id: int) -> None:
        original = None
        user = self.db.get_user(user_id)
        if user:
            original = user.get("nickname_original")
        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member is None:
                continue
            try:
                await member.edit(nick=original)
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MadnessCog(bot))

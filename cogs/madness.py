"""The Corruption, Inactivity Decay, and Loss of Control (Madness) engine."""
from __future__ import annotations

import datetime
import time

import discord
from discord.ext import commands, tasks

import config
from settings import settings
from data import pathways
from utils import persona, zalgo
from utils.roles import resolve_member, sync_beyonder_role
from db.database import Database

TICK_SECONDS = 600  # 10 minutes
DAY_SECONDS = 86400  # 24 hours


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

        # Gibberish filter during a Mental Breakdown
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

    # --- periodic tick ----------------------------------------------------
    @tasks.loop(seconds=TICK_SECONDS)
    async def madness_loop(self) -> None:
        if not settings.get("features_madness", True):
            return
        await self._apply_inactivity_decay()
        await self._check_breakdowns()
        await self._check_recoveries()

    async def _apply_inactivity_decay(self) -> None:
        """Apply daily inactivity decay (>30 days) and regression (>365 days)."""
        now = time.time()
        beyonders = self.db.all_beyonders()

        for user in beyonders:
            uid = int(user["user_id"])
            last_active = float(user.get("last_active_ts") or 0.0)
            if last_active <= 0:
                continue

            idle_seconds = now - last_active
            last_check = float(user.get("last_decay_check_ts") or 0.0)

            # Daily decay trigger
            if idle_seconds >= 30 * DAY_SECONDS:
                if now - last_check >= DAY_SECONDS:
                    # Daily penalty: +5.0% Corruption, -5.0% Digestion, -2.0% Sanity
                    self.db.add_corruption(uid, 5.0)
                    self.db.add_digestion(uid, -5.0)
                    self.db.add_sanity(uid, -2.0)
                    self.db.update_decay_check(uid, now)

            # Year-long inactivity: Sequence demotion
            if idle_seconds >= 365 * DAY_SECONDS:
                last_demotion = float(user.get("last_demotion_ts") or 0.0)
                # Ensure demotion only happens at most once per 365 days of idle time
                if now - last_demotion >= 365 * DAY_SECONDS:
                    result = self.db.demote_user_sequence(uid)
                    if result:
                        old_seq, new_seq = result
                        pathway = user["pathway"]
                        new_title = pathways.sequence_name(pathway, new_seq)

                        # Role sync
                        for guild in self.bot.guilds:
                            member = await resolve_member(guild, uid)
                            if member:
                                await sync_beyonder_role(
                                    self.db, member, pathway, new_seq, guild=guild
                                )
                                # Broadcast omen message to default announcement/system channel
                                channel = guild.system_channel
                                if channel is None:
                                    channel = discord.utils.get(
                                        guild.text_channels, name="general"
                                    ) or discord.utils.get(guild.text_channels, name="announcements")
                                if channel and channel.permissions_for(guild.me).send_messages:
                                    try:
                                        omen_embed = persona.error_embed(
                                            f"**AN OMEN FROM THE GRAY FOG**\n\n"
                                            f"The prolonged slumber of **{member.display_name}** has frayed their soul.\n"
                                            f"Their spirituality collapsed into the void after exceeding 365 days of absence. "
                                            f"They have fallen from Sequence {old_seq} and regressed to "
                                            f"**Sequence {new_seq} ({new_title})** upon the Path of "
                                            f"**{pathways.get_pathway(pathway)['name']}**."
                                        )
                                        await channel.send(embed=omen_embed)
                                    except (discord.Forbidden, discord.HTTPException):
                                        pass

    async def _check_breakdowns(self) -> None:
        threshold = float(
            settings.get("corruption_breakdown_threshold", config.CORRUPTION_BREAKDOWN_THRESHOLD)
        )
        for user in self.db.users_above_corruption(threshold):
            if int(user["corrupted_state"]) == 1:
                continue
            self.db.set_corrupted(int(user["user_id"]), 1, user.get("nickname_original"))
            self.db.set_fog_until(
                int(user["user_id"]),
                time.time() + float(settings.get("fog_timeout_minutes", config.FOG_TIMEOUT_MINUTES)) * 60,
            )
            await self._distort_and_banish(int(user["user_id"]))

    async def _check_recoveries(self) -> None:
        threshold = float(
            settings.get("corruption_breakdown_threshold", config.CORRUPTION_BREAKDOWN_THRESHOLD)
        )
        for user in self.db.corrupted_users():
            user_id = int(user["user_id"])
            if time.time() < float(user["fog_until"]):
                continue
            self.db.clear_corrupted(user_id)
            self.db.clear_fog(user_id)
            self.db.set_corruption(user_id, max(0.0, threshold - 20.0))
            await self._restore_member(user_id)

    async def _distort_and_banish(self, user_id: int) -> None:
        for guild in self.bot.guilds:
            member = await resolve_member(guild, user_id)
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
            member = await resolve_member(guild, user_id)
            if member is None:
                continue
            try:
                await member.edit(nick=original)
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MadnessCog(bot))

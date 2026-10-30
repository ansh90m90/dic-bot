"""Spirit World Anomalies — random encounters, `/pray`, and `/enter`."""
from __future__ import annotations

import datetime
import random
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from settings import settings
from data import ingredients
from utils import persona, zalgo
from db.database import Database

EVENT_TYPES: dict[str, dict] = {
    "ravings": {
        "name": "The Ravings of the True Creator",
        "kind": "pray",
        "announce": (
            "The ravings of the True Creator echo through the channel. "
            "The first **3** to type `/pray The Fool` resist the corruption. "
            "All others gain +10 Madness."
        ),
    },
    "door": {
        "name": "A Door in the Spirit World",
        "kind": "enter",
        "announce": (
            "A mystical door appears before you. Typing `/enter` yields either a rare "
            "potion ingredient or a temporary banishment — Lost in the Spirit World."
        ),
    },
    "fog_tide": {
        "name": "A Tide of Gray Fog",
        "kind": "pray",
        "announce": (
            "A tide of gray fog rises from below. The first **3** to `/pray The Fool` "
            "find shelter; the rest are touched by the mist (+5 Madness)."
        ),
    },
}


async def trigger_anomaly(bot: commands.Bot, channel: discord.TextChannel,
                          event_type: str) -> bool:
    """Announce and register an anomaly in ``channel``. Returns success."""
    if event_type not in EVENT_TYPES:
        return False
    info = EVENT_TYPES[event_type]
    db: Database = bot.db  # type: ignore[attr-defined]
    ends_at = time.time() + float(settings.get("anomaly_window", config.ANOMALY_WINDOW))
    db.set_anomaly(channel.id, event_type, ends_at, {"rewarded": [], "kind": info["kind"]})
    embed = persona.fog_embed(info["name"], info["announce"], color=persona.DANGER_COLOR)
    try:
        await channel.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        db.clear_anomaly(channel.id)
        return False


class AnomaliesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.next_anomaly: float = time.time() + random.randint(
            int(settings.get("anomaly_min_interval", config.ANOMALY_MIN_INTERVAL)),
            int(settings.get("anomaly_max_interval", config.ANOMALY_MAX_INTERVAL)),
        )

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    async def cog_load(self) -> None:
        self.anomaly_loop.start()

    async def cog_unload(self) -> None:
        self.anomaly_loop.cancel()

    @tasks.loop(seconds=60)
    async def anomaly_loop(self) -> None:
        if not settings.get("features_anomalies", True):
            return
        if time.time() < self.next_anomaly:
            return
        self.next_anomaly = time.time() + random.randint(
            int(settings.get("anomaly_min_interval", config.ANOMALY_MIN_INTERVAL)),
            int(settings.get("anomaly_max_interval", config.ANOMALY_MAX_INTERVAL)),
        )
        channel = self._pick_channel()
        if channel is None:
            return
        event_type = random.choice(list(EVENT_TYPES.keys()))
        await trigger_anomaly(self.bot, channel, event_type)

    def _pick_channel(self) -> discord.TextChannel | None:
        candidates: list[discord.TextChannel] = []
        for guild in self.bot.guilds:
            for ch in guild.text_channels:
                perms = ch.permissions_for(guild.me)
                if perms.send_messages and perms.view_channel:
                    candidates.append(ch)
        if not candidates:
            return None
        return random.choice(candidates)

    # --- /pray ------------------------------------------------------------
    @app_commands.command(name="pray")
    @app_commands.describe(target="The being you beseech (e.g. 'The Fool').")
    async def pray(self, interaction: discord.Interaction, target: str) -> None:
        """Beseech a being of the gray fog during a Spirit World Anomaly."""
        channel = interaction.channel
        anomaly = self.db.get_anomaly(channel.id) if channel else None
        if anomaly is None or anomaly["data"].get("kind") != "pray":
            await interaction.response.send_message(
                embed=persona.fog_embed(
                    "A Whisper in the Fog",
                    f"You offer your prayer to **{target}**, but the gray fog is still. "
                    f"No anomaly stirs here now.",
                ),
                ephemeral=True,
            )
            return

        data = anomaly["data"]
        rewarded: list[int] = data.get("rewarded", [])
        if interaction.user.id in rewarded:
            await interaction.response.send_message(
                embed=persona.fog_embed(
                    "Already Answered",
                    "The fog has already heard your prayer, Mortal. Do not test it twice.",
                ),
                ephemeral=True,
            )
            return

        if len(rewarded) < 3:
            rewarded.append(interaction.user.id)
            data["rewarded"] = rewarded
            self.db.set_anomaly(channel.id, anomaly["event_type"], anomaly["ends_at"], data)
            self.db.add_tarot(interaction.user.id, 1)
            await interaction.response.send_message(
                embed=persona.success_embed(
                    "The Fool Answers",
                    "**The Fool** inclines his head. You resist the corruption and are "
                    "granted a Tarot Coin for your faith.",
                )
            )
        else:
            new_c = self.db.add_corruption(interaction.user.id, 10)
            await interaction.response.send_message(
                embed=persona.error_embed(
                    f"The fog does not hear you. The ravings creep in — **+10 Madness** "
                    f"(corruption {new_c:.1f}%)."
                )
            )

    # --- /enter -----------------------------------------------------------
    @app_commands.command(name="enter")
    async def enter(self, interaction: discord.Interaction) -> None:
        """Step through a mystical door during a Spirit World Anomaly."""
        channel = interaction.channel
        anomaly = self.db.get_anomaly(channel.id) if channel else None
        if anomaly is None or anomaly["data"].get("kind") != "enter":
            await interaction.response.send_message(
                embed=persona.fog_embed(
                    "No Door Awaits",
                    "You reach for a door, but there is only the gray fog. No anomaly "
                    "stirs here now.",
                ),
                ephemeral=True,
            )
            return

        if random.random() < 0.5:
            ing = ingredients.roll_ingredient()
            self.db.add_item(interaction.user.id, ing, 1)
            await interaction.response.send_message(
                embed=persona.success_embed(
                    "The Door Opens",
                    f"Beyond the door you grasp a **{ing}** — a rare potion ingredient, "
                    f"claimed from the Spirit World.",
                )
            )
        else:
            # Lost in the Spirit World: temporary mute.
            await self._lost_in_fog(interaction)
            await interaction.response.send_message(
                embed=persona.error_embed(
                    f"**{interaction.user.display_name}** steps through and is **Lost in "
                    f"the Spirit World** — silenced for a short while until the fog "
                    f"releases them."
                )
            )

    async def _lost_in_fog(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            return
        until = discord.utils.utcnow() + datetime.timedelta(minutes=2)
        try:
            await member.timeout(until, reason="Lost in the Spirit World")
        except (discord.Forbidden, discord.HTTPException):
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AnomaliesCog(bot))

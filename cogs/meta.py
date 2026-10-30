"""Meta commands: live `/settings` and comprehensive custom `/help`."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from settings import SCHEMA, settings
from utils import checks, persona

_HELP_SUBTOPICS = {
    "mechanics": {
        "title": "Core Mechanics & Spirit World Lore",
        "description": (
            "**The 22 Pathways & Acting Method:**\n"
            "Mortals begin at Sequence 9 by swearing fealty to a pathway (`/pathway choose <name>`). "
            "To ascend to higher ranks, Beyonders must digest their potions using the **Acting Method**—"
            "aligning their behavior and deeds with the core principle of their sequence title.\n\n"
            "**Sanity (0%–100%):**\n"
            "• Mental stability protects your soul against ritual backlash and maximizes digestion gains.\n"
            "• Drops from failed advancement rituals, catastrophic divinations, and long inactivity.\n"
            "• Restored gradually through natural recovery or divine cleansing (`/angel cleanse`).\n\n"
            "**Corruption (0%–100%):**\n"
            "• Eldritch taint from Spirit World anomalies, failed rituals, and excessive slumber.\n"
            "• High corruption severely penalizes digestion speed and raises ritual backlash hazards.\n"
            "• **Mental Breakdown (≥80% Corruption):** Triggers unholy Zalgo name distortion, gibberish outbursts in chat, "
            "and a timeout in the Spirit World fog."
        ),
    },
    "progression": {
        "title": "Advancement Ladder & Ritual Backlash",
        "description": (
            "**Advancement Requirements Table:**\n"
            "Advancing requires 100% Digestion, target Potion Formula, Beyonder Characteristic(s), "
            "multi-rarity ingredients, active days, minimum Sanity, maximum Corruption, and Gold/Tarot currency:\n"
            "• **Seq 8:** 150 Gold, 1× Char, 2 Common + 1 Uncommon, 2 active days, Sanity ≥60%, Corr ≤50%, 5% hazard.\n"
            "• **Seq 7:** 400 Gold, 1 Tarot, 1× Char, 3 Common + 2 Uncommon, 5 active days, Sanity ≥65%, Corr ≤45%, 10% hazard.\n"
            "• **Seq 6:** 1,000 Gold, 2 Tarot, 1× Char, 4 Common + 3 Uncommon + 1 Rare, 10 active days, Sanity ≥70%, Corr ≤40%, 15% hazard.\n"
            "• **Seq 5:** 2,500 Gold, 4 Tarot, 1× Char, 5 Com + 4 Uncom + 2 Rare, 18 days, Sanity ≥75%, Corr ≤35%, Acting Trial, 20% hazard.\n"
            "• **Seq 4 (Demigod):** 7,500 Gold, 8 Tarot, 1× Char, 5 Com + 5 Uncom + 3 Rare + 1 Legendary, 35 days, Sanity ≥80%, Corr ≤25%, Demigod Trial, 25% hazard.\n"
            "• **Seq 3:** 20,000 Gold, 15 Tarot, 1× Char, 6 Uncom + 4 Rare + 2 Leg, 60 days, Sanity ≥85%, Corr ≤20%, Demigod Trial, 30% hazard.\n"
            "• **Seq 2 (Angel):** 55,000 Gold, 30 Tarot, 2× Seq 2 Char, 6 Rare + 4 Leg, 100 days, Sanity ≥88%, Corr ≤15%, Angel Trial, max 6 Angels/Pathway, 35% hazard.\n"
            "• **Seq 1 (King of Angels):** 150,000 Gold, 60 Tarot, 3× Seq 1 Char, 8 Rare + 6 Leg, 180 days, Sanity ≥92%, Corr ≤10%, Acting Trial, max 3 Kings/Pathway, 40% hazard.\n"
            "• **Seq 0 (True God):** 100% Seq 1 Digest, Sanity ≥90%, Corr ≤10%, 25 Tarot Coins, Pathway Uniqueness, 3× Seq 1 Char, Apotheosis ritual.\n\n"
            "**Ritual Backlash Hazard:**\n"
            "If `advancement_hazard_enabled` is active, advancing carries risk (5% to 40%). High Sanity reduces risk; high Corruption amplifies it.\n"
            "• **On Backlash Failure:** Gold, Tarot Coins, Formula, and ingredients are consumed. Main Characteristic is preserved. "
            "Digestion drops by 15%–50%, Sanity drops by 15%, and Corruption increases by 10%–45%!"
        ),
    },
    "voice": {
        "title": "Voice Channel (VC) Digestion Dominance",
        "description": (
            "**The Dominant Potion Digestion Engine:**\n"
            "Active presence in voice channels yields the most potion digestion XP in the entire bot:\n\n"
            "• **Continuous 60-Second Loop:** Evaluated every minute for active, non-deafened human members in non-AFK voice channels.\n"
            "• **Base Rate Calibrated:** Sequence 9 requires 72 hours (4,320 minutes) of continuous voice presence to digest 100%.\n"
            "• **+25% Unmuted Group Presence Bonus:** Speaking or remaining unmuted in a channel with at least one other member boosts "
            "digestion XP by +25%.\n"
            "• **Chat Digestion Comparison:** Sending substantive messages (≥15 characters) grants small digestion ticks, "
            "but is heavily throttled by cooldowns (180s base, 225s for Seq 4–3, 270s for Seq 2–1). Voice presence yields continuous progression.\n"
            "• **Estimated Time Buffer:** `/profile` calculates remaining time with a 1.30× (30%) real-world buffer "
            "to account for pauses, muting, and irregular logins."
        ),
    },
    "economy": {
        "title": "Economy: Gold, Tarot Coins & Wealth Generation",
        "description": (
            "**Currencies:**\n"
            "• **Gold Pounds:** The mortal currency used to buy common ingredients, formulas, and characteristics.\n"
            "• **Tarot Coins:** Secret mystical tokens used for high-sequence advancement and sacred ceremonies.\n\n"
            "**Ways to Earn Currency:**\n"
            "• `/daily` — Claim your daily stipend of Gold and Tarot Coins.\n"
            "• `/divine <inquiry>` — Perform pendulum divination. Auspicious Major Arcana (The Sun, Wheel of Fortune, The Star) "
            "award 50–200 Gold and Tarot Coins! Cursed cards test sanity.\n"
            "• `/bounty list` & `/bounty hunt <target>` — Undertake hazardous Tavern contracts on rogue Beyonders and monsters "
            "(Wraith, Marionette, Rampager) for 150–2,500 Gold and Tarot Coins.\n"
            "• `/sacrifice <item> [qty]` — Offer harvested monster ingredients to the Gray Fog Altar to transmute them into Gold & Coins.\n"
            "• `/angel grant <user> <currency> <amount>` — Administrators can generate and gift unlimited Gold or Tarot Coins.\n\n"
            "**The Mystical Market:**\n"
            "• `/shop list` & `/shop buy <item>` — Purchase ingredients (Common 50, Uncommon 200, Rare 800, Legendary 3000) "
            "and Sequence formulas.\n"
            "• `/shop buy characteristic` — Purchase raw pathway characteristics."
        ),
    },
    "tarot": {
        "title": "The Secret Tarot Club Gathering",
        "description": (
            "**The Sacred Domain Above the Gray Fog:**\n"
            "A clandestine assembly where Beyonders convene under the cover of Major Arcana aliases:\n\n"
            "• `/tarot open [channel_name]` — Opens the sanctum. If the channel does not exist, the bot **automatically creates it** "
            "as a private chamber hidden from `@everyone` and grants read/write permissions to the Tarot Club role.\n"
            "• `/tarot join` — Swear the oath, take your designated Major Arcana seat (e.g., Justice, The Hanged Man, The Sun), "
            "and receive the exclusive Tarot role.\n"
            "• `/tarot speak <message>` — Transmit messages into the Tarot chamber via disguised webhooks under your Major Arcana avatar, "
            "keeping your true identity hidden.\n"
            "• `/tarot leave` & `/tarot close` — Conclude the gathering and revoke Tarot access roles."
        ),
    },
    "trials": {
        "title": "Demigod, Angel & Apotheosis Trials",
        "description": (
            "**Beyond Mortal Bounds (Sequence 5–0):**\n"
            "Higher ascensions require passing perilous trials and overcoming pathway scarcity:\n\n"
            "• **Acting & Demigod Trials (Seq 5, 4, 3):** Beyonders must complete formal acting trials recorded on their dossier.\n"
            "• **Angel Trials (Seq 2, 1):** Require Archangel review and adjudication (`/angel trial approve/reject`).\n"
            "• **Pathway Population Caps:**\n"
            "  - Sequence 2 (Angel): Maximum 6 Angels per Pathway.\n"
            "  - Sequence 1 (King of Angels): Maximum 3 Kings per Pathway.\n"
            "  - Sequence 0 (True God): Strictly ONE True God per Pathway.\n"
            "• **Apotheosis Ritual (`/angel apotheosis`):** Requires 100% Seq 1 digestion, Sanity ≥90%, Corruption ≤10%, "
            "25 Tarot Coins, Pathway Uniqueness, and 3× Seq 1 Characteristics consumed simultaneously."
        ),
    },
    "inactivity": {
        "title": "Inactivity Decay & Sequence Regression",
        "description": (
            "**Prolonged Slumber Penalties:**\n"
            "Beyonders who vanish from the realm suffer gradual loss of spirituality:\n\n"
            "• **> 30 Days Inactive:** Suffers daily degradation of **+5.0% Corruption**, **-5.0% Digestion** (clamped at 0%), "
            "and **-2.0% Sanity**.\n"
            "• **> 365 Days Inactive:** Suffers **Sequence Regression**! The Beyonder drops by 1 Sequence (Seq + 1, max 9), "
            "resets digestion to 0%, forfeits their Godhood slot if Sequence 0, cancels pending trials, and has their Discord roles demoted. "
            "An omen announcement is broadcast to the server's default announcement channel warning the realm of their fall.\n\n"
            "**Preserving Your Soul:**\n"
            "Sending any message, joining a voice channel, or executing any command refreshes your `last_active_ts` timestamp."
        ),
    },
    "roles": {
        "title": "Discord Hierarchy, Hoisting & Diagnostics",
        "description": (
            "**Role Synchronization Standard:**\n"
            "• **Naming Standard:** `{Pathway Name} · Seq {sequence} {Sequence Title}` (e.g., `Fool · Seq 9 Seer`).\n"
            "• **Legacy In-Place Rename:** Automatically updates old role formats (`Fool · Seer`) to the official numbered format.\n"
            "• **Hoisting:** High-Sequences (Sequence 4 Demigods down to Sequence 0 True Gods) have `hoist=True` enabled "
            "to tower prominently above server member lists.\n"
            "• **Old Sequence Cleanup:** Deletes older sequence roles upon promotion or demotion to prevent clutter.\n"
            "• **Auto-Restoration:** Members re-sync their Beyonder rank upon sending messages, joining voice channels, "
            "rejoining the server (`on_member_join`), running `/profile`, or when an admin runs `/angel sync-roles`.\n"
            "• **Permission Diagnostics:** If the bot lacks `manage_roles` or its role is below the target rank, "
            "actionable diagnostics are reported directly in command embeds."
        ),
    },
    "admin": {
        "title": "Archangel & Creator Administration Tools",
        "description": (
            "**Divine Control Commands:**\n"
            "• `/angel console` — Open the interactive Archangel Console: visual roster, pending trials review & one-click treasury grants.\n"
            "• `/angel grant <user> <currency> <amount>` — Generate and gift arbitrary Gold or Tarot Coins to any member.\n"
            "• `/angel sync-roles` — Force-resynchronize all Beyonder roles in the server with detailed metric diagnostics.\n"
            "• `/angel trial <user>` — Adjudicate pending Demigod and Angel acting trials.\n"
            "• `/angel bestow <user> <formula/item/characteristic>` — Grant mystical items to faithful followers.\n"
            "• `/angel cleanse <user>` — Purge corruption and restore sanity to afflicted Beyonders.\n"
            "• `/settings view/set/reset` — Configure live server parameters (e.g., shop prices, backlash hazard toggle).\n"
            "• `/creator appoint <user> <pathway> <seq>` — Instant elevation to any sequence rank.\n"
            "• `/creator strip <user>` — Completely strip Beyonder powers and reset to mortal."
        ),
    },
}


class MetaCog(commands.Cog):
    srv = app_commands.Group(name="settings", description="View and edit live server settings.")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _key_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice]:
        current = current.lower()
        return [app_commands.Choice(name=k, value=k) for k in SCHEMA if current in k][:25]

    # --- /settings --------------------------------------------------------
    @srv.command(name="view")
    @checks.admin_only
    async def settings_view(self, interaction: discord.Interaction) -> None:
        embed = persona.fog_embed(
            "Server Settings", "These apply immediately and persist in `settings.json`."
        )
        for key, spec in SCHEMA.items():
            embed.add_field(
                name=key, value=f"`{settings.get(key)}` — {spec['desc']}", inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @srv.command(name="set")
    @checks.admin_only
    @app_commands.describe(key="The setting to change.", value="New value.")
    @app_commands.autocomplete(key=_key_autocomplete)
    async def settings_set(
        self, interaction: discord.Interaction, key: str, value: str
    ) -> None:
        try:
            new_value = settings.set(key, value)
        except ValueError as exc:
            await interaction.response.send_message(
                embed=persona.error_embed(str(exc)), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=persona.success_embed("Setting Updated", f"**{key}** is now `{new_value}`."),
            ephemeral=True,
        )

    @srv.command(name="reset")
    @checks.admin_only
    @app_commands.describe(key="A setting to reset (omit to reset everything).")
    @app_commands.autocomplete(key=_key_autocomplete)
    async def settings_reset(
        self, interaction: discord.Interaction, key: str | None = None
    ) -> None:
        try:
            settings.reset(key)
        except ValueError as exc:
            await interaction.response.send_message(
                embed=persona.error_embed(str(exc)), ephemeral=True
            )
            return
        msg = (
            "All settings restored to defaults."
            if key is None
            else f"**{key}** restored to its default."
        )
        await interaction.response.send_message(
            embed=persona.success_embed("Settings Reset", msg), ephemeral=True
        )

    @srv.command(name="reload")
    @checks.admin_only
    async def settings_reload(self, interaction: discord.Interaction) -> None:
        settings.load()
        await interaction.response.send_message(
            embed=persona.success_embed("Settings Reloaded", "Re-read `settings.json`."),
            ephemeral=True,
        )

    # --- /help ------------------------------------------------------------
    async def _topic_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice]:
        current = current.lower()
        subtopics = [
            ("mechanics", "Spirit World lore, Acting Method, Sanity & Corruption"),
            ("progression", "Advancement ladder, requirements & ritual backlash"),
            ("voice", "Voice channel (VC) digestion dominance & 60s loop"),
            ("economy", "Gold, Tarot Coins, Divination, Bounties, Altar, Shop"),
            ("tarot", "Secret Tarot Club gathering & anonymous webhooks"),
            ("trials", "Demigod, Angel & Apotheosis trials & population caps"),
            ("inactivity", "Inactivity decay (>30d) & Sequence regression (>365d)"),
            ("roles", "Discord role formatting, hoisting (Seq 4-0) & diagnostics"),
            ("admin", "Archangel, Creator & server configuration commands"),
        ]
        choices = [
            app_commands.Choice(name=f"{k}: {desc}", value=k)
            for k, desc in subtopics
            if current in k or current in desc.lower()
        ]

        # Also offer command matches if user typed something specific
        cmd_names = [c.qualified_name for c in self._flatten()]
        for name in cmd_names:
            if current in name.lower() and len(choices) < 25:
                choices.append(app_commands.Choice(name=f"/{name}", value=name))

        return choices[:25]

    def _flatten(self) -> list:
        result, seen = [], set()
        for cmd in self.bot.tree.walk_commands():
            if cmd.qualified_name in seen:
                continue
            seen.add(cmd.qualified_name)
            result.append(cmd)
            if isinstance(cmd, app_commands.Group):
                for sub in cmd.walk_commands():
                    if sub.qualified_name not in seen:
                        seen.add(sub.qualified_name)
                        result.append(sub)
        return result

class OracleDoubtModal(discord.ui.Modal, title="Spirit World Oracle — Ask Doubts"):
    inquiry = discord.ui.TextInput(
        label="What doubt burdens your mind?",
        style=discord.TextStyle.paragraph,
        placeholder="Ask about Pathways, Potions, Voice Digestion, Ritual Backlash, or Server Rules...",
        required=True,
        max_length=600,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        from utils.gemini import ask_oracle

        question = self.inquiry.value.strip()
        answer = await ask_oracle(question)

        embed = persona.fog_embed(
            "The Spirit World Oracle Whispers",
            f"**Inquiry:** *\"{question}\"*\n\n{answer}",
        )
        embed.set_footer(text="The Fool's Attendant · Divine AI Oracle")
        await interaction.followup.send(embed=embed, ephemeral=True)


class HelpNavigationView(discord.ui.View):
    def __init__(self, cog: MetaCog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="Overview", style=discord.ButtonStyle.primary, row=0, emoji="📜")
    async def btn_overview(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = self.cog._build_index_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Lore & Sanity", style=discord.ButtonStyle.secondary, row=0, emoji="🔮")
    async def btn_mechanics(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sub = _HELP_SUBTOPICS["mechanics"]
        embed = persona.fog_embed(sub["title"], sub["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Progression", style=discord.ButtonStyle.secondary, row=0, emoji="⚡")
    async def btn_progression(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sub = _HELP_SUBTOPICS["progression"]
        embed = persona.fog_embed(sub["title"], sub["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Voice XP", style=discord.ButtonStyle.secondary, row=0, emoji="🎙️")
    async def btn_voice(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sub = _HELP_SUBTOPICS["voice"]
        embed = persona.fog_embed(sub["title"], sub["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Economy", style=discord.ButtonStyle.secondary, row=1, emoji="💰")
    async def btn_economy(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sub = _HELP_SUBTOPICS["economy"]
        embed = persona.fog_embed(sub["title"], sub["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Tarot Club", style=discord.ButtonStyle.secondary, row=1, emoji="👁️")
    async def btn_tarot(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sub = _HELP_SUBTOPICS["tarot"]
        embed = persona.fog_embed(sub["title"], sub["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Trials & Caps", style=discord.ButtonStyle.secondary, row=1, emoji="⚔️")
    async def btn_trials(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sub = _HELP_SUBTOPICS["trials"]
        embed = persona.fog_embed(sub["title"], sub["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Slumber Decay", style=discord.ButtonStyle.secondary, row=1, emoji="⏳")
    async def btn_inactivity(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sub = _HELP_SUBTOPICS["inactivity"]
        embed = persona.fog_embed(sub["title"], sub["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Roles", style=discord.ButtonStyle.secondary, row=2, emoji="👑")
    async def btn_roles(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sub = _HELP_SUBTOPICS["roles"]
        embed = persona.fog_embed(sub["title"], sub["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Admin Tools", style=discord.ButtonStyle.secondary, row=2, emoji="🛡️")
    async def btn_admin(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sub = _HELP_SUBTOPICS["admin"]
        embed = persona.fog_embed(sub["title"], sub["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Ask Oracle (AI Doubts)", style=discord.ButtonStyle.success, row=2, emoji="✨")
    async def btn_ai_doubts(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(OracleDoubtModal())


    @app_commands.command(name="help")
    @app_commands.describe(topic="Subtopic (mechanics/progression/voice/economy/tarot/trials/inactivity/roles/admin) or command name.")
    @app_commands.autocomplete(topic=_topic_autocomplete)
    async def help_cmd(
        self, interaction: discord.Interaction, topic: str | None = None
    ) -> None:
        """Inspect server mechanics, progression rules, voice XP, decay, economy, or ask AI doubts."""
        if topic:
            clean = topic.strip().lower()
            if clean.startswith("/"):
                clean = clean[1:]
            if clean in _HELP_SUBTOPICS:
                sub = _HELP_SUBTOPICS[clean]
                embed = persona.fog_embed(sub["title"], sub["description"])
                await interaction.response.send_message(embed=embed, view=HelpNavigationView(self))
                return
            # Check if it matches a command
            cmd = next((c for c in self._flatten() if c.qualified_name.lower() == clean), None)
            if cmd is not None:
                await self._show_command(interaction, cmd)
                return

        # Show main index with overview of Profile, Voice/Chat XP, Decay, and Advancement
        embed = self._build_index_embed()
        await interaction.response.send_message(embed=embed, view=HelpNavigationView(self))

    def _build_index_embed(self) -> discord.Embed:
        embed = persona.fog_embed(
            "The Fool's Attendant — Grimoire & Help",
            "Welcome to the mystical domain of the gray fog.\n"
            "Use the interactive **buttons below** to navigate topics, or click **✨ Ask Oracle (AI Doubts)** to ask anything!\n\n"
            "• `🔮 Lore & Sanity` — Spirit World lore, 22 Pathways, Acting Method, Sanity & Corruption\n"
            "• `⚡ Progression` — Advancement ladder, potion formulas, ingredients & ritual backlash\n"
            "• `🎙️ Voice XP` — Voice channel (VC) digestion dominance, 60s loop & +25% unmuted bonus\n"
            "• `💰 Economy` — Daily, Divination omens, Monster Bounties, Altar Sacrifices & Shop\n"
            "• `👁️ Tarot Club` — Secret assembly, auto-channel generation & anonymous webhooks\n"
            "• `⚔️ Trials & Caps` — Demigod, Angel & Apotheosis trials & pathway population caps\n"
            "• `⏳ Slumber Decay` — 30-day degradation & 365-day sequence regression with omen broadcast\n"
            "• `👑 Roles` — Role naming (`{Pathway} · Seq {seq} {Title}`), hoisting & diagnostics\n"
            "• `🛡️ Admin Tools` — Archangel grants, role sync, trial review, bestowals & settings",
        )

        embed.add_field(
            name="Beyonder & Progression Commands",
            value=(
                "`/profile` — View your 880×500 visual grimoire card with buffered time estimate\n"
                "`/pathway choose <name>` — Brew and drink your Sequence 9 potion to become a Beyonder\n"
                "`/advance` — Attempt advancement ritual (subject to backlash hazard)\n"
                "`/status [user]` — Inspect status dossier and progression metrics"
            ),
            inline=False,
        )

        embed.add_field(
            name="Mystic Economy & Gathering",
            value=(
                "`/daily` — Claim your daily stipend of Gold and Tarot Coins\n"
                "`/divine <inquiry>` — Perform pendulum divination for Gold & Tarot Coins\n"
                "`/bounty list` & `/bounty hunt <target>` — Hunt monsters and rogue Beyonders\n"
                "`/sacrifice <item> [qty]` — Offer harvested ingredients to the altar for wealth\n"
                "`/inventory` — Inspect ingredients, formulas, and characteristics\n"
                "`/shop list` & `/shop buy <item>` — Purchase ingredients, formulas, and characteristics"
            ),
            inline=False,
        )

        embed.add_field(
            name="Tarot Club Assembly",
            value=(
                "`/tarot open [channel_name]` — Open the sanctum (auto-creates channel if missing)\n"
                "`/tarot join` — Swear oath, take your Major Arcana seat & gain Tarot role\n"
                "`/tarot speak <message>` — Send anonymous messages disguised by webhooks\n"
                "`/tarot leave` & `/tarot close` — Conclude gathering and revoke access"
            ),
            inline=False,
        )

        embed.add_field(
            name="Archangel & Administration Commands",
            value=(
                "`/angel console` — Open the interactive Beyonders, Trials & Treasury Console\n"
                "`/angel grant <user> <currency> <amount>` — Generate and gift Gold or Tarot Coins\n"
                "`/angel sync-roles` — Synchronize all Beyonder roles with actionable diagnostics\n"
                "`/angel trial <user>` — Adjudicate Demigod and Angel trials\n"
                "`/angel bestow <user> <item>` & `/angel cleanse <user>` — Bless or purge taint\n"
                "`/creator appoint` & `/creator strip` — Absolute authority commands\n"
                "`/settings view` / `/settings set` / `/settings reset` — Live server configurations"
            ),
            inline=False,
        )
        embed.set_footer(text="The Fool's Attendant · Click 'Ask Oracle' to resolve any doubt")
        return embed

    async def _show_command(self, interaction: discord.Interaction, cmd) -> None:
        embed = persona.fog_embed(f"/{cmd.qualified_name}", cmd.description or "")
        if cmd.parameters:
            parts = []
            for p in cmd.parameters:
                req = "required" if p.required else "optional"
                parts.append(f"`{p.name}` — {p.description or ''} ({req})")
            embed.add_field(name="Parameters", value="\n".join(parts), inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MetaCog(bot))

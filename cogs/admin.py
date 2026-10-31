"""Divine Authority — `/creator`, `/angel`, and `/moderator` command groups."""
from __future__ import annotations
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from data import ingredients, pathways
from utils import checks, persona
from utils.roles import (
    sync_beyonder_role,
    sync_all_guild_roles,
    setup_all_pathway_roles,
    sync_angel_title_role,
    remove_angel_title_role,
    LEGENDARY_ANGEL_TITLES,
)
from db.database import Database
from cogs.anomalies import EVENT_TYPES, trigger_anomaly
from cogs.apotheosis import uniqueness_key


def _progress_bar(val: float, max_val: float = 100.0, length: int = 8) -> str:
    filled = int(round((max(0.0, min(max_val, val)) / max_val) * length))
    return "█" * filled + "░" * (length - filled)


class TreasuryCustomModal(discord.ui.Modal, title="Treasury — Custom Divine Grant"):
    amount_input = discord.ui.TextInput(
        label="Amount to Bestow",
        placeholder="e.g. 10000",
        min_length=1,
        max_length=10,
        required=True,
    )
    currency_input = discord.ui.TextInput(
        label="Currency Type",
        placeholder="Type 'gold' or 'tarot'",
        default="gold",
        min_length=4,
        max_length=5,
        required=True,
    )
    recipient_input = discord.ui.TextInput(
        label="Recipient ID or @mention (Optional)",
        placeholder="Leave blank to use selected member from console",
        required=False,
    )

    def __init__(self, console_view: AngelConsoleView):
        super().__init__()
        self.console_view = console_view
        if console_view.selected_user_id:
            self.recipient_input.default = str(console_view.selected_user_id)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        raw_cur = self.currency_input.value.strip().lower()
        if raw_cur not in ("gold", "tarot"):
            await interaction.response.send_message(
                embed=persona.error_embed("Currency must be either 'gold' or 'tarot'."),
                ephemeral=True,
            )
            return

        try:
            amt = int(self.amount_input.value.strip().replace(",", ""))
            if amt <= 0:
                raise ValueError()
        except ValueError:
            await interaction.response.send_message(
                embed=persona.error_embed("Amount must be a positive whole integer."),
                ephemeral=True,
            )
            return

        target_id = self.console_view.selected_user_id
        raw_recip = self.recipient_input.value.strip()
        if raw_recip:
            cleaned = raw_recip.replace("<@", "").replace(">", "").replace("!", "")
            if cleaned.isdigit():
                target_id = int(cleaned)

        if not target_id:
            await interaction.response.send_message(
                embed=persona.error_embed("No recipient specified. Please select a user or enter their ID."),
                ephemeral=True,
            )
            return

        self.console_view.selected_user_id = target_id
        db = self.console_view.db
        if raw_cur == "gold":
            db.add_gold(target_id, amt)
            cname = f"{amt:,} Gold Pounds"
        else:
            db.add_tarot(target_id, amt)
            cname = f"{amt:,} Tarot Coins"

        embed = self.console_view.build_current_embed()
        self.console_view.update_components()
        await interaction.response.edit_message(embed=embed, view=self.console_view)
        await interaction.followup.send(
            embed=persona.success_embed(
                "Divine Treasury Boon",
                f"Archangel Council has bestowed **{cname}** upon <@{target_id}>.",
            ),
            ephemeral=True,
        )


class RecipientUserSelect(discord.ui.UserSelect):
    def __init__(self, console_view: AngelConsoleView):
        super().__init__(
            placeholder="Select a server member to grant currency...",
            min_values=1,
            max_values=1,
            row=1,
        )
        self.console_view = console_view

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_user = self.values[0]
        self.console_view.selected_user_id = selected_user.id
        embed = self.console_view.build_current_embed()
        self.console_view.update_components()
        await interaction.response.edit_message(embed=embed, view=self.console_view)


class TrialSelect(discord.ui.Select):
    def __init__(self, console_view: AngelConsoleView, trials: list[dict]):
        options: list[discord.SelectOption] = []
        for t in trials[:25]:
            uid = int(t["user_id"])
            user = console_view.bot.get_user(uid)
            name = user.display_name if user else f"User {uid}"
            t_seq = t["target_sequence"]
            t_kind = t.get("trial_kind", "trial").capitalize()
            options.append(
                discord.SelectOption(
                    label=f"{name[:25]} (Seq {t_seq})",
                    value=str(uid),
                    description=f"{t_kind} Trial",
                    default=(console_view.selected_trial_user_id == uid),
                )
            )
        super().__init__(
            placeholder="Select a candidate to review or pass their trial...",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
        )
        self.console_view = console_view

    async def callback(self, interaction: discord.Interaction) -> None:
        self.console_view.selected_trial_user_id = int(self.values[0])
        embed = self.console_view.build_current_embed()
        self.console_view.update_components()
        await interaction.response.edit_message(embed=embed, view=self.console_view)


class AngelConsoleView(discord.ui.View):
    def __init__(self, bot: commands.Bot, guild: discord.Guild, admin_id: int):
        super().__init__(timeout=900.0)
        self.bot = bot
        self.guild = guild
        self.admin_id = admin_id
        self.current_tab = "overview"  # "overview" | "trials" | "treasury"
        self.page = 0
        self.page_size = 5
        self.selected_user_id: int | None = None
        self.selected_trial_user_id: int | None = None

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False
        is_admin = interaction.user.guild_permissions.administrator
        is_owner = (interaction.user.id == interaction.guild.owner_id)
        if not (is_admin or is_owner or interaction.user.id == self.admin_id):
            await interaction.response.send_message(
                embed=persona.error_embed("Only Archangels (Administrators) may operate the Divine Console."),
                ephemeral=True,
            )
            return False
        return True

    def build_current_embed(self) -> discord.Embed:
        if self.current_tab == "trials":
            return self._build_trials_embed()
        elif self.current_tab == "treasury":
            return self._build_treasury_embed()
        else:
            return self._build_overview_embed()

    def _build_overview_embed(self) -> discord.Embed:
        beyonders = self.db.all_beyonders()
        trials = self.db.all_trials()
        total_beyonders = len(beyonders)
        mortals = max(0, (self.guild.member_count or 0) - total_beyonders)

        high_seq = [b for b in beyonders if int(b["sequence"]) <= 4]
        mid_seq = [b for b in beyonders if 5 <= int(b["sequence"]) <= 7]
        low_seq = [b for b in beyonders if int(b["sequence"]) >= 8]
        mad_users = [b for b in beyonders if float(b.get("corruption", 0)) >= 50.0 or int(b.get("corrupted_state", 0)) == 1]

        embed = persona.fog_embed(
            "Archangel Divine Console — Beyonder Registry",
            (
                "Supernatural ledger of all awakened members, sequence ladders, and sanity metrics.\n\n"
                f"• 👥 **Awakened Beyonders:** {total_beyonders} | 👤 **Ordinary Mortals:** {mortals}\n"
                f"• 👑 **High Seq (0–4):** {len(high_seq)} | ⚡ **Mid Seq (5–7):** {len(mid_seq)} | 🌿 **Low Seq (8–9):** {len(low_seq)}\n"
                f"• ⚠️ **Madness Alerts:** {len(mad_users)} afflicted | ⚔️ **Pending Trials:** {len(trials)}"
            )
        )

        if not beyonders:
            embed.add_field(
                name="No Awakened Beyonders",
                value="No server members have consumed an initial potion (`/pathway choose <pathway>`) yet. All remain ordinary mortals.",
                inline=False,
            )
            return embed

        sorted_beyonders = sorted(
            beyonders,
            key=lambda b: (int(b["sequence"]), -float(b.get("digestion", 0.0)), -int(b.get("active_days", 0)))
        )

        total_pages = max(1, (len(sorted_beyonders) + self.page_size - 1) // self.page_size)
        self.page = max(0, min(self.page, total_pages - 1))
        start_idx = self.page * self.page_size
        page_items = sorted_beyonders[start_idx : start_idx + self.page_size]

        for b in page_items:
            uid = int(b["user_id"])
            seq = int(b["sequence"])
            path_key = b["pathway"]
            p_info = pathways.get_pathway(path_key)
            path_name = p_info["name"] if p_info else path_key.capitalize()
            seq_title = pathways.sequence_name(path_key, seq)
            digestion = float(b.get("digestion", 0.0))
            sanity = float(b.get("sanity", 100.0))
            corruption = float(b.get("corruption", 0.0))
            gold = int(b.get("gold", 0))
            tarot = int(b.get("tarot_coins", 0))
            vc_mins = int(b.get("vc_minutes", 0))
            vc_hrs = vc_mins / 60.0
            active_days = int(b.get("active_days", 0))

            if seq == 0:
                badge = "👑 True Deity"
            elif seq in (1, 2):
                badge = "🪽 Archangel"
            elif seq in (3, 4):
                badge = "👁️ Demigod / Saint"
            elif int(b.get("corrupted_state", 0)) == 1 or corruption >= 80.0:
                badge = "🩸 Severe Madness"
            elif corruption >= 50.0:
                badge = "⚠️ Fog-Afflicted"
            elif sanity <= 30.0:
                badge = "🧠 Fractured Mind"
            else:
                badge = "✨ Stable"

            bar = _progress_bar(digestion)
            angel_row = self.db.get_angel_title(uid)
            angel_str = f"• **Divine Title:** 🪽 Archangel · {angel_row['title']}\n" if angel_row else ""
            embed.add_field(
                name=f"{badge} · <@{uid}> ({seq_title})",
                value=(
                    f"{angel_str}"
                    f"• **Pathway:** {path_name} (Sequence {seq})\n"
                    f"• **Digestion:** `[{bar}]` {digestion:.1f}%\n"
                    f"• **Madness:** Sanity {sanity:.0f}% · Corruption {corruption:.0f}%\n"
                    f"• **Activity:** {vc_hrs:.1f}h VC logged · {active_days} active days\n"
                    f"• **Wealth:** 🪙 {gold:,} Gold · 🎴 {tarot} Tarot Coins"
                ),
                inline=False,
            )

        embed.set_footer(text=f"Page {self.page + 1} of {total_pages} • Total Beyonders: {total_beyonders}")
        return embed

    def _build_trials_embed(self) -> discord.Embed:
        trials = self.db.all_trials()
        if not trials:
            embed = persona.fog_embed(
                "Advancement Trials Council",
                (
                    "**All Ascension Thresholds Clear.**\n\n"
                    "No Beyonders are currently awaiting divine trial review.\n"
                    "Members who satisfy their 100% digestion and ingredients at Sequence 4, 3, 2, 1, or 0 "
                    "will appear here for Archangel adjudication."
                )
            )
            return embed

        embed = persona.fog_embed(
            f"Advancement Trials Council ({len(trials)} Pending)",
            (
                "The following candidates have completed their potion digestion and acquired ritual ingredients. "
                "They stand at the threshold awaiting the Archangel Council's adjudication.\n\n"
                "Select a candidate below to inspect or pass their trial."
            )
        )

        for t in trials:
            uid = int(t["user_id"])
            t_seq = int(t["target_sequence"])
            t_kind = t.get("trial_kind", "ascension")
            kind_label = {
                "demigod": "Demigod Trial",
                "angel": "Angel's Acting Trial",
                "acting": "Acting Method Trial",
                "apotheosis": "Sequence 0 Apotheosis",
            }.get(t_kind, f"{t_kind.capitalize()} Trial")

            user_row = self.db.get_user(uid)
            path_key = user_row["pathway"] if user_row else "unknown"
            p_info = pathways.get_pathway(path_key)
            path_name = p_info["name"] if p_info else path_key
            target_title = pathways.sequence_name(path_key, t_seq)

            is_sel = (self.selected_trial_user_id == uid)
            prefix = "👉 **[SELECTED CANDIDATE]**\n" if is_sel else ""

            digestion = float(user_row.get("digestion", 100.0)) if user_row else 100.0
            sanity = float(user_row.get("sanity", 100.0)) if user_row else 100.0
            corruption = float(user_row.get("corruption", 0.0)) if user_row else 0.0
            gold = int(user_row.get("gold", 0)) if user_row else 0
            tarot = int(user_row.get("tarot_coins", 0)) if user_row else 0

            embed.add_field(
                name=f"⚔️ Target: {target_title} (Seq {t_seq}) — <@{uid}>",
                value=(
                    f"{prefix}"
                    f"• **Pathway:** {path_name} | **Trial Type:** {kind_label}\n"
                    f"• **Digestion:** {digestion:.1f}% | **Sanity:** {sanity:.0f}% | **Corruption:** {corruption:.0f}%\n"
                    f"• **Holdings:** 🪙 {gold:,} Gold · 🎴 {tarot} Tarot Coins"
                ),
                inline=False,
            )

        embed.set_footer(text=f"{len(trials)} trials awaiting council action")
        return embed

    def _build_treasury_embed(self) -> discord.Embed:
        embed = persona.fog_embed(
            "Archangel Divine Treasury — Currency Distribution",
            (
                "Generate and grant **Gold Pounds** and **Tarot Coins** directly to any server member.\n"
                "As an Archangel, your authority allows unrestricted treasury minting."
            )
        )

        if self.selected_user_id:
            row = self.db.ensure_user(self.selected_user_id)
            target = self.guild.get_member(self.selected_user_id)
            dname = target.display_name if target else f"User {self.selected_user_id}"
            path_key = row.get("pathway")
            seq = row.get("sequence")
            if path_key and seq is not None:
                rank_str = f"**{pathways.sequence_name(path_key, int(seq))}** (Sequence {seq})"
            else:
                rank_str = "*Ordinary Mortal (No Pathway)*"

            gold = int(row.get("gold", 0))
            tarot = int(row.get("tarot_coins", 0))

            embed.add_field(
                name="🎯 Selected Recipient",
                value=(
                    f"**Member:** <@{self.selected_user_id}> ({dname})\n"
                    f"• **Rank:** {rank_str}\n"
                    f"• **Vault Balance:** 🪙 **{gold:,}** Gold Pounds | 🎴 **{tarot:,}** Tarot Coins\n\n"
                    f"*Click any preset grant button below for instant distribution, or click ✍️ Custom Grant.*"
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name="🎯 Selected Recipient: None",
                value=(
                    "Select a recipient from the dropdown user menu below.\n"
                    "Once selected, you can bestow Gold Pounds or Tarot Coins in a single click."
                ),
                inline=False,
            )
        return embed

    def update_components(self) -> None:
        self.clear_items()
        trials = self.db.all_trials()
        trial_count = len(trials)

        # Tab Row (Row 0)
        btn_overview = discord.ui.Button(
            label="Beyonders Overview",
            style=discord.ButtonStyle.success if self.current_tab == "overview" else discord.ButtonStyle.secondary,
            emoji="📋",
            row=0,
        )
        btn_overview.callback = self._on_overview_tab
        self.add_item(btn_overview)

        trial_btn_style = (
            discord.ButtonStyle.danger if trial_count > 0 and self.current_tab == "trials"
            else discord.ButtonStyle.primary if trial_count > 0
            else discord.ButtonStyle.success if self.current_tab == "trials"
            else discord.ButtonStyle.secondary
        )
        btn_trials = discord.ui.Button(
            label=f"Trials ({trial_count})",
            style=trial_btn_style,
            emoji="⚖️",
            row=0,
        )
        btn_trials.callback = self._on_trials_tab
        self.add_item(btn_trials)

        btn_treasury = discord.ui.Button(
            label="Treasury Distribution",
            style=discord.ButtonStyle.success if self.current_tab == "treasury" else discord.ButtonStyle.secondary,
            emoji="💰",
            row=0,
        )
        btn_treasury.callback = self._on_treasury_tab
        self.add_item(btn_treasury)

        btn_refresh = discord.ui.Button(
            label="Refresh",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            row=0,
        )
        btn_refresh.callback = self._on_refresh
        self.add_item(btn_refresh)

        # Tab Specific Components
        if self.current_tab == "overview":
            beyonders = self.db.all_beyonders()
            total_pages = max(1, (len(beyonders) + self.page_size - 1) // self.page_size)
            if total_pages > 1:
                btn_prev = discord.ui.Button(
                    label="◀ Prev Page",
                    style=discord.ButtonStyle.primary,
                    disabled=(self.page <= 0),
                    row=1,
                )
                btn_prev.callback = self._on_prev_page
                self.add_item(btn_prev)

                btn_next = discord.ui.Button(
                    label="Next Page ▶",
                    style=discord.ButtonStyle.primary,
                    disabled=(self.page >= total_pages - 1),
                    row=1,
                )
                btn_next.callback = self._on_next_page
                self.add_item(btn_next)

        elif self.current_tab == "trials":
            if trials:
                self.add_item(TrialSelect(self, trials))
                btn_pass_one = discord.ui.Button(
                    label="Pass Selected Trial",
                    style=discord.ButtonStyle.success,
                    emoji="⚔️",
                    disabled=(self.selected_trial_user_id is None),
                    row=2,
                )
                btn_pass_one.callback = self._on_pass_selected_trial
                self.add_item(btn_pass_one)

                btn_pass_all = discord.ui.Button(
                    label=f"Pass All Trials ({len(trials)})",
                    style=discord.ButtonStyle.primary,
                    emoji="⚡",
                    row=2,
                )
                btn_pass_all.callback = self._on_pass_all_trials
                self.add_item(btn_pass_all)

        elif self.current_tab == "treasury":
            self.add_item(RecipientUserSelect(self))

            btn_g1 = discord.ui.Button(label="+1,000 Gold", style=discord.ButtonStyle.secondary, emoji="🪙", row=2)
            btn_g1.callback = lambda i, c="gold", a=1000: self._quick_grant(i, c, a)
            self.add_item(btn_g1)

            btn_g5 = discord.ui.Button(label="+5,000 Gold", style=discord.ButtonStyle.secondary, emoji="🪙", row=2)
            btn_g5.callback = lambda i, c="gold", a=5000: self._quick_grant(i, c, a)
            self.add_item(btn_g5)

            btn_t10 = discord.ui.Button(label="+10 Tarot", style=discord.ButtonStyle.secondary, emoji="🎴", row=2)
            btn_t10.callback = lambda i, c="tarot", a=10: self._quick_grant(i, c, a)
            self.add_item(btn_t10)

            btn_t50 = discord.ui.Button(label="+50 Tarot", style=discord.ButtonStyle.secondary, emoji="🎴", row=2)
            btn_t50.callback = lambda i, c="tarot", a=50: self._quick_grant(i, c, a)
            self.add_item(btn_t50)

            btn_custom = discord.ui.Button(label="Custom Grant...", style=discord.ButtonStyle.primary, emoji="✍️", row=2)
            btn_custom.callback = self._on_custom_grant
            self.add_item(btn_custom)

    async def _on_overview_tab(self, interaction: discord.Interaction) -> None:
        self.current_tab = "overview"
        embed = self.build_current_embed()
        self.update_components()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_trials_tab(self, interaction: discord.Interaction) -> None:
        self.current_tab = "trials"
        embed = self.build_current_embed()
        self.update_components()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_treasury_tab(self, interaction: discord.Interaction) -> None:
        self.current_tab = "treasury"
        embed = self.build_current_embed()
        self.update_components()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_refresh(self, interaction: discord.Interaction) -> None:
        embed = self.build_current_embed()
        self.update_components()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_prev_page(self, interaction: discord.Interaction) -> None:
        self.page = max(0, self.page - 1)
        embed = self.build_current_embed()
        self.update_components()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_next_page(self, interaction: discord.Interaction) -> None:
        self.page += 1
        embed = self.build_current_embed()
        self.update_components()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_pass_selected_trial(self, interaction: discord.Interaction) -> None:
        if not self.selected_trial_user_id:
            await interaction.response.send_message(
                embed=persona.error_embed("Please select a trial candidate first."),
                ephemeral=True,
            )
            return
        uid = self.selected_trial_user_id
        self.db.clear_trial(uid)
        self.selected_trial_user_id = None
        embed = self.build_current_embed()
        self.update_components()
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(
            embed=persona.success_embed(
                "Trial Adjudicated",
                f"Ascension trial passed for <@{uid}>! They may now run `/advance` to complete ascension.",
            ),
            ephemeral=True,
        )

    async def _on_pass_all_trials(self, interaction: discord.Interaction) -> None:
        trials = self.db.all_trials()
        if not trials:
            await interaction.response.send_message(
                embed=persona.error_embed("No pending trials to adjudicate."),
                ephemeral=True,
            )
            return
        for t in trials:
            self.db.clear_trial(int(t["user_id"]))
        self.selected_trial_user_id = None
        embed = self.build_current_embed()
        self.update_components()
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(
            embed=persona.success_embed(
                "All Trials Passed",
                f"Successfully adjudicated and passed all {len(trials)} pending trials! Candidates may now advance.",
            ),
            ephemeral=True,
        )

    async def _quick_grant(self, interaction: discord.Interaction, currency: str, amount: int) -> None:
        if not self.selected_user_id:
            await interaction.response.send_message(
                embed=persona.error_embed("Please select a recipient member from the menu above first."),
                ephemeral=True,
            )
            return
        if currency == "gold":
            self.db.add_gold(self.selected_user_id, amount)
            label = f"{amount:,} Gold Pounds"
        else:
            self.db.add_tarot(self.selected_user_id, amount)
            label = f"{amount:,} Tarot Coins"

        embed = self.build_current_embed()
        self.update_components()
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(
            embed=persona.success_embed(
                "Treasury Bestowal",
                f"Archangel Council has granted **{label}** to <@{self.selected_user_id}>.",
            ),
            ephemeral=True,
        )

    async def _on_custom_grant(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TreasuryCustomModal(self))


async def _angel_title_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    q = current.strip().lower()
    choices = [
        app_commands.Choice(name=t, value=t)
        for t in LEGENDARY_ANGEL_TITLES
        if q in t.lower()
    ]
    if q and not any(c.value.lower() == q for c in choices):
        custom_name = current.strip()
        if not custom_name.lower().startswith("angel of") and not custom_name.lower().startswith("archangel"):
            custom_name = f"Angel of {custom_name.title()}"
        choices.insert(0, app_commands.Choice(name=f"Custom: {custom_name}", value=custom_name))
    return choices[:25]


class AdminCog(commands.Cog):
    creator = app_commands.Group(
        name="creator", description="Above the Sequences — Server Owner only."
    )
    angel = app_commands.Group(
        name="angel", description="Archangel Council — Server Admin only."
    )
    moderator = app_commands.Group(
        name="moderator", description="Delegated Moderator powers."
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    # ======================================================================
    # CREATOR (owner)
    # ======================================================================
    @creator.command(name="appoint")
    @app_commands.describe(
        user="Whom to appoint.",
        pathway="The Pathway to place them upon.",
        seq="Sequence to grant (0-9; 0 is True God).",
    )
    @checks.owner_only
    async def creator_appoint(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        pathway: str,
        seq: app_commands.Range[int, 0, 9],
    ) -> None:
        """Unilaterally grant any rank from Sequence 9 to Sequence 0."""
        key = pathways.resolve_pathway(pathway)
        if key is None:
            await interaction.response.send_message(
                embed=persona.error_embed(f"No such Pathway: **{pathway}**."),
                ephemeral=True,
            )
            return
        self.db.set_sequence(user.id, key, seq)
        role, error_diag = await sync_beyonder_role(
            self.db, user, key, seq, guild=interaction.guild
        )
        if seq == 0:
            self.db.set_god(key, user.id)
            self.db.add_item(user.id, uniqueness_key(key), 1)

        title = pathways.sequence_name(key, seq)
        embed = persona.success_embed(
            "Divine Appointment",
            f"By the word of the one Above the Sequences, **{user.display_name}** is "
            f"now **{title}** (Sequence {seq}) upon the Path of "
            f"**{pathways.get_pathway(key)['name']}**.",
        )
        if error_diag:
            embed.add_field(name="⚠️ Role Diagnostics", value=error_diag, inline=False)

        await interaction.response.send_message(embed=embed)

    @creator.command(name="item")
    @app_commands.describe(
        user="Whom to grant the item to.",
        item="Item key: 'gold', 'tarot', an ingredient name, or "
              "'formula:<pathway>:<seq>' / 'characteristic:<pathway>:<seq>' / "
              "'uniqueness:<pathway>'.",
        qty="Quantity.",
    )
    @checks.owner_only
    async def creator_item_spawn(
        self, interaction: discord.Interaction, user: discord.Member, item: str, qty: int = 1
    ) -> None:
        """Grant gold, Tarot Coins, or any inventory item (for testing/rewards)."""
        if qty < 1:
            qty = 1
        item_lower = item.strip().lower()
        if item_lower == "gold":
            self.db.add_gold(user.id, qty)
            label = f"{qty:,} Gold Pounds"
        elif item_lower == "tarot":
            self.db.add_tarot(user.id, qty)
            label = f"{qty:,} Tarot Coins"
        else:
            self.db.add_item(user.id, item, qty)
            label = f"{qty}× {item}"
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Item Manifested",
                f"Granted **{label}** to **{user.display_name}**.",
            )
        )

    @creator.command(name="strip")
    @app_commands.describe(user="The Sequence 0 to unmake.")
    @checks.owner_only
    async def creator_strip(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Strip a Deity of their Uniqueness and cast them back to Sequence 1."""
        row = self.db.ensure_user(user.id)
        if row["pathway"] is None or int(row["sequence"]) != 0:
            await interaction.response.send_message(
                embed=persona.error_embed("That one is no True God to be unmade."),
                ephemeral=True,
            )
            return
        key = row["pathway"]
        self.db.strip_god(key)
        self.db.set_sequence(user.id, key, 1)
        role, error_diag = await sync_beyonder_role(
            self.db, user, key, 1, guild=interaction.guild
        )
        self.db.remove_item(user.id, uniqueness_key(key), 1)

        embed = persona.fog_embed(
            "Uniqueness Stolen",
            f"The one Above the Sequences has torn the **Uniqueness of "
            f"{pathways.get_pathway(key)['name']}** from **{user.display_name}**, "
            f"casting them back to Sequence 1.",
        )
        if error_diag:
            embed.add_field(name="⚠️ Role Diagnostics", value=error_diag, inline=False)

        await interaction.response.send_message(embed=embed)

    @creator.command(name="force-loss")
    @app_commands.describe(user="Whom to force into Loss of Control.")
    @checks.owner_only
    async def creator_force_loss(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        """Force a Beyonder into absolute Loss of Control."""
        self.db.set_corruption(user.id, 100.0)
        self.db.set_sanity(user.id, 0.0)
        await interaction.response.send_message(
            embed=persona.error_embed(
                f"**{user.display_name}** has been forced into **Loss of Control**. "
                f"Their corruption is absolute; the fog will claim them shortly."
            )
        )

    # ======================================================================
    # ANGEL (admin)
    # ======================================================================
    @angel.command(name="console")
    @checks.admin_only
    async def angel_console(self, interaction: discord.Interaction) -> None:
        """Open the interactive Archangel Divine Console for Beyonders, trials, and treasury."""
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                embed=persona.error_embed("This console may only be manifested within a server."),
                ephemeral=True,
            )
            return
        view = AngelConsoleView(self.bot, guild, interaction.user.id)
        embed = view.build_current_embed()
        view.update_components()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @angel.command(name="sync-roles")
    @checks.admin_only
    async def angel_sync_roles(self, interaction: discord.Interaction) -> None:
        """Resynchronize all Beyonder roles across the server and return execution metrics."""
        guild = interaction.guild
        if guild is None:
            return
        await interaction.response.defer(ephemeral=True)
        metrics = await sync_all_guild_roles(self.bot, guild)
        await interaction.followup.send(
            embed=persona.success_embed(
                "Role Synchronization Complete",
                f"**Guild:** {guild.name}\n"
                f"• **Successfully Synced:** {metrics['synced']} members\n"
                f"• **Skipped:** {metrics['skipped']}\n"
                f"• **Errors / Lacking Permissions:** {metrics['errors']}",
            ),
            ephemeral=True,
        )

    @angel.command(name="setup-roles")
    @checks.admin_only
    async def angel_setup_roles(self, interaction: discord.Interaction) -> None:
        """Pre-provision all 22 Pathway allegiance roles and the Archangel Council role in this server."""
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                embed=persona.error_embed("This command may only be manifested within a server."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=False)
        res = await setup_all_pathway_roles(guild)

        err_text = ""
        if res["errors"]:
            err_text = f"\n\n⚠️ **Notices:**\n" + "\n".join(f"• {e}" for e in res["errors"][:5])

        embed = persona.success_embed(
            "Pathway & Council Roles Initialized",
            (
                f"**Guild:** {guild.name}\n\n"
                f"• **🪽 Archangel Council Role:** {'Created & Configured' if res['council_role'] else 'Skipped/Unavailable'}\n"
                f"• **New Pathway Roles Created:** {res['pathways_created']}\n"
                f"• **Existing Pathway Roles:** {res['pathways_existing']}\n"
                f"• **Total Pathways Provisioned:** {res['pathways_created'] + res['pathways_existing']} / 22"
                f"{err_text}\n\n"
                f"Beyonders will automatically receive both their Pathway allegiance role (`Pathway · {{Name}}`) "
                f"and their Sequence rank role (`{{Name}} · Seq {{seq}} {{Title}}`) upon advancement or `/angel sync-roles`."
            ),
        )
        await interaction.followup.send(embed=embed)

    @angel.command(name="title-set")
    @app_commands.describe(
        title="Unique Angel Title (e.g. 'Angel of Time', 'Angel of Retribution').",
        member="The administrator receiving the title (defaults to yourself).",
    )
    @app_commands.autocomplete(title=_angel_title_autocomplete)
    @checks.admin_only
    async def angel_title_set(
        self,
        interaction: discord.Interaction,
        title: str,
        member: Optional[discord.Member] = None,
    ) -> None:
        """Bestow a unique divine Angel Title upon an administrator (creates a hoisted Archangel role)."""
        target = member or interaction.user
        if not isinstance(target, discord.Member):
            target = interaction.guild.get_member(target.id) if interaction.guild else None

        if target is None:
            await interaction.response.send_message(
                embed=persona.error_embed("Could not resolve target member in this server."),
                ephemeral=True,
            )
            return

        clean_title = title.strip()
        if clean_title.startswith("🪽 Archangel · "):
            clean_title = clean_title.replace("🪽 Archangel · ", "")
        elif clean_title.startswith("🪽 "):
            clean_title = clean_title.replace("🪽 ", "")

        role, err = await sync_angel_title_role(self.db, target, clean_title)
        if err and role is None:
            await interaction.response.send_message(
                embed=persona.error_embed(f"Failed to bestow Angel Title: {err}"),
                ephemeral=True,
            )
            return

        embed = persona.success_embed(
            "Divine Archangel Bestowal",
            (
                f"**{target.display_name}** has claimed their seat among the divine!\n\n"
                f"🪽 **Divine Title:** Archangel · {clean_title}\n"
                f"🏷️ **Assigned Role:** {role.mention if role else 'None'}\n"
                f"🏛️ **Council:** Granted **🪽 Archangel Council** membership.\n\n"
                f"*Their unique title is now visible across `/profile`, `/status`, and the Archangel Console.*"
            ),
        )
        if err:
            embed.add_field(name="⚠️ Diagnostic Notice", value=err, inline=False)

        await interaction.response.send_message(embed=embed)

    @angel.command(name="title-list")
    async def angel_title_list(self, interaction: discord.Interaction) -> None:
        """List active Angel Titles in the realm and legendary titles available for claim."""
        active = self.db.all_angel_titles()
        embed = persona.fog_embed(
            "The Archangel Council of Divine Titles",
            "Administrators holding supreme authority in the realm bear unique Angel Titles.\n",
        )

        active_lines = []
        claimed_names = set()
        for row in active:
            uid = int(row["user_id"])
            t = row["title"]
            claimed_names.add(t.lower())
            active_lines.append(f"• <@{uid}> — **🪽 Archangel · {t}**")

        if active_lines:
            embed.add_field(
                name="✨ Active Archangels",
                value="\n".join(active_lines),
                inline=False,
            )
        else:
            embed.add_field(
                name="✨ Active Archangels",
                value="*No Angel titles have been claimed yet in this realm. Use `/angel title-set` to claim one.*",
                inline=False,
            )

        avail = [t for t in LEGENDARY_ANGEL_TITLES if t.lower() not in claimed_names]
        if avail:
            sample_avail = avail[:12]
            embed.add_field(
                name="📜 Legendary Titles Available for Bestowal",
                value=", ".join(f"`{t}`" for t in sample_avail) + (f" *and {len(avail) - len(sample_avail)} more...*" if len(avail) > len(sample_avail) else ""),
                inline=False,
            )

        embed.set_footer(text="Bestow titles using /angel title-set <title> [member]")
        await interaction.response.send_message(embed=embed)

    @angel.command(name="title-remove")
    @app_commands.describe(member="The member whose title will be revoked.")
    @checks.admin_only
    async def angel_title_remove(
        self, interaction: discord.Interaction, member: Optional[discord.Member] = None
    ) -> None:
        """Revoke a member's Angel Title and remove their Archangel role."""
        target = member or interaction.user
        if not isinstance(target, discord.Member):
            target = interaction.guild.get_member(target.id) if interaction.guild else None

        if target is None:
            await interaction.response.send_message(
                embed=persona.error_embed("Could not resolve target member."),
                ephemeral=True,
            )
            return

        err = await remove_angel_title_role(self.db, target)
        if err:
            await interaction.response.send_message(
                embed=persona.error_embed(f"Failed to remove Angel title: {err}"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=persona.success_embed(
                "Angel Title Revoked",
                f"**{target.display_name}**'s divine title and associated Archangel roles have been stripped.",
            )
        )

    @angel.command(name="bestow")
    @app_commands.describe(
        user="Whom to promote.",
        pathway="The Pathway to place them upon.",
        seq="Sequence to grant (9-4 only).",
    )
    @checks.admin_only
    async def angel_bestow(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        pathway: str,
        seq: app_commands.Range[int, 0, 9],
    ) -> None:
        """Grant ranks up to Sequence 4 only. Sequence 3+ is divinely rejected."""
        if seq in (0, 1, 2, 3):
            await interaction.response.send_message(
                embed=persona.error_embed(
                    "**Divine Rejection.** The Archangel Council may raise no one beyond "
                    "Sequence 4. Only the one Above the Sequences may bestow Demigods and "
                    "higher."
                ),
                ephemeral=True,
            )
            return
        key = pathways.resolve_pathway(pathway)
        if key is None:
            await interaction.response.send_message(
                embed=persona.error_embed(f"No such Pathway: **{pathway}**."),
                ephemeral=True,
            )
            return
        self.db.set_sequence(user.id, key, seq)
        role, error_diag = await sync_beyonder_role(
            self.db, user, key, seq, guild=interaction.guild
        )
        embed = persona.success_embed(
            "Promotion",
            f"**{user.display_name}** is raised to **{pathways.sequence_name(key, seq)}** "
            f"(Sequence {seq}) upon the Path of **{pathways.get_pathway(key)['name']}**.",
        )
        if error_diag:
            embed.add_field(name="⚠️ Role Diagnostics", value=error_diag, inline=False)

        await interaction.response.send_message(embed=embed)

    @angel.command(name="grant")
    @app_commands.describe(
        user="Whom to grant currency to.",
        currency="Currency type: gold or tarot.",
        amount="Amount to grant.",
    )
    @app_commands.choices(
        currency=[
            app_commands.Choice(name="Gold Pounds", value="gold"),
            app_commands.Choice(name="Tarot Coins", value="tarot"),
        ]
    )
    @checks.admin_only
    async def angel_grant(
        self, interaction: discord.Interaction, user: discord.Member, currency: str, amount: int
    ) -> None:
        """Generate and bestow Gold Pounds or Tarot Coins upon any member."""
        if amount <= 0:
            await interaction.response.send_message(
                embed=persona.error_embed("Amount must be positive."), ephemeral=True
            )
            return
        if currency == "gold":
            self.db.add_gold(user.id, amount)
            label = f"{amount:,} Gold Pounds"
        else:
            self.db.add_tarot(user.id, amount)
            label = f"{amount:,} Tarot Coins"
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Divine Treasury Boon",
                f"The Archangel Council has bestowed **{label}** upon **{user.display_name}**.",
            )
        )

    @angel.command(name="anomaly")
    @app_commands.describe(event_type="The Spirit World Anomaly to trigger.")
    @app_commands.choices(
        event_type=[
            app_commands.Choice(name=v["name"], value=k) for k, v in EVENT_TYPES.items()
        ]
    )
    @checks.admin_only
    async def angel_anomaly_trigger(
        self, interaction: discord.Interaction, event_type: str
    ) -> None:
        """Manually spawn a Spirit World random encounter in this channel."""
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=persona.error_embed("An anomaly may only manifest in a text channel."),
                ephemeral=True,
            )
            return
        ok = await trigger_anomaly(self.bot, channel, event_type)
        if not ok:
            await interaction.response.send_message(
                embed=persona.error_embed("The fog refused to manifest that anomaly."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=persona.fog_embed("The Fog Stirs", "The anomaly has been summoned."),
            ephemeral=True,
        )

    @angel.command(name="cleanse")
    @app_commands.describe(user="Whom to cleanse.")
    @checks.admin_only
    async def angel_cleanse(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Reset an afflicted member's madness meter (corruption and sanity)."""
        self.db.set_corruption(user.id, 0.0)
        self.db.set_sanity(user.id, 100.0)
        self.db.clear_corrupted(user.id)
        self.db.clear_fog(user.id)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Cleansed",
                f"The fog withdraws from **{user.display_name}**. Their madness meter is "
                f"reset — corruption purged, sanity restored.",
            )
        )

    @angel.command(name="purify")
    @app_commands.describe(user="Whose corruption to purge.")
    @checks.admin_only
    async def angel_purify(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Purge corruption without touching sanity."""
        self.db.set_corruption(user.id, 0.0)
        self.db.clear_corrupted(user.id)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Purified", f"The corruption within **{user.display_name}** has been purged."
            )
        )

    @angel.command(name="trial")
    @app_commands.describe(user="Whose trial to pass.")
    @checks.admin_only
    async def angel_trial_pass(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        """Adjudicate and pass a pending advancement trial."""
        pending = self.db.get_trial(user.id)
        if pending is None:
            await interaction.response.send_message(
                embed=persona.error_embed("That one has no pending trial."),
                ephemeral=True,
            )
            return
        self.db.clear_trial(user.id)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Trial Passed",
                f"**{user.display_name}** has survived their trial. They may now run "
                f"`/advance` to complete their ascension.",
            )
        )

    @angel.command(name="apotheosis")
    @app_commands.describe(user="Whom to crown as Sequence 0.")
    @checks.admin_only
    async def angel_apotheosis_crown(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        """Crown a King of Angels who has completed their Apotheosis trial."""
        row = self.db.ensure_user(user.id)
        pending = self.db.get_trial(user.id)
        if pending is None or pending["trial_kind"] != "apotheosis":
            await interaction.response.send_message(
                embed=persona.error_embed("That one has not initiated an Apotheosis."),
                ephemeral=True,
            )
            return
        if row["pathway"] is None or int(row["sequence"]) != 1:
            await interaction.response.send_message(
                embed=persona.error_embed("Only a Sequence 1 King of Angels may be crowned."),
                ephemeral=True,
            )
            return
        key = row["pathway"]
        if self.db.get_god(key) is not None:
            await interaction.response.send_message(
                embed=persona.error_embed("A Sequence 0 already rules that Pathway."),
                ephemeral=True,
            )
            return
        if self.db.count_item(user.id, uniqueness_key(key)) < 1:
            await interaction.response.send_message(
                embed=persona.error_embed("They do not hold the Pathway's Uniqueness."),
                ephemeral=True,
            )
            return

        char_key = ingredients.characteristic_key(key, 1)
        if self.db.count_item(user.id, char_key) < 3:
            await interaction.response.send_message(
                embed=persona.error_embed("Apotheosis requires 3× Sequence 1 Characteristics."),
                ephemeral=True,
            )
            return

        # Check tarot coins, sanity, corruption requirements for Seq 0:
        if int(row.get("tarot_coins", 0)) < 25:
            await interaction.response.send_message(
                embed=persona.error_embed("Apotheosis requires 25 Tarot Coins."),
                ephemeral=True,
            )
            return
        if float(row["sanity"]) < 90.0:
            await interaction.response.send_message(
                embed=persona.error_embed("Apotheosis demands Sanity ≥ 90%."),
                ephemeral=True,
            )
            return
        if float(row["corruption"]) > 10.0:
            await interaction.response.send_message(
                embed=persona.error_embed("Apotheosis demands Corruption ≤ 10%."),
                ephemeral=True,
            )
            return

        # Consume resources
        self.db.add_tarot(user.id, -25)
        self.db.remove_item(user.id, uniqueness_key(key), 1)
        self.db.remove_item(user.id, char_key, 3)

        self.db.clear_trial(user.id)
        self.db.set_sequence(user.id, key, 0)
        role, error_diag = await sync_beyonder_role(
            self.db, user, key, 0, guild=interaction.guild
        )
        self.db.set_god(key, user.id)

        embed = persona.success_embed(
            "Apotheosis Complete",
            f"**{user.display_name}** has ascended! They are now **"
            f"{pathways.sequence_name(key, 0)}** — the True God of the "
            f"Path of **{pathways.get_pathway(key)['name']}**.",
        )
        if error_diag:
            embed.add_field(name="⚠️ Role Diagnostics", value=error_diag, inline=False)

        await interaction.response.send_message(embed=embed)

    # ======================================================================
    # MODERATOR
    # ======================================================================
    @moderator.command(name="warn")
    @app_commands.describe(user="Whom to issue a sanity warning to.")
    @checks.mod_only
    async def moderator_warn(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        """Issue a sanity warning (a small corruption spike)."""
        new_c = self.db.add_corruption(user.id, 10.0)
        await interaction.response.send_message(
            embed=persona.fog_embed(
                "Sanity Warning",
                f"**{user.display_name}** has drawn the fog's displeasure. "
                f"Corruption rises to {new_c:.1f}%.",
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))

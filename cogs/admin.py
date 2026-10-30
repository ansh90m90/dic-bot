"""Divine Authority — `/creator`, `/angel`, and `/moderator` command groups."""
from __future__ import annotations

import random
import time

import discord
from discord import app_commands
from discord.ext import commands

import config
from data import ingredients, pathways
from data.artifacts import get_artifact
from utils import checks, persona
from utils.roles import sync_beyonder_role
from db.database import Database
from cogs.anomalies import EVENT_TYPES, trigger_anomaly
from cogs.apotheosis import uniqueness_key


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
        await sync_beyonder_role(self.db, user, key, seq)
        if seq == 0:
            self.db.set_god(key, user.id)
            self.db.add_item(user.id, uniqueness_key(key), 1)
        title = pathways.sequence_name(key, seq)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Divine Appointment",
                f"By the word of the one Above the Sequences, **{user.display_name}** is "
                f"now **{title}** (Sequence {seq}) upon the Path of "
                f"**{pathways.get_pathway(key)['name']}**.",
            )
        )

    @creator.command(name="artifact")
    @app_commands.describe(
        grade="Artifact grade (0 = divine, 3 = minor).",
        effect="The artifact's perk (e.g. 'Triples digestion').",
        target="Who receives the artifact (defaults to you).",
    )
    @checks.owner_only
    async def creator_artifact_spawn(
        self,
        interaction: discord.Interaction,
        grade: app_commands.Range[int, 0, 3],
        effect: str,
        target: discord.Member | None = None,
    ) -> None:
        """Create a new custom Sealed Artifact."""
        recipient = target or interaction.user
        artifact_id = f"CUSTOM-{random.randint(1000, 9999)}"
        curse = {
            0: "Drains 8 sanity per day; loss of control is inevitable without sealing.",
            1: "Drains 5 sanity per day.",
            2: "Drains 3 sanity per day.",
            3: "Drains 1 sanity per day.",
        }[grade]
        self.db.add_artifact(
            recipient.id, artifact_id, None, "Custom Sealed Artifact", grade, effect, curse
        )
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Artifact Forged",
                f"A new Sealed Artifact has manifested: `{artifact_id}`\n"
                f"**Grade:** {grade}  ·  **Perk:** {effect}  ·  **Curse:** {curse}\n"
                f"Bestowed upon **{recipient.display_name}**.",
            )
        )

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
        await sync_beyonder_role(self.db, user, key, 1)
        self.db.remove_item(user.id, uniqueness_key(key), 1)
        await interaction.response.send_message(
            embed=persona.fog_embed(
                "Uniqueness Stolen",
                f"The one Above the Sequences has torn the **Uniqueness of "
                f"{pathways.get_pathway(key)['name']}** from **{user.display_name}**, "
                f"casting them back to Sequence 1.",
            )
        )

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
        await sync_beyonder_role(self.db, user, key, seq)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Promotion",
                f"**{user.display_name}** is raised to **{pathways.sequence_name(key, seq)}** "
                f"(Sequence {seq}) upon the Path of **{pathways.get_pathway(key)['name']}**.",
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
                embed=persona.error_embed("Only a Sequence 1 may be crowned."),
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

        self.db.clear_trial(user.id)
        self.db.set_sequence(user.id, key, 0)
        await sync_beyonder_role(self.db, user, key, 0)
        self.db.set_god(key, user.id)
        self.db.remove_item(user.id, uniqueness_key(key), 1)
        await interaction.response.send_message(
            embed=persona.success_embed(
                "Apotheosis Complete",
                f"**{user.display_name}** has ascended. They are now **"
                f"{pathways.sequence_name(key, 0)}** — the one and only True God of the "
                f"Path of **{pathways.get_pathway(key)['name']}**.",
            )
        )

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

    @moderator.command(name="confiscate")
    @app_commands.describe(user="Whose artifact to confiscate.", artifact_id="The artifact's id.")
    @checks.mod_only
    async def moderator_confiscate(
        self, interaction: discord.Interaction, user: discord.Member, artifact_id: str
    ) -> None:
        """Confiscate a Grade 3 Sealed Artifact."""
        art = self.db.get_artifact(artifact_id)
        if art is None or int(art["owner_id"]) != user.id:
            await interaction.response.send_message(
                embed=persona.error_embed("That artifact does not belong to that member."),
                ephemeral=True,
            )
            return
        if int(art["grade"]) != 3:
            await interaction.response.send_message(
                embed=persona.error_embed("Moderators may only confiscate Grade 3 Artifacts."),
                ephemeral=True,
            )
            return
        if int(art["equipped"]):
            self.db.unequip_artifact(user.id)
        self.db.delete_artifact(artifact_id)
        await interaction.response.send_message(
            embed=persona.fog_embed(
                "Artifact Confiscated",
                f"The Grade 3 artifact **{art['name']}** (`{artifact_id}`) has been "
                f"confiscated from **{user.display_name}**.",
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))

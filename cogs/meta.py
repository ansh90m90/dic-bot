"""Meta commands: live `/settings` and auto-generated `/help`."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from settings import SCHEMA, settings
from utils import checks, persona


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
    async def _command_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice]:
        current = current.lower()
        names = [c.qualified_name for c in self._flatten()]
        return [app_commands.Choice(name=n, value=n) for n in names if current in n.lower()][:25]

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

    @app_commands.command(name="help")
    @app_commands.describe(command="A command to inspect, e.g. 'pathway choose'.")
    @app_commands.autocomplete(command=_command_autocomplete)
    async def help_cmd(
        self, interaction: discord.Interaction, command: str | None = None
    ) -> None:
        if command:
            await self._show_command(interaction, command)
        else:
            await self._show_index(interaction)

    async def _show_index(self, interaction: discord.Interaction) -> None:
        commands = self._flatten()
        groups = [
            c for c in commands
            if isinstance(c, app_commands.Group) and getattr(c, "parent", None) is None
        ]
        top = [
            c for c in commands
            if isinstance(c, app_commands.Command) and getattr(c, "parent", None) is None
        ]
        by_parent: dict[str, list] = {}
        for c in commands:
            parent = getattr(c, "parent", None)
            if parent is not None:
                by_parent.setdefault(parent.qualified_name, []).append(c)

        embed = persona.fog_embed(
            "The Fool's Attendant — Commands",
            "Use `/help <command>` for details and parameters.",
        )
        for g in groups:
            subs = by_parent.get(g.qualified_name, [])
            embed.add_field(
                name=g.qualified_name,
                value="\n".join(
                    f"`/{s.qualified_name}` — {s.description or ''}" for s in subs
                ),
                inline=False,
            )
        if top:
            embed.add_field(
                name="Commands",
                value="\n".join(
                    f"`/{c.qualified_name}` — {c.description or ''}" for c in top
                ),
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    async def _show_command(self, interaction: discord.Interaction, name: str) -> None:
        target = name.strip().lower()
        cmd = next(
            (c for c in self._flatten() if c.qualified_name.lower() == target), None
        )
        if cmd is None:
            await interaction.response.send_message(
                embed=persona.error_embed(f"No command named **{name}**."), ephemeral=True
            )
            return
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

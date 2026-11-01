"""Slash commands — the only way the bot is configured."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

import settings as store
from welcome import send_welcome

log = logging.getLogger("ovyx")

LABELS = {
    "welcome_channel_id": "Welcome channel",
    "goal": "Community goal",
    "brand_line": "Brand line",
    "title": "Title",
    "tagline": "Tagline",
    "card_title": "Card title",
    "card_footer": "Card footer",
    "flags": "Card flags",
    "verify_role_id": "Verify role",
    "tos_channel_id": "Rules channel",
    "verify_label": "Verify label",
    "read_label": "Rules label",
    "accent": "Accent",
    "card_top": "Card top",
    "card_bottom": "Card bottom",
    "border": "Border",
    "bar_track": "Bar track",
    "bar_fill": "Bar fill",
}


def is_staff(interaction: discord.Interaction) -> bool:
    """Manage Server, inside a guild."""
    return interaction.guild is not None and interaction.user.guild_permissions.manage_guild


async def _reply(interaction: discord.Interaction, **kwargs) -> None:
    """Respond ephemerally, whether or not the interaction was already deferred."""
    if interaction.response.is_done():
        await interaction.followup.send(**kwargs)
    else:
        await interaction.response.send_message(**kwargs)


async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.CheckFailure):
        await _reply(interaction, content="You need the **Manage Server** permission, in a server.", ephemeral=True)
        return
    log.error("command %s failed: %s", interaction.command, error, exc_info=error)
    await _reply(interaction, content="Something went wrong — check the bot logs.", ephemeral=True)


def _summary_embed(title: str, changed: dict[str, object], config: dict) -> discord.Embed:
    def render(key: str, value: object) -> str:
        if key in {"welcome_channel_id", "tos_channel_id"}:
            return f"<#{value}>"
        if key == "verify_role_id":
            return f"<@&{value}>"
        return str(value) if str(value) else "*(empty)*"

    embed = discord.Embed(title=title, color=store.color_int(config["theme"]["accent"]))
    embed.description = (
        "\n".join(f"**{LABELS.get(key, key)}** · {render(key, value)}" for key, value in changed.items())
        or "Nothing changed."
    )
    embed.set_footer(text="Run /settings to see the full configuration")
    return embed


async def _apply(interaction: discord.Interaction, title: str, **changes) -> None:
    try:
        config = store.update(**changes)
    except store.SettingsError as exc:
        await _reply(interaction, content=f"⚠️ {exc}", ephemeral=True)
        return

    shown = {key: value for key, value in changes.items() if value is not None}
    if theme := shown.pop("theme", None):
        shown.update(theme)
    await _reply(interaction, embed=_summary_embed(title, shown, config), ephemeral=True)


def register(tree: app_commands.CommandTree) -> None:
    """Attach every configuration command to the tree."""

    @tree.command(name="setup", description="Set the welcome channel and community goal")
    @app_commands.describe(channel="Channel that receives the welcome messages", goal="Member count that fills the bar")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.check(is_staff)
    async def setup(interaction: discord.Interaction, channel: discord.TextChannel, goal: int | None = None) -> None:
        if goal is not None and goal < 1:
            await _reply(interaction, content="⚠️ Goal must be 1 or higher.", ephemeral=True)
            return
        await _apply(interaction, "Welcome channel updated", welcome_channel_id=channel.id, goal=goal)

    @tree.command(name="brand", description="Edit the wording of the welcome message")
    @app_commands.describe(
        brand_line="Small line above the title",
        title="Big heading",
        tagline="Bold line under the greeting",
        card_title="Small heading inside the image card",
        card_footer="Footer inside the image card",
        flags="Country flags shown before MEMBER #",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.check(is_staff)
    async def brand(
        interaction: discord.Interaction,
        brand_line: str | None = None,
        title: str | None = None,
        tagline: str | None = None,
        card_title: str | None = None,
        card_footer: str | None = None,
        flags: str | None = None,
    ) -> None:
        await _apply(
            interaction,
            "Wording updated",
            brand_line=brand_line,
            title=title,
            tagline=tagline,
            card_title=card_title,
            card_footer=card_footer,
            flags=flags,
        )

    @tree.command(name="theme", description="Recolour the card and the message container")
    @app_commands.describe(
        accent="Container accent + avatar glow",
        card_top="Card background, top colour",
        card_bottom="Card background, bottom colour",
        border="Card border colour",
        bar_track="Progress bar background",
        bar_fill="Progress bar fill",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.check(is_staff)
    async def theme(
        interaction: discord.Interaction,
        accent: str | None = None,
        card_top: str | None = None,
        card_bottom: str | None = None,
        border: str | None = None,
        bar_track: str | None = None,
        bar_fill: str | None = None,
    ) -> None:
        palette = {
            key: value
            for key, value in {
                "accent": accent,
                "card_top": card_top,
                "card_bottom": card_bottom,
                "border": border,
                "bar_track": bar_track,
                "bar_fill": bar_fill,
            }.items()
            if value
        }
        await _apply(interaction, "Theme updated", theme=palette)

    @tree.command(name="links", description="Point Verify/Read at a role and a channel")
    @app_commands.describe(
        verify_role="Role mentioned after **Verify**",
        rules_channel="Channel mentioned after **Read**",
        verify_text="Text shown when no role is set",
        read_text="Text shown when no channel is set",
        clear="Remove the role and channel mentions",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.check(is_staff)
    async def links(
        interaction: discord.Interaction,
        verify_role: discord.Role | None = None,
        rules_channel: discord.TextChannel | None = None,
        verify_text: str | None = None,
        read_text: str | None = None,
        clear: bool = False,
    ) -> None:
        if clear:
            config = store.clear("verify_role_id", "tos_channel_id")
            await _reply(interaction, embed=_summary_embed("Links cleared", {}, config), ephemeral=True)
            return
        await _apply(
            interaction,
            "Links updated",
            verify_role_id=verify_role.id if verify_role else None,
            tos_channel_id=rules_channel.id if rules_channel else None,
            verify_label=verify_text,
            read_label=read_text,
        )

    @tree.command(name="preview", description="Post a dummy welcome message to test the current look")
    @app_commands.describe(name="Display name to render", position="Member number to show")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.check(is_staff)
    async def preview(
        interaction: discord.Interaction,
        name: str = "facae",
        position: int | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not isinstance(interaction.channel, discord.abc.Messageable):
            await interaction.followup.send("This channel cannot receive messages.", ephemeral=True)
            return
        try:
            message = await send_welcome(
                interaction.channel,
                display_name=name,
                mention=interaction.user.mention,
                position=position or interaction.guild.member_count or 1,
                created_at=interaction.user.created_at,
            )
        except discord.HTTPException as exc:
            await interaction.followup.send(f"Could not post here: {exc.text}", ephemeral=True)
            return
        await interaction.followup.send(f"Preview posted: {message.jump_url}", ephemeral=True)

    @tree.command(name="settings", description="Show the current welcome configuration")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.check(is_staff)
    async def show_settings(interaction: discord.Interaction) -> None:
        config = store.load()
        theme = config["theme"]
        verify = f"<@&{config['verify_role_id']}>" if config["verify_role_id"] else f"`{config['verify_label']}`"
        rules = f"<#{config['tos_channel_id']}>" if config["tos_channel_id"] else f"`{config['read_label']}`"

        embed = discord.Embed(title="Welcome bot configuration", color=store.color_int(theme["accent"]))
        embed.add_field(
            name="Channel", value=f"<#{config['welcome_channel_id']}>" if config["welcome_channel_id"] else "not set"
        )
        embed.add_field(name="Goal", value=str(config["goal"]))
        embed.add_field(name="Flags", value=config["flags"] or "*(none)*")
        embed.add_field(name="Brand line", value=config["brand_line"] or "*(empty)*", inline=False)
        embed.add_field(name="Title", value=config["title"] or "*(empty)*", inline=False)
        embed.add_field(name="Tagline", value=config["tagline"] or "*(empty)*", inline=False)
        embed.add_field(name="Card title", value=config["card_title"] or "*(empty)*")
        embed.add_field(name="Card footer", value=config["card_footer"] or "*(empty)*")
        embed.add_field(name="Verify / Read", value=f"{verify} · {rules}", inline=False)
        embed.add_field(
            name="Palette",
            value="\n".join(f"`{name}` {value}" for name, value in theme.items()),
            inline=False,
        )
        embed.set_footer(text="Change anything with /setup /brand /theme /links")
        await _reply(interaction, embed=embed, ephemeral=True)

    @tree.command(name="reset", description="Restore every default setting")
    @app_commands.describe(confirm="Must be true — this overwrites the current configuration")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.check(is_staff)
    async def reset_config(interaction: discord.Interaction, confirm: bool = False) -> None:
        if not confirm:
            await _reply(interaction, content="Add `confirm:True` to restore the defaults.", ephemeral=True)
            return
        config = store.reset()
        await _reply(interaction, embed=_summary_embed("Defaults restored", {}, config), ephemeral=True)

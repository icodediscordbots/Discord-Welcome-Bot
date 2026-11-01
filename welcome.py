from __future__ import annotations

import asyncio
import io
from datetime import datetime, timezone

import discord

import settings as settings_store
from render.card import render_avatar, render_card

BAR_SEGMENTS = 18
PARTIALS = "▏▎▍▌▋▊▉"


def progress_bar(position: int, goal: int, segments: int = BAR_SEGMENTS) -> str:
    ratio = 0.0 if goal <= 0 else max(0.0, min(1.0, position / goal))
    filled = ratio * segments
    full = int(filled)
    bar = "█" * full
    if full < segments:
        step = int(round((filled - full) * 8))
        if step:
            bar += PARTIALS[step - 1]
        bar += "░" * (segments - full - (1 if step else 0))
    return bar


def humanize_age(created_at: datetime) -> str:
    delta = datetime.now(timezone.utc) - created_at
    days = max(0, delta.days)
    for size, unit in ((365, "year"), (30, "month"), (1, "day")):
        if days >= size:
            value = days // size
            return f"{value} {unit}{'' if value == 1 else 's'}"
    hours = max(0, int(delta.total_seconds() // 3600))
    return f"{hours} hour{'' if hours == 1 else 's'}"


def _verify_target(config: dict) -> str:
    if config["verify_role_id"]:
        return f"<@&{config['verify_role_id']}>"
    return f"`{config['verify_label']}`"


def _tos_target(config: dict) -> str:
    if config["tos_channel_id"]:
        return f"<#{config['tos_channel_id']}>"
    return f"`{config['read_label']}`"


def _body(config: dict, display_name: str) -> str:
    lines = [f"**{display_name}** Welcome!", ""]
    if config["tagline"]:
        lines += [f"**{config['tagline']}**", ""]
    lines += [
        f"WE WELCOME YOU TO THE SERVER",
        f"**Read** Rules",
    ]
    return "\n".join(lines)


def _member_block(mention: str, position: int) -> str:
    return f"### Member\n{mention}\nPosition **#{position}**"


def _account_block(created_at: datetime) -> str:
    return (
        f"### Account\nCreated <t:{int(created_at.timestamp())}:R>\n"
        f"Age **{humanize_age(created_at)}**"
    )


def _road_block(position: int, goal: int) -> str:
    ratio = 0.0 if goal <= 0 else max(0.0, min(1.0, position / goal))
    return f"### Road to {goal} Members\n{progress_bar(position, goal)} **{round(ratio * 100)}%**"


def build_message(
    config: dict,
    *,
    display_name: str,
    mention: str,
    position: int,
    created_at: datetime,
    card_png: bytes,
    avatar_png: bytes,
) -> tuple[discord.ui.LayoutView, list[discord.File]]:
    """Assemble the layout view and the files it references."""
    blocks: list[discord.ui.Item] = []
    if config["brand_line"]:
        blocks.append(discord.ui.TextDisplay(f"-# {config['brand_line']}"))
    if config["title"]:
        blocks.append(
            discord.ui.Section(
                discord.ui.TextDisplay(f"# {config['title']}"),
                accessory=discord.ui.Thumbnail("attachment://avatar.png"),
            )
        )
    blocks += [
        discord.ui.TextDisplay(_body(config, display_name)),
        discord.ui.TextDisplay(_member_block(mention, position)),
        discord.ui.TextDisplay(_account_block(created_at)),
        discord.ui.TextDisplay(_road_block(position, config["goal"])),
    ]

    children: list[discord.ui.Item] = []
    for index, block in enumerate(blocks):
        if index:
            children.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        children.append(block)
    children.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    children.append(discord.ui.MediaGallery(discord.MediaGalleryItem("attachment://welcome.png")))

    container = discord.ui.Container(*children, accent_colour=settings_store.color_int(config["theme"]["accent"]))
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(container)

    files = [
        discord.File(io.BytesIO(avatar_png), "avatar.png"),
        discord.File(io.BytesIO(card_png), "welcome.png"),
    ]
    return view, files


async def send_welcome(
    channel: discord.abc.Messageable,
    *,
    display_name: str,
    mention: str,
    position: int,
    created_at: datetime,
    avatar_bytes: bytes | None = None,
) -> discord.Message:
    """Render and post the welcome message."""
    config = settings_store.load()

    card_png, avatar_png = await asyncio.gather(
        asyncio.to_thread(
            render_card,
            username=display_name,
            position=position,
            goal=config["goal"],
            avatar_bytes=avatar_bytes,
            flags=config["flags"],
            card_title=config["card_title"],
            footer=config["card_footer"],
            theme=config["theme"],
        ),
        asyncio.to_thread(
            render_avatar,
            avatar_bytes,
            display_name,
            config["theme"],
        ),
    )

    view, files = build_message(
        config,
        display_name=display_name,
        mention=mention,
        position=position,
        created_at=created_at,
        card_png=card_png,
        avatar_png=avatar_png,
    )
    return await channel.send(view=view, files=files)

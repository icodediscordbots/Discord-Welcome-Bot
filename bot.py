"""OVYX welcome bot — posts the configured welcome card when a member joins."""

from __future__ import annotations

import logging
import os

import discord
from dotenv import load_dotenv

import commands
import settings as store
from welcome import send_welcome

log = logging.getLogger("ovyx")
ROOT = os.path.dirname(os.path.abspath(__file__))


def load_token() -> str:
    """Read the bot token from .env — the only file-level setting."""
    load_dotenv(os.path.join(ROOT, ".env"))
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit("DISCORD_TOKEN is missing from .env")
    return token


def welcome_channel(guild: discord.Guild) -> discord.abc.GuildChannel | None:
    channel_id = store.load()["welcome_channel_id"]
    if channel_id and (channel := guild.get_channel(channel_id)):
        return channel
    return guild.system_channel


async def welcome_member(member: discord.Member) -> discord.Message | None:
    """Send the welcome message for a member; returns the posted message."""
    channel = welcome_channel(member.guild)
    if channel is None:
        log.warning("no welcome channel configured — run /setup in %s", member.guild.name)
        return None

    avatar = None
    try:
        avatar = await member.display_avatar.replace(size=512, format="png").read()
    except discord.HTTPException:
        log.warning("avatar fetch failed for %s, using initials", member.id)

    return await send_welcome(
        channel,
        display_name=member.display_name,
        mention=member.mention,
        position=member.guild.member_count or 1,
        created_at=member.created_at,
        avatar_bytes=avatar,
    )


class WelcomeBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        commands.register(self.tree)
        self.tree.on_error = commands.on_error
        async for guild in self.fetch_guilds():
            await self._sync(guild)

    async def _sync(self, guild: discord.Guild) -> None:
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self._sync(guild)

    async def on_ready(self) -> None:
        log.info("logged in as %s (%s) - %d guild(s)", self.user, self.user.id, len(self.guilds))
        if not store.load()["welcome_channel_id"]:
            for guild in self.guilds:
                log.warning("guild %s has no welcome channel — run /setup there", guild.name)

    async def on_member_join(self, member: discord.Member) -> None:
        try:
            message = await welcome_member(member)
        except discord.HTTPException:
            log.exception("failed to welcome %s", member.id)
            return
        if message is not None:
            log.info("welcomed %s as member #%s", member, member.guild.member_count)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    WelcomeBot().run(load_token(), log_handler=None)


if __name__ == "__main__":
    main()

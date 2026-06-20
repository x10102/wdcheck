# Builtins
from typing import cast
from logging import info, error
from datetime import datetime

# External
import discord

# Internal
from core.modulebase import ModuleBase
from core.singletons import config
from core.models import StarboardPinnedMessage
from utils.discordutils import get_message_url

class StarboardModule(ModuleBase):

    @staticmethod
    def env_override():
        return "disable_starboard"
    
    @staticmethod
    def name():
        return "Starboard"
    
    @staticmethod
    def config_required():
        return ['channels.starboard', 'channels.console', 'starboard.threshold', 'starboard.emoji']

    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot
        self.threshold: int = config.get_value('starboard.threshold')
        self.channel: int = config.get_value('channels.starboard')
        self.console: int = config.get_value('channels.console')
        self.excluded: set[int] = set(config.get('starboard.excluded_channels') or {})
        self.emoji: set[discord.PartialEmoji] = {discord.PartialEmoji.from_str(e) for e in config.get_value('starboard.emoji')}

    @ModuleBase.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Ignore emojis not used for stars, ignore the starboard channel and also all excluded channels
        if payload.emoji not in self.emoji:
            return
        if payload.channel_id == self.channel:
            return
        if payload.channel_id in self.excluded:
            return
        message_model: StarboardPinnedMessage = \
            StarboardPinnedMessage.get_or_create(message_id = payload.message_id,
                                                emoji = payload.emoji)[0]
        message_model.reaction_count += 1
        if message_model.pinned_at is not None:
            return
        if message_model.reaction_count < self.threshold:
            message_model.save()
            return
        message_model.pinned_at = datetime.now()
        message_model.save()
        channel = await self.bot.fetch_channel(payload.channel_id)
        starboard_channel = await self.bot.fetch_channel(self.channel)
        if not isinstance(channel, discord.TextChannel) or not isinstance(starboard_channel, discord.TextChannel):
            error(f"Attempted to fetch message from invalid channel type, channel ID is {payload.channel_id}")
            console = cast(discord.abc.Messageable, self.bot.get_channel(self.console))
            await console.send("Pokus o načtení špatného typu kanálu v on_raw_reaction_add (TOHLE JE DEFINITIVNĚ BUG)")
            return
        message = await channel.fetch_message(payload.message_id)

        star_embed = discord.Embed()
        star_embed.set_author(name=f"{message.author.display_name}", icon_url=message.author.display_avatar.url)
        star_embed.add_field(name="",
                             value=message.content,
                             inline=False)
        star_embed.add_field(name="", 
                             value=f"**[Skočit na zprávu]({get_message_url(message)})**",
                             inline=False)
        star_embed.set_footer(text=message.created_at.astimezone().strftime("%d.%m.%Y %H:%M:%S"))

        # We can only send a single image in an embed, so we loop over all of them and grab the first one
        if len(message.attachments) > 0:
            for att in message.attachments:
                # Just check the MIME type for 'image', discord doesn't directly tell us if the file is embedded as image
                if not att.content_type:
                    continue
                if att.content_type.startswith("image"):
                    star_embed.set_image(url=att.proxy_url)
                    break
                if att.content_type.startswith("video"):
                    star_embed.add_field(name="",
                                         value=f"{att.proxy_url}")
                    continue

        # Do the same for embeds
        if len(message.embeds) > 0:
            for embed in message.embeds:
                if embed.image:
                    star_embed.set_image(url=embed.image.proxy_url)
                    break
                if embed.thumbnail:
                    star_embed.set_image(url=embed.thumbnail.url)
                    break

        channel_and_count = f"**{self.threshold}x {payload.emoji} v <#{message.channel.id}>**"

        await starboard_channel.send(embed=star_embed, content=channel_and_count)

        
    @ModuleBase.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.emoji not in self.emoji:
            return
        if payload.channel_id == self.channel:
            return
        if payload.channel_id in self.excluded:
            return
        message_model: StarboardPinnedMessage | None = \
            StarboardPinnedMessage.get_or_none((StarboardPinnedMessage.message_id == payload.message_id)
                                                & (StarboardPinnedMessage.emoji == payload.emoji))
        if not message_model:
            return
        if message_model.reaction_count == 0:
            return
        message_model.reaction_count -= 1
        message_model.save()
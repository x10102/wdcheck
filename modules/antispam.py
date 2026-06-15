
from discord import Message
import discord
from logging import info, warning
from dataclasses import dataclass, field
from hashlib import blake2b
from datetime import datetime, timedelta
from typing import cast
import os
import random
import asyncio
import utils.discordutils as discordutils
from constants import TIMEOUTED_VERB
from enum import IntEnum
from core.exceptions import MissingConfigError

from core.modulebase import ModuleBase

from core.models import AntispamTriggerEvent, AntiSpamResolveAction, SpamAttachmentHash


class SpamReportField(IntEnum):
    USERNAME = 0
    USER_ID = 1
    MESSAGE_CONTENT = 2
    ATTACHMENT_COUNT = 3
    TIMESTAMP = 4
    ACTION = 5

@dataclass
class MessageContent:
    message_object: discord.Message = field(compare=False)
    text: str
    attachment_hashes: set[str]
    timestamp: datetime = field(compare=False)

class AntiSpamEventView(discord.ui.View):
    def __init__(self, muted_user: discord.Member, offending_message_list: set[discord.Message], event_record: AntispamTriggerEvent):
        super().__init__(timeout=None)
        self.muted_user: discord.Member = muted_user
        self.offending_messages: set[discord.Message] = offending_message_list
        self._event_record = event_record

    async def delete_messages(self):
        for msg in self.offending_messages:
            info(f"Deleting message ID {msg.id}")
            await msg.delete()

    async def resolve_interaction(self, interaction: discord.Interaction, new_action: str):
        discordutils.check_valid_interaction(interaction)
        assert interaction.user is not None
        assert interaction.message is not None

        embed = interaction.message.embeds[0]
        embed.add_field(name="Vyřešil/a",
                        value=interaction.user.display_name,
                        inline=False)
        
        new_action = f"~~{embed.fields[SpamReportField.ACTION].value}~~ {new_action}"
        embed.set_field_at(
            SpamReportField.ACTION,
            name="Akce",
            value=new_action,
            inline=False
        )
        embed.colour = discord.Color.brand_green()
        await interaction.response.edit_message(view=self, embed=embed)

        self._event_record.resolution_timestamp = datetime.now()
        self._event_record.resolving_user = discordutils.ensure_user(interaction.user)
        self._event_record.save()

    @discord.ui.button(label="Zrušit mute", row=0, style=discord.ButtonStyle.primary)
    async def first_button_callback(self, button, interaction: discord.Interaction):

        await self.muted_user.remove_timeout()

        info(f"Timeout canceled for {self.muted_user.name} (ID: {self.muted_user.id})")
        self.disable_all_items()

        self._event_record.moderator_action = AntiSpamResolveAction.UNMUTE

        await self.resolve_interaction(interaction, "Propuštěn zpět na server")

    @discord.ui.button(label="Smazat zprávy", row=0, style=discord.ButtonStyle.danger)
    async def second_button_callback(self, button, interaction: discord.Interaction):

        await self.delete_messages()

        info(f"Offending messages deleted for {self.muted_user.name} (ID: {self.muted_user.id})")
        self.disable_all_items()

        self._event_record.moderator_action = AntiSpamResolveAction.DELETE_MESSAGES

        await self.resolve_interaction(interaction, "Vymazán z historie")

    @discord.ui.button(label="Smazat + kick", row=0, style=discord.ButtonStyle.danger)
    async def third_button_callback(self, button, interaction: discord.Interaction):

        await self.delete_messages()
        await self.muted_user.kick(reason="Spam")
        self.disable_all_items()

        self._event_record.moderator_action = AntiSpamResolveAction.DELETE_AND_KICK

        info(f"Messages deleted and {self.muted_user.name} (ID: {self.muted_user.id}) kicked")
        await self.resolve_interaction(interaction, "Vyhostěn do dalekých krajin")
        

class AntispamModule(ModuleBase):

    @staticmethod
    def env_override():
        return "DISABLE_ANTISPAM"
    
    @staticmethod
    def name():
        return "AntiSpam"

    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot
        self.previous_messages: dict[int, MessageContent] = {}
        self.offending_messages: dict[int, set[discord.Message]] = {}
        self.repeat_counters: dict[int, int] = {}
        self.author_locks: dict[int, asyncio.Lock] = {}
        self.repeat_timeout = timedelta(minutes=int(os.environ.get("ANTISPAM_WINDOW_MINUTES", 5)))
        self.default_mute = timedelta(hours=int(os.environ.get("ANTISPAM_TIMEOUT_HOURS", 12)))
        self.spam_limit = int(os.environ.get("ANTISPAM_WINDOW_SIZE", 4))
        console_channel = os.environ.get("CONSOLE_CHANNEL")
        if not console_channel:
            raise MissingConfigError("No console channel set")
        self.console_channel = int(console_channel)

    def _lock_for_user(self, user_id: int) -> asyncio.Lock:
        lock = self.author_locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self.author_locks[user_id] = lock
        return lock

    async def notify_moderators(self, offending_message: discord.Message, event_record: AntispamTriggerEvent):
        message_author = offending_message.author
        console = cast(discord.abc.Messageable, self.bot.get_channel(self.console_channel))
        action_verb = random.choice(TIMEOUTED_VERB)

        embed = discord.Embed(title="Detekován spam!")

        embed.add_field(name="Jméno Uživatele",
                        value=str(message_author.name),
                        inline=False)
        embed.add_field(name="ID Uživatele",
                        value=str(message_author.id),
                        inline=False)
        embed.add_field(name="Obsah zprávy",
                        value=f"```\n{offending_message.content}\n```",
                        inline=False)
        embed.add_field(name="Počet příloh",
                        value=str(len(offending_message.attachments)),
                        inline=False)
        embed.add_field(name="Odesláno",
                        value=offending_message.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                        inline=False)
        embed.add_field(name="Akce",
                        value=f"{action_verb} na {self.default_mute.seconds // 3600} hodin",
                        inline=False)
        
        
        embed.colour = discord.Color.blue()
        
        if isinstance(message_author, discord.User):
            raise RuntimeError("Got User object where Member object was expected (PM interactions not supported)")


        await console.send(content=f"<@&{os.environ.get("ADMIN_ROLE_ID")}>",
                            embed=embed, 
                            view=AntiSpamEventView(message_author, self.offending_messages[offending_message.author.id], event_record))
        del self.offending_messages[offending_message.author.id]

    @staticmethod
    def __message_to_content(msg: discord.Message):
        return MessageContent(msg, msg.content, set(), msg.created_at)
    
    @staticmethod
    async def __hash_attachments(content: MessageContent):
        # No attachments, return
        if len(content.message_object.attachments) == 0:
            return content
        
        # Already hashed, return
        if len(content.attachment_hashes) > 0:
            return content
        
        for att in content.message_object.attachments:
            info(f"Processing attachment: {att.filename}")
            hasher = blake2b(digest_size=16)
            async for chunk in att.read_chunked(65536):
                hasher.update(chunk)
            content.attachment_hashes.add(hasher.hexdigest())

        return content

    @staticmethod
    def __attachments_match(first: MessageContent, other: MessageContent) -> bool:
        # Check that the count and sizes of attachments match
        if len(first.message_object.attachments) != len(other.message_object.attachments):
            return False
        return all([att_self.size == att_other.size 
                    for att_self, att_other 
                    in zip(first.message_object.attachments, other.message_object.attachments)])

    @ModuleBase.listener()
    async def on_message(self, message: Message):
        # Skip messages from bots and system
        if not message.author or message.author.bot:
            return
        
        async with self._lock_for_user(message.author.id):

            current_message = AntispamModule.__message_to_content(message)
            author = message.author.id

            # No recorded messages yet, record the author and return
            if author not in self.previous_messages:
                self.previous_messages[author] = current_message
                self.repeat_counters[author] = 0
                info(f"First message by {author}")
                return

            previous_message = self.previous_messages[author]

            # Previous message was too long ago or attachments/text don't match, reset the counter and return
            if message.created_at - previous_message.timestamp > self.repeat_timeout\
                or not AntispamModule.__attachments_match(previous_message, current_message)\
                or previous_message.text != current_message.text:
                self.repeat_counters[author] = 0
                self.previous_messages[author] = current_message
                if author in self.offending_messages:
                    del self.offending_messages[author]
                return
            
            await AntispamModule.__hash_attachments(current_message)
            await AntispamModule.__hash_attachments(previous_message)
            
            # Messages match and aren't too far apart, increment the counter
            if current_message == previous_message:
                info(f"Repeated message by {message.author.name} (ID: {message.author.id}), spam counter increased to {self.repeat_counters[author] + 1}")
                if author not in self.offending_messages:
                    self.offending_messages[author] = set()
                self.offending_messages[author].add(previous_message.message_object)
                self.offending_messages[author].add(current_message.message_object)
                self.repeat_counters[author] += 1

            # Store the current message so that the timestamps are correct
            self.previous_messages[author] = current_message
            
            if self.repeat_counters[author] >= self.spam_limit:
                self.repeat_counters[author] = 0
                await cast(discord.Member, message.author).timeout_for(self.default_mute)
                warning(f"Timing out {message.author.name} (ID: {message.author.id}) for {self.default_mute} hours")

                offending_user = discordutils.ensure_user(message.author)
                event_record = AntispamTriggerEvent.create(
                    event_timestamp = datetime.now(),
                    offending_user = offending_user,
                    muted_for = datetime.min + self.default_mute,
                    message_content = message.content,
                    attachment_count = len(message.attachments)
                )

                for idx, hash in enumerate(current_message.attachment_hashes):
                    SpamAttachmentHash.create(
                        hexdigest=hash,
                        filename=message.attachments[idx].filename,
                        event=event_record
                    )

                await self.notify_moderators(message, event_record)
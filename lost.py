# Builtins
from datetime import datetime, timedelta, tzinfo
from os import environ
from logging import info

# External
from discord.ext import tasks
from discord.ext.commands.cog import Cog
from discord.ext.commands import slash_command
import discord

# Internal
from constants import THE_NUMBERS
from discordutils import ensure_user
from models import LostCycle, LostCycleReset

# !WARNING: SHIT CODE AHEAD
# TODO: Refactor this sometime

class LostModule(Cog):

    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.iterations = 0
        self.channel_id = int(environ.get("LOST_CHANNEL_ID"))
        self.role_id = int(environ.get("LOST_ROLE_ID"))
        self.can_reset = False
        self.started_at = datetime.now()
        self.first_prompt_loop = True
        self.first_fail_loop = True
        self.loop_running = False
        self.current_cycle = None

    @tasks.loop(minutes=240)
    async def lost_failed(self):
        if self.first_fail_loop:
            self.first_fail_loop = False
            return
        
        info("Cycle failed")
        channel = self.bot.get_channel(self.channel_id)
        await channel.send(f"<@&{self.role_id}>\n```Zemřeli jste!\nCyklus začal: {self.started_at.strftime('%H:%M:%S %d/%m/%Y')}\nIterací před smrtí: {self.iterations}```")
        self.iterations = 0
        self.can_reset = False
        self.lost_prompt.stop()
        self.lost_failed.stop()

    @tasks.loop(minutes=235)
    async def lost_prompt(self):
        if self.first_prompt_loop:
            self.first_prompt_loop = False
            return
        channel = self.bot.get_channel(self.channel_id)
        await channel.send(f"<@&{self.role_id}> Je čas...")
        self.first_prompt_loop = True
        self.can_reset = True


    @slash_command(description="Start the cycle")
    async def start(self, ctx: discord.ApplicationContext):
        if self.loop_running:
            await ctx.respond("To určite vole")
            return
        info("Cycle started")
        await ctx.respond("So it begins...")
        self.can_reset = False
        self.iterations = 0
        self.started_at = datetime.now()
        self.first_prompt_loop = True
        self.first_fail_loop = True
        self.loop_running = True

        self.current_cycle = LostCycle()
        self.current_cycle.save()

        self.lost_prompt.start()
        self.lost_failed.start()

    @slash_command(description="Kolik zbývá času?")
    async def time(self, ctx: discord.ApplicationContext):
        if not self.loop_running:
            await ctx.respond("bruh")
            return
        await ctx.respond(f"Zbývá {(self.lost_prompt.next_iteration- datetime.now(self.lost_prompt.next_iteration.tzinfo)).total_seconds() / 60:.1f} minut")

    @slash_command(description="Zachraňte se")
    async def reset(self, ctx: discord.ApplicationContext, answer: discord.Option(str, required=True)):
        if not self.can_reset:
            await ctx.respond("Ještě ne...")
            return
        if answer != THE_NUMBERS:
            await ctx.respond("Špatně!")
            return
        else:
            info("Cycle reset")
            await ctx.respond("Přežijete... prozatím. See you in 4 hours <:koteseni:1354216680800391268>")
            self.can_reset = False
            self.iterations += 1
            self.first_fail_loop = True
            self.first_prompt_loop = True
            self.lost_failed.restart()
            self.lost_prompt.restart()
            responder = ensure_user(ctx.user)
            creset = LostCycleReset()
            creset.cycle = self.current_cycle
            creset.user = responder
            creset.save()


    
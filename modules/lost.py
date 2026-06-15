# Builtins
from datetime import datetime
from os import environ
from logging import info

# External
from discord.ext import tasks
from discord.ext.commands import slash_command
import discord

# Internal
from constants import THE_NUMBERS, KOTESENI
from utils.discordutils import ensure_user
from core.models import LostCycle, LostCycleReset
from core.exceptions import MissingConfigError

from core.modulebase import ModuleBase

# !WARNING: SHIT CODE AHEAD
# TODO: Refactor this sometime

class LostModule(ModuleBase):

    @staticmethod
    def env_override():
        return "DISABLE_LOST"
    
    @staticmethod
    def name():
        return "Lost"

    def __init__(self, bot: discord.Bot):
        channel_id = environ.get("LOST_CHANNEL_ID")
        role_id = environ.get("LOST_ROLE_ID")
        if not channel_id or not role_id:
            raise MissingConfigError("Channel or role ID not configured")
        self.bot: discord.Bot = bot
        self.iterations = 0
        self.channel_id = int(channel_id)
        self.role_id = int(role_id)
        self.can_reset = False
        self.started_at = datetime.now()
        self.first_prompt_loop = True
        self.first_fail_loop = True
        self.loop_running = False
        self.current_cycle: LostCycle | None = None
        self.resume_last = None
        last_cycle = LostCycle.select().order_by(LostCycle.id.desc()).first()
        # if last_cycle:
        #    lost_channel = bot.fetch_channel(self.channel_id)
        #    started_str = last_cycle.started.strftime('%H:%M:%S %d/%m/%Y')
        #    asyncio.run_coroutine_threadsafe(async lambda: await lost_channel.send(f"Hmmm... vypadá to, že bot měl výpadek. Cheems asi něco podělal. Při příštím startu budete pokračovat v cyklu začatém v {started_str}"), bot.loop)
            
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
        self.loop_running = False
        self.lost_prompt.cancel()
        self.lost_failed.cancel()
        self.current_cycle.ended = datetime.now()
        self.current_cycle.save()

    @tasks.loop(minutes=235)
    async def lost_prompt(self):
        # The task runs once immediately when scheduled
        # We don't want that, so just skip the first iteration with a flag
        # Way easier than digging around in the discord library code
        if self.first_prompt_loop:
            self.first_prompt_loop = False
            return
        channel = self.bot.get_channel(self.channel_id)
        await channel.send(f"<@&{self.role_id}> Je čas...")
        # No clue why we're setting that here it gets reset in reset() anyway
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
        assert self.lost_prompt.next_iteration is not None
        await ctx.respond(f"Zbývá {(self.lost_prompt.next_iteration- datetime.now(self.lost_prompt.next_iteration.tzinfo)).total_seconds() / 60:.1f} minut")

    @slash_command(description="Zachraňte se")
    @discord.option("answer", type=str)
    async def reset(self, ctx: discord.ApplicationContext, answer: str):
        if not self.can_reset:
            await ctx.respond("Ještě ne...")
            return
        if answer != THE_NUMBERS:
            await ctx.respond("Špatně!")
            return
        else:
            info("Cycle reset")
            await ctx.respond(F"Přežijete... prozatím. See you in 4 hours {KOTESENI}")
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


    
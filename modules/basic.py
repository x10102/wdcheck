from core.modulebase import ModuleBase
import discord
from discord.ext.commands import slash_command
from logging import critical, info
from core.models import WDApplication
from constants import PROGRAM_VERSION
import os

class BasicModule(ModuleBase):

    @staticmethod
    def env_override():
        return "DISABLE_BASIC"
    
    @staticmethod
    def name():
        return "Basic Commands"

    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    @discord.default_permissions(administrator=True)
    @slash_command(name="kill", description="Ukončí bota v případě že se zblázní")
    async def kill_process(self, ctx: discord.ApplicationContext):
        critical(f"Received emergency shutdown command from {ctx.user.name} ({ctx.user.id}), exiting immediately")
        await ctx.respond("i guess bro")
        await self.bot.close()
        exit(67)

    @discord.default_permissions(administrator=True)
    @slash_command(name="stats", description="Zobrazí statistiky")
    async def view_stats(self, ctx: discord.ApplicationContext):
        info(f"Sending stats as response to {ctx.user.name} ({ctx.user.id})")
        accepted_count = WDApplication.select().where(WDApplication.accepted).count()
        rejected_count = WDApplication.select().where(~WDApplication.accepted).count()
        external_count = WDApplication.select().where(WDApplication.resolved_externally).count()
        await ctx.respond(f"```WDCheck verze {PROGRAM_VERSION}\nPřijatých žádostí: {accepted_count}\nZamítnutých žádostí: {rejected_count}\nNezapočítaných žádostí: {external_count}```")

    @discord.default_permissions(administrator=True)
    @slash_command(name="ping", description="Mňau")
    async def ping(self, ctx: discord.ApplicationContext):
        info(f"Sending ping as response to {ctx.user.name} ({ctx.user.id})")
        await ctx.respond("🐈")

    @discord.default_permissions(administrator=True)
    @slash_command(name="synccommands", description="Synchronizuje příkazy s Discordem po aktualizaci, nepoužívat pokud nevíte co to znamená")
    async def cmd_sync(self, ctx: discord.ApplicationContext):
        info(f"Synchronizing commands at request of {ctx.user.name} ({ctx.user.id})")
        await self.bot.sync_commands()
        await ctx.respond("Synchronizace dokončena, pro použití nových příkazů restartujte Discord (CTRL+R)")

    @ModuleBase.listener()
    async def on_ready(self):
        info(f"{self.bot.user} is ready to go!")
        if(os.environ.get("SYNC_COMMANDS_ON_STARTUP", "false") == "true"):
            info("Syncing commands")
            await self.bot.sync_commands()
            channel = self.bot.get_channel(int(os.environ.get("CONSOLE_CHANNEL")))
            await channel.send("Nové příkazy synchronizovány s Discord bot API, Čýmsi nezapomeň upravit .env")
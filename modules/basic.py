from core.modulebase import ModuleBase
import discord
from discord.ext.commands import slash_command
from logging import critical, info
from core.models import WDApplication, AntispamTriggerEvent, LostCycle
from constants import PROGRAM_VERSION
from core.singletons import config


class BasicModule(ModuleBase):

    @staticmethod
    def env_override():
        return "disable_basic"
    
    @staticmethod
    def name():
        return "Basic Commands"
    
    @staticmethod
    def config_required():
        return ['channels.console']

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
        antispam_trigger_count = AntispamTriggerEvent.select().count()
        lost_cycle_count = LostCycle.select().count()
        stats_text = (f"```Monika.aic verze {PROGRAM_VERSION}\n"
                      f"Přijatých žádostí: {accepted_count}\n"
                      f"Zamítnutých žádostí: {rejected_count}\n"
                      f"Nezapočítaných žádostí: {external_count}\n"
                      f"Události detekce spamu: {antispam_trigger_count}\n"
                      f"Cykly ztraceného tlačítka: {lost_cycle_count}```")
        await ctx.respond(stats_text)

    @discord.default_permissions(administrator=True)
    @slash_command(name="config", description="Zobrazí konfiguraci")
    async def view_config(self, ctx: discord.ApplicationContext):
        # unnghhh I hate global state
        loaded_modules = self.bot.__getattribute__("loaded_modules")
        config_text = (f"Konfigurace Monika.aic verze {PROGRAM_VERSION}\n")
        # TODO: Finish this
        await ctx.respond("teehee :3")

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
        if(config.get("overrides.sync_commands_on_startup", "false") == "true"):
            info("Syncing commands")
            await self.bot.sync_commands()
            channel = self.bot.get_channel(int(config.get("channels.console")))
            await channel.send("Nové příkazy synchronizovány s Discord bot API, Čýmsi nezapomeň upravit .env")
import discord
import logging
import nest_asyncio # type: ignore[import-untyped]
from dotenv import load_dotenv
from logging import info, warning, critical
import os
from peewee import Model
from modules.lost import LostModule
from modules.antispam import AntispamModule
from core.exceptions import MissingConfigError
from modules.applications import WikidotApplicationsModule

from core.modulebase import ModuleBase

from core.models import LostCycle, LostCycleReset, database, WDApplication, User, AntispamTriggerEvent, SpamAttachmentHash

bot = discord.Bot(intents=discord.Intents.all())

PROGRAM_VERSION = "1.0.0"
LOAD_MODULES: list[type[ModuleBase]] = [LostModule, AntispamModule, WikidotApplicationsModule]
CREATE_MODELS: list[Model] = [User, WDApplication, LostCycle, LostCycleReset, AntispamTriggerEvent, SpamAttachmentHash]

# Set up the logging format and target
# Logs to stdout and "bot.log" by default
def setup_logger(filename="bot.log"):

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    log_format = '[%(levelname).1s][%(asctime)s] %(message)s'
    date_format = '%H-%M-%S %d-%m-%Y'

    formatter = logging.Formatter(log_format, datefmt=date_format)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

@discord.default_permissions(administrator=True)
@bot.slash_command(name="kill", description="Ukončí bota v případě že se zblázní")
async def kill_process(ctx: discord.ApplicationContext):
    critical(f"Received emergency shutdown command from {ctx.user.name} ({ctx.user.id}), exiting immediately")
    await ctx.respond("i guess bro")
    await bot.close()
    exit(67)

@discord.default_permissions(administrator=True)
@bot.slash_command(name="stats", description="Zobrazí statistiky")
async def view_stats(ctx: discord.ApplicationContext):
    info(f"Sending stats as response to {ctx.user.name} ({ctx.user.id})")
    accepted_count = WDApplication.select().where(WDApplication.accepted).count()
    rejected_count = WDApplication.select().where(~WDApplication.accepted).count()
    external_count = WDApplication.select().where(WDApplication.resolved_externally).count()
    await ctx.respond(f"```WDCheck verze {PROGRAM_VERSION}\nPřijatých žádostí: {accepted_count}\nZamítnutých žádostí: {rejected_count}\nNezapočítaných žádostí: {external_count}```")

@discord.default_permissions(administrator=True)
@bot.slash_command(name="ping", description="Mňau")
async def ping(ctx: discord.ApplicationContext):
    info(f"Sending ping as response to {ctx.user.name} ({ctx.user.id})")
    await ctx.respond("🐈")

@discord.default_permissions(administrator=True)
@bot.slash_command(name="synccommands", description="Synchronizuje příkazy s Discordem po aktualizaci, nepoužívat pokud nevíte co to znamená")
async def cmd_sync(ctx: discord.ApplicationContext):
    info(f"Synchronizing commands at request of {ctx.user.name} ({ctx.user.id})")
    await bot.sync_commands()
    await ctx.respond("Synchronizace dokončena, pro použití nových příkazů restartujte Discord (CTRL+R)")

@bot.event
async def on_ready():
    info(f"{bot.user} is ready to go!")
    if(os.environ.get("SYNC_COMMANDS_ON_STARTUP", "false") == "true"):
        info("Syncing commands")
        await bot.sync_commands()
        channel = bot.get_channel(int(os.environ.get("CONSOLE_CHANNEL")))
        await channel.send("Nové příkazy synchronizovány s Discord bot API, Čýmsi nezapomeň upravit .env")
        
if __name__ == "__main__":
    setup_logger(os.environ.get("LOG_FILE", "bot.log"))
    info("Logger initialized")
    info(f"Monika.aic version {PROGRAM_VERSION} starting")
    info("Applying nested asyncio patch")
    # This is needed for running the wikidot library alongside pycord as it uses its own asyncio loop
    nest_asyncio.apply()
    load_dotenv(override=True)
    info("Initializing database")
    database.init(os.environ.get("DB_FILE", "applications.db"))
    database.connect()
    database.create_tables(CREATE_MODELS)

    info("Loading modules")
    
    for module in LOAD_MODULES:
        if os.environ.get(module.env_override()) == 'true':
            info(f"Not loading module: {module.name()} - due to env override")
            continue
        try:
            bot.add_cog(module(bot))
            info(f"Loaded module: {module.name()}")
        except MissingConfigError:
            warning(f"Not loading module: {module.name()} - due to missing configuration")
        except Exception as e:
            warning(f"Error while loading module: {module.name()}: {str(e)}")
    
    token = os.environ.get("BOT_TOKEN")
    if not token:
        critical("Discord API token is missing, cannot continue")
        exit(2)

    bot.run(token)
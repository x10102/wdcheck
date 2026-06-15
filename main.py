# Builtins
import os

# External
from peewee import Model
from dotenv import load_dotenv
import logging
from logging import info, warning, critical
import nest_asyncio # type: ignore[import-untyped]
import discord

# Internal
from core.exceptions import MissingConfigError
from core.modulebase import ModuleBase
from constants import PROGRAM_VERSION
from core.models import LostCycle, LostCycleReset, database, WDApplication, User, AntispamTriggerEvent, SpamAttachmentHash

# Modules
from modules.basic import BasicModule
from modules.applications import WikidotApplicationsModule
from modules.lost import LostModule
from modules.antispam import AntispamModule

bot = discord.Bot(intents=discord.Intents.all())

LOAD_MODULES: list[type[ModuleBase]] = [BasicModule, LostModule, AntispamModule, WikidotApplicationsModule]
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
# Builtins
import os

# External
from peewee import Model
from dotenv import load_dotenv
import logging
from logging import info, warning, critical, error
import nest_asyncio # type: ignore[import-untyped]
import discord

# Internal
from core.exceptions import MissingConfigError
from core.modulebase import ModuleBase
from core.singletons import config
from constants import PROGRAM_VERSION
from core.models import LostCycle, LostCycleReset, database, WDApplication, User, AntispamTriggerEvent, SpamAttachmentHash, StarboardPinnedMessage

# Modules
from modules.basic import BasicModule
from modules.applications import WikidotApplicationsModule
from modules.lost import LostModule
from modules.antispam import AntispamModule
from modules.imagetools import ImageToolsModule
from modules.starboard import StarboardModule

bot = discord.Bot(intents=discord.Intents.all())

LOAD_MODULES: list[type[ModuleBase]] = [BasicModule, LostModule, AntispamModule, WikidotApplicationsModule, StarboardModule]
CREATE_MODELS: list[Model] = [User, WDApplication, LostCycle, LostCycleReset, AntispamTriggerEvent, SpamAttachmentHash, StarboardPinnedMessage]

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
    config.load_from_json()
    setup_logger(config.get("log_file", "bot.log"))
    info("Logger initialized")
    info(f"Monika.aic version {PROGRAM_VERSION} starting")
    info("Applying nested asyncio patch")
    # This is needed for running the wikidot library alongside pycord as it uses its own asyncio loop
    nest_asyncio.apply()
    
    info("Initializing database")
    database.init(config.get("db_file", "applications.db"))
    database.connect()
    database.create_tables(CREATE_MODELS)

    info("Loading modules")
    
    loaded = []

    overrides = config.scope("overrides")

    for module in LOAD_MODULES:
        if overrides.get(module.env_override()):
            info(f"Not loading module: {module.name()} - due to env override")
            continue
        missing_required = config.keys_missing(module.config_required())
        if len(missing_required) != 0:
            error(f"Not loading module {module.name()} - missing required keys: [{', '.join(missing_required)}]")
            continue
        try:
            bot.add_cog(module(bot))
            info(f"Loaded module: {module.name()}")
            loaded.append(module)
        except MissingConfigError:
            warning(f"Not loading module: {module.name()} - due to missing configuration")
        except Exception as e:
            warning(f"Error while loading module: {module.name()}: {str(e)}")

    setattr(bot, 'loaded_modules', loaded)

    token = config.get("bot_token")
    if not token:
        critical("Discord API token is missing, cannot continue")
        exit(2)

    bot.run(token)
import discord
import wikidot
import logging
import nest_asyncio
import random
from datetime import datetime
from dotenv import load_dotenv
from discord.ext import tasks
from logging import info, warning, debug, error, critical
import os
from lost import LostModule

from models import LostCycle, LostCycleReset, database, WDApplication, User
from constants import PM_VERB
from wdutils import *
from textutils import print_application_number
from discordutils import ensure_user

bot = discord.Bot()
PROGRAM_VERSION = "1.0.0"

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

def ensure_config():
    if not all([k in dict(os.environ) for k in ['WIKI_USER', 'WIKI_PASSWORD', 'WIKI_NAME', 'BOT_TOKEN', 'CONSOLE_CHANNEL']]):
        critical("Missing configuration values, exiting...")
        exit(-1)

class WDAppConfirmView(discord.ui.View):
    def __init__(self, application, record: WDApplication):
        self.application = application
        self.record = record
        super().__init__(timeout=None)

    @discord.ui.button(label="Přijmout", row=0, style=discord.ButtonStyle.success)
    async def first_button_callback(self, button, interaction: discord.Interaction):
        info(f"Application for {self.application.user.name} was accepted by {interaction.user.name} (ID: {interaction.user.id})")
        # Disable the buttons
        self.disable_all_items()
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.brand_green()
        embed.title = "Žádost přijata"
        await interaction.response.edit_message(view=self, embed=embed)
        self.record.accepted = True
        self.record.resolved = True
        self.record.resolved_at = datetime.now()
        self.record.resolved_externally = False
        self.record.resolved_by = ensure_user(interaction.user)
        self.record.save()
        # Need to do it this way because accepting the application outside of the original client context throws an error
        with wikidot.Client(username=os.environ.get("WIKI_USER"), password=os.environ.get("WIKI_PASSWORD")) as client:
            site = client.site.get(os.environ.get("WIKI_NAME"))
            for app in site.get_applications():
                if app.user.id == self.application.user.id:
                    wd_appl_action(self.application, site, ApplAction.ACCEPT)

    @discord.ui.button(label="Odmítnout", row=0, style=discord.ButtonStyle.danger)
    async def second_button_callback(self, button, interaction: discord.Interaction):
        # TODO: Add rejection reason
        # (Maybe not? The reason doesn't even seem to show in wikidot mail)
        info(f"Application for {self.application.user.name} was rejected by {interaction.user.name} (ID: {interaction.user.id})")
        self.disable_all_items()
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.brand_red()
        embed.title = "Žádost zamítnuta"
        await interaction.response.edit_message(view=self, embed=embed)
        await interaction.followup.send(f"Zamítnuto! Nezapomeňte uživateli *{random.choice(PM_VERB)}* a sdělit mu důvod!")
        self.record.accepted = False
        self.record.resolved = True
        self.record.resolved_at = datetime.now()
        self.record.resolved_externally = False
        self.record.resolved_by = ensure_user(interaction.user)
        self.record.save()
        with wikidot.Client(username=os.environ.get("WIKI_USER"), password=os.environ.get("WIKI_PASSWORD")) as client:
            site = client.site.get(os.environ.get("WIKI_NAME"))
            for app in site.get_applications():
                if app.user.id == self.application.user.id:
                    wd_appl_action(self.application, site, ApplAction.REJECT)

@bot.event
async def on_ready():
    info(f"{bot.user} is ready to go!")
    if not check_applications.is_running():
        info("Scheduled check task")
        check_applications.start()

@tasks.loop(minutes=30)
async def check_applications():
    info("Running check task")
    count = 0
    applications = list()
    with wikidot.Client(username=os.environ.get("WIKI_USER"), password=os.environ.get("WIKI_PASSWORD")) as client:

        channel = bot.get_channel(int(os.environ.get("CONSOLE_CHANNEL")))
        site = client.site.get(os.environ.get("WIKI_NAME"))
        applications = site.get_applications()

        for application in applications:
            if(WDApplication.select()
                .where((WDApplication.resolved == False) & (WDApplication.user_id == application.user.id))):
                info(f"Skipping application for {application.user.name} (already in progress)")
                continue # Application already in progress
            count += 1
            appl = WDApplication(user_id = application.user.id, username = application.user.name, unix_name = application.user.unix_name, text = application.text)
            info(f"New application recorded (User: {application.user})")
            appl.save()
            
            embed = discord.Embed(
                title="Žádost čeká na schválení",
                description=f"Od uživatele [{application.user.name}](https://www.wikidot.com/user:info/{application.user.unix_name})",
                color=discord.Colour.blurple(),
            )
            embed.add_field(name="Zpráva", value=f"```{application.text}```")
            await channel.send(embed=embed, view=WDAppConfirmView(application, appl))

        for unresolved in WDApplication.select().where(WDApplication.resolved == False):
            if not any([a.user.id == unresolved.user_id for a in applications]):
                unresolved.resolved = True
                unresolved.resolved_externally = True
                unresolved.accepted = None
                unresolved.save()
                
    return count

@discord.default_permissions(administrator=True)
@bot.slash_command(name="applications", description="Zobrazí čekající žádanky na Wikidotu")
async def view_applications(ctx: discord.ApplicationContext):
    new_count = await check_applications()
    await ctx.respond(f"{print_application_number(new_count)}", ephemeral=True)

@discord.default_permissions(administrator=True)
@bot.slash_command(name="stats", description="Zobrazí statistiky")
async def view_stats(ctx: discord.ApplicationContext):
    info(f"Sending stats as response to {ctx.user.name} ({ctx.user.id})")
    accepted_count = WDApplication.select().where(WDApplication.accepted == True).count()
    rejected_count = WDApplication.select().where(WDApplication.accepted == False).count()
    external_count = WDApplication.select().where(WDApplication.resolved_externally == True).count()
    await ctx.respond(f"```WDCheck verze {PROGRAM_VERSION}\nPřijatých žádostí: {accepted_count}\nZamítnutých žádostí: {rejected_count}\nNezapočítaných žádostí: {external_count}```")

@discord.default_permissions(administrator=True)
@bot.slash_command(name="ping", description="Mňau")
async def view_stats(ctx: discord.ApplicationContext):
    info(f"Sending ping as response to {ctx.user.name} ({ctx.user.id})")
    await ctx.respond("🐈")

if __name__ == "__main__":
    setup_logger(os.environ.get("LOG_FILE", "bot.log"))
    info("Logger initialized")
    info(f"WDCheck version {PROGRAM_VERSION} starting")
    info("Applying nested asyncio patch")
    # This is needed for running the wikidot library alongside pycord as it uses its own asyncio loop
    nest_asyncio.apply()
    load_dotenv(override=True)
    ensure_config()
    info("Initializing database")
    database.init(os.environ.get("DB_FILE", "applications.db"))
    database.connect()
    database.create_tables([User, WDApplication, LostCycle, LostCycleReset])
    bot.add_cog(LostModule(bot))
    bot.run(os.environ.get("BOT_TOKEN"))
import discord
import wikidot
import random

from discord.ext import tasks
from core.modulebase import ModuleBase
from logging import info, error
from core.models import WDApplication
from utils.discordutils import check_valid_interaction, ensure_user
from utils.textutils import print_application_number
from utils.wdutils import wd_appl_action, ApplAction
from datetime import datetime
from typing import cast

from constants import PM_VERB
from core.exceptions import MissingConfigError
from core.singletons import config

class WDAppConfirmView(discord.ui.View):
    def __init__(self, application, record: WDApplication, module: "WikidotApplicationsModule"):
        self.application = application
        self.record = record
        self.module = module
        super().__init__(timeout=None)

    @discord.ui.button(label="Přijmout", row=0, style=discord.ButtonStyle.success)
    async def first_button_callback(self, button, interaction: discord.Interaction):
        check_valid_interaction(interaction)
        assert interaction.user is not None
        assert interaction.message is not None

        info(f"Application for {self.application.user.name} was accepted by {interaction.user.name} (ID: {interaction.user.id})")
        # Disable the buttons
        self.disable_all_items()
        embed = interaction.message.embeds[0]
        embed.colour = discord.Color.brand_green()
        embed.title = "Žádost přijata"
        await interaction.response.edit_message(view=self, embed=embed)
        self.record.accepted = True
        self.record.resolved = True
        self.record.resolved_at = datetime.now()
        self.record.resolved_externally = False
        self.record.resolved_by = ensure_user(interaction.user)
        self.record.save()
        # Need to do it this way because accepting the application outside of the original client context throws an error
        with wikidot.Client(username=self.module.wiki_user, password=self.module.wiki_password) as client:
            site = client.site.get(self.module.wiki_name)
            for app in site.applications:
                if app.user.id == self.application.user.id:
                    wd_appl_action(self.application, site, ApplAction.ACCEPT)

    @discord.ui.button(label="Odmítnout", row=0, style=discord.ButtonStyle.danger)
    async def second_button_callback(self, button, interaction: discord.Interaction):
        check_valid_interaction(interaction)
        assert interaction.user is not None
        assert interaction.message is not None

        # TODO: Add rejection reason
        # (Maybe not? The reason doesn't even seem to show in wikidot mail)
        info(f"Application for {self.application.user.name} was rejected by {interaction.user.name} (ID: {interaction.user.id})")
        self.disable_all_items()
        embed = interaction.message.embeds[0]
        embed.colour = discord.Color.brand_red()
        embed.title = "Žádost zamítnuta"
        await interaction.response.edit_message(view=self, embed=embed)
        await interaction.followup.send(f"Zamítnuto! Nezapomeňte uživateli *{random.choice(PM_VERB)}* a sdělit mu důvod!")
        self.record.accepted = False
        self.record.resolved = True
        self.record.resolved_at = datetime.now()
        self.record.resolved_externally = False
        self.record.resolved_by = ensure_user(interaction.user)
        self.record.save()
        with wikidot.Client(username=self.module.wiki_user, password=self.module.wiki_password) as client:
            site = client.site.get(self.module.wiki_name)
            for app in site.applications:
                if app.user.id == self.application.user.id:
                    wd_appl_action(self.application, site, ApplAction.REJECT)

class WikidotApplicationsModule(ModuleBase):

    @staticmethod
    def env_override():
        return "DISABLE_APPLICATION_CHECK"
    
    @staticmethod
    def name():
        return "Wikidot Applications"

    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot
        console_channel = config.get("CONSOLE_CHANNEL")
        wiki_name = config.get("WIKI_NAME")
        wiki_user = config.get("WIKI_USER")
        wiki_password = config.get("WIKI_PASSWORD")

        if not all([console_channel, wiki_name, wiki_password, wiki_user]):
            raise MissingConfigError("Missing Wikidot config values")

        # Why do I even bother with fucking MyPy at this point
        # That thing is just so stupid
        # I should NOT have to cast() here
        # all() is such a simple built in function, a type checker used in a hundred trillion projects should understand it
        self.console_channel: int = int(cast(str, console_channel))
        self.wiki_name: str = cast(str, wiki_name)
        self.wiki_user: str = cast(str, wiki_user)
        self.wiki_password: str = cast(str, wiki_password)

    @ModuleBase.listener()
    async def on_ready(self):
        if not self.check_applications.is_running() \
            and config.get("DISABLE_APPLICATION_CHECK") != 'true':
            info("Scheduled check task")
            self.check_applications.start()
    
    @tasks.loop(minutes=30)
    async def check_applications(self):
        info("Running check task")
        count = 0
        applications = list()
        try:
            with wikidot.Client(username=self.wiki_user, password=self.wiki_password) as client:

                channel = self.bot.get_channel(self.console_channel)
                site = client.site.get(self.wiki_name)

                for application in site.applications:
                    if(WDApplication.select()
                        .where((~WDApplication.resolved) & (WDApplication.user_id == application.user.id))):
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

                for unresolved in WDApplication.select().where(~WDApplication.resolved):
                    if not any([a.user.id == unresolved.user_id for a in applications]):
                        unresolved.resolved = True
                        unresolved.resolved_externally = True
                        unresolved.accepted = None
                        unresolved.save()
        except Exception as e:
            error(f"Error encountered in check task: {str(e)}")
            channel = self.bot.get_channel(int(config.get("CONSOLE_CHANNEL")))
            await channel.send(content=f"Při stahování žádanek nastala chyba: {str(e)}")

        return count

    @discord.default_permissions(administrator=True)
    @discord.slash_command(name="applications", description="Zobrazí čekající žádanky na Wikidotu")
    async def view_applications(self, ctx: discord.ApplicationContext):
        await ctx.interaction.response.defer()
        new_count = await self.check_applications()
        await ctx.interaction.followup.send(f"{print_application_number(new_count)}", ephemeral=True) 
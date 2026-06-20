import discord
import io
import os.path
from PIL import Image
from core.modulebase import ModuleBase
from logging import warning, info


class ImageToolsModule(ModuleBase):
    
    @staticmethod
    def env_override():
        return "DISABLE_IMAGE_PROCESSING"
    
    @staticmethod
    def name():
        return "Image processing"
    
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    @discord.message_command(name="Vytvořit GIF")
    async def make_gif(self, ctx: discord.ApplicationContext, message: discord.Message):
        if not message:
            warning("Context has empty message object, cannot complete command")
            await ctx.respond("neco se posralo srry")
            return
        if len(message.attachments) == 0:
            await ctx.respond("bro... ten obrazek mi musis dat... 💔")
            return
        image_att = message.attachments[0]
        info(f"Creating GIF from \"{image_att.filename}\" at request of {ctx.user.name} ({ctx.user.id})")
        bytestream = io.BytesIO(await image_att.read(use_cached=False))
        image = Image.open(bytestream)
        
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3]) 

        converted = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)

        output_bytestream = io.BytesIO()
        converted.save(output_bytestream, format="GIF")
        with open("a.gif", 'wb') as f:
            f.write(output_bytestream.read())
        response_filename = os.path.splitext(image_att.filename)[0]+".gif"
        response_attachment = discord.File(fp=output_bytestream, filename=response_filename)
        await ctx.respond(file=response_attachment)
import discord
from discord.ext import commands

class Extras(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
        if msg.guild is None:
            return
        if msg.channel.id == 905035677459161089:
            if len(msg.attachments) > 0:
                image_exist = [i for i in msg.attachments if "image/" in i.content_type]
                if image_exist:
                    if msg.content == "":
                        await msg.channel.send(f"Hey {msg.author.mention}, it's illegal to send an image here without a title or url!")
                        await msg.delete(delay=0.5)


async def setup(bot: commands.Bot) -> None:
    global Extras_Instance
    Extras_Instance = Extras(bot)
    await bot.add_cog(Extras_Instance, guilds=[discord.Object(id=887647011904557068)])

Extras_Instance : Extras
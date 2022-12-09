# bot.py
import os
import sys
import pytz, datetime
import gspread
from dotenv import load_dotenv

import discord
import discord.utils
from discord.ext import commands

import config
from config import Config, MAIN_PATH
from groups import Groups
import scheduler
import mongo
from mongo import MongoDB

from cogs.help import Help
from cogs.ppc import PPC
import cogs.ppc
from cogs.guild import PGR_Guild
import cogs.guild
from cogs.tht import THT
import cogs.tht
from cogs.utilities import Utilities
import cogs.utilities
from cogs.warzone import Warzone
import cogs.warzone

from utils.utils import ViewTimedOutError

def get_prefix(client, message):
    return Config.read_config(message.guild)["command_prefix"]

def get_tht_channels(client, message) -> dict:
    return Config.read_config(message.guild)["tht_channels"]

intents = discord.Intents.default()  # Allow the use of custom intents
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.remove_command('help')

@bot.event
async def on_ready():
    Config.check_folder()
    Groups.check_folder()
    mongo.Mongo_Instance = MongoDB(os.getenv('MONGODB_CONN'))
    mongo.Mongo_Instance.setup(bot.guilds)
    scheduler.run_scheduler(os.getenv('MONGODB_CONN'), bot.guilds)
    gc = gspread.service_account(filename=os.path.join(MAIN_PATH, 'service_account.json'))
    await add_cogs(gc)
    print(f'{bot.user} has connected to Discord on ' + str(len(bot.guilds)) + ' servers.')

@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            timezone = pytz.timezone("Asia/Jakarta")
            today = datetime.datetime.today().astimezone(timezone).strftime("%Y-%m-%d %H-%M-%S")
            f.write(f'{today} (UTC+7)\nUnhandled message: {event} {args[0]}\n{sys.exc_info()}\n')
            print('Error logged!')
        else:
            raise

@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot:
        return
    if msg.guild is None:
        return
    # try:
    #     if discord.utils.find(lambda m: m.id == bot.user.id, msg.mentions) != None:
    #         await msg.channel.send("Hi! My prefix for this server is *" + Config.read_config(msg.guild)["command_prefix"] +"*")
    # except:
    #     raise

    await bot.process_commands(msg)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.errors.CommandNotFound):
        return
    if isinstance(error, ViewTimedOutError):
        emb = discord.Embed(description="Timed out...", color=discord.Colour.red())
        await interaction.edit_original_response(embed=emb, view=None)
    else:
        raise
        #print(error)

def is_owner():
    def predicate(ctx: commands.Context):
        return ctx.author.id == 150826178842722304
    return commands.check(predicate)

@bot.command()
@is_owner()
async def reload(ctx: commands.Context, cog: str):
    if cog == 'reaction':
        await bot.reload_extension('cogs.reaction')
        await ctx.send(f"Cog '{cog}' reloaded.")
    else:
        await ctx.send("Available arguments: reaction")

@reload.error
async def reload_error(ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the reload command."""
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            await ctx.send("You have no permission to run this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Available arguments: reaction")

async def add_cogs(gc):
    cogs.utilities.Utilities_Instance = Utilities(bot)
    cogs.warzone.Warzone_Instance = Warzone(bot)
    cogs.tht.THT_Instance = THT(bot)
    cogs.guild.Guild_Instance = PGR_Guild(bot, gc)
    cogs.ppc.PPC_Instance = PPC(bot, gc)

    await bot.add_cog(Help(bot))
    await bot.add_cog(cogs.utilities.Utilities_Instance)
    await bot.add_cog(cogs.warzone.Warzone_Instance, guilds=[discord.Object(id=887647011904557068), discord.Object(id=487100763684864010)])
    await bot.add_cog(cogs.tht.THT_Instance, guilds=[discord.Object(id=887647011904557068), discord.Object(id=487100763684864010)])
    await bot.add_cog(cogs.guild.Guild_Instance, guilds=[discord.Object(id=887647011904557068), discord.Object(id=487100763684864010)])
    await bot.add_cog(cogs.ppc.PPC_Instance)

    await bot.load_extension('cogs.reaction')
    
# try:
#     bot.loop.create_task(scheduler.run_scheduler(os.getenv('MONGODB_CONN')))
#     bot.loop.run_until_complete(bot.start(TOKEN))
# except SystemExit:
#     pass
#     # handle_exit()
# except KeyboardInterrupt:
#     # handle_exit()
#     bot.loop.close()
#     print("Bot ended.")

if __name__ == "__main__":
    config.MAIN_PATH = os.path.dirname(os.path.realpath(__file__))

    load_dotenv(".env")
    TOKEN = os.getenv('DISCORD_TOKEN')

    bot.run(TOKEN)
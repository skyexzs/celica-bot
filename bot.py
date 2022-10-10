# bot.py
import os
import sys
import pytz, datetime
from dotenv import load_dotenv

import discord
import discord.utils
from discord.ext import commands

import config
from config import Config
from groups import Groups
import scheduler
import mongo
from mongo import MongoDB
import cogs.tht
from cogs.tht import THT
import cogs.utilities
from cogs.utilities import Utilities
import cogs.warzone
from cogs.warzone import Warzone

def get_prefix(client, message):
    return Config.read_config(message.guild)["command_prefix"]

def get_tht_channels(client, message) -> dict:
    return Config.read_config(message.guild)["tht_channels"]

intents = discord.Intents.default()  # Allow the use of custom intents
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

@bot.event
async def on_ready():
    await add_cogs()
    Config.check_folder()
    Groups.check_folder()
    mongo.Mongo_Instance = MongoDB(os.getenv('MONGODB_CONN'))
    mongo.Mongo_Instance.setup(bot.guilds)
    scheduler.run_scheduler(os.getenv('MONGODB_CONN'), bot.guilds)
    print(f'{bot.user} has connected to Discord on ' + str(len(bot.guilds)) + ' servers.')

@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            timezone = pytz.timezone("Asia/Jakarta")
            today = datetime.datetime.today().astimezone(timezone).strftime("%Y-%m-%d %H-%M-%S")
            f.write(f'{today} (UTC+7)\nUnhandled message: {event} {args[0]}\n{sys.exc_info()}\n')
        else:
            raise

@bot.event
async def on_message(msg: discord.Message):
    try:
        if not(msg.author.bot):
            if discord.utils.find(lambda m: m.id == bot.user.id, msg.mentions) != None:
                await msg.channel.send("Hi! My prefix for this server is *" + Config.read_config(msg.guild)["command_prefix"] +"*")
            await cogs.tht.on_tht_message_event(msg)
    except:
        pass

    await bot.process_commands(msg)

async def add_cogs():
    cogs.utilities.Utilities_Instance = Utilities(bot)
    cogs.warzone.Warzone_Instance = Warzone(bot)
    cogs.tht.THT_Instance = THT(bot)
    await bot.add_cog(cogs.utilities.Utilities_Instance)
    await bot.add_cog(cogs.warzone.Warzone_Instance)
    await bot.add_cog(cogs.tht.THT_Instance)

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
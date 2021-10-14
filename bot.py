# bot.py
import os

import discord
from discord import mentions
import discord.utils
from discord.message import Message
from discord.ext import commands
from dotenv import load_dotenv
import config
from config import Config

from cogs.utilities import Utilities
from cogs.warzone import Warzone

config.MAIN_PATH = os.path.dirname(os.path.realpath(__file__))

load_dotenv(".env")
TOKEN = os.getenv('DISCORD_TOKEN')

def get_prefix(client, message):
    return Config.read_config(message.guild)["command_prefix"]

bot = commands.Bot(command_prefix=get_prefix)

@bot.event
async def on_ready():
    add_cogs()
    Config.check_folder()
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise

@bot.event
async def on_message(msg):
    try:
        if not(msg.author.bot):
            if discord.utils.find(lambda m: m.id == bot.user.id, msg.mentions) != None:
                await msg.channel.send("Hi! My prefix for this server is *" + Config.read_config(msg.guild)["command_prefix"] +"*")
    except:
        pass

    await bot.process_commands(msg)

def add_cogs():
    bot.add_cog(Utilities(bot))
    bot.add_cog(Warzone(bot))

bot.run(TOKEN)
# bot.py
import os
import discord
import discord.utils
from discord.ext import commands
from dotenv import load_dotenv
import config
from config import Config
from groups import Groups
import scheduler

import cogs.utilities
from cogs.utilities import Utilities
import cogs.warzone
from cogs.warzone import Warzone

def get_prefix(client, message):
    return Config.read_config(message.guild)["command_prefix"]


intents = discord.Intents.default()  # Allow the use of custom intents
intents.members = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

@bot.event
async def on_ready():
    add_cogs()
    Config.check_folder()
    Groups.check_folder()
    scheduler.run_scheduler(os.getenv('MONGODB_CONN'), bot.guilds)
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
    #bot.add_cog(Utilities(bot))
    cogs.utilities.Utilities_Instance = Utilities(bot)
    cogs.warzone.Warzone_Instance = Warzone(bot)
    bot.add_cog(cogs.utilities.Utilities_Instance)
    bot.add_cog(cogs.warzone.Warzone_Instance)

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
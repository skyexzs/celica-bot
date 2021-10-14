from discord.ext import commands

import sys, os.path

import config
from config import Config

#sys.path.append(os.path.abspath('../'))
#import config
#from config import Config

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot;
    
    @commands.command()
    @commands.has_permissions(administrator = True)
    async def prefix(self, ctx, symbol: str):
        """Set prefix of the bot."""
        available_prefixes = ['!', '.', '#', '=', '-']
        if (len(symbol) == 1 and symbol in available_prefixes):
            data = Config.read_config(ctx.guild)
            data["command_prefix"] = symbol
            Config.write_config(ctx.guild, data)
            await ctx.send("> Command prefix has been set to " + symbol)
    
    @commands.command()
    async def test(self, ctx):
        await ctx.send(config.Config.read_config(ctx.guild))
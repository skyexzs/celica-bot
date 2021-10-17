import discord
from discord.ext import commands

import os.path

from config import MAIN_PATH, Config
from utils import utils as utl

available_prefixes = ['!', '.', '#', '=', '-']

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot;
    
    @commands.command(ignore_extra=False)
    @commands.has_permissions(administrator = True)
    async def prefix(self, ctx, symbol: str):
        """Set prefix of the bot."""
        if (len(symbol) == 1 and symbol in available_prefixes):
            data = Config.read_config(ctx.guild)
            data["command_prefix"] = symbol
            Config.write_config(ctx.guild, data)
            emb = utl.make_embed(desc="Command prefix has been set to " + symbol, color=discord.Colour.green())
            await utl.send_embed(ctx, emb);
        else:
            emb = utl.make_embed(desc="Please enter a symbol between " + str(available_prefixes), color=discord.Colour.green())
            await utl.send_embed(ctx, emb);

    @prefix.error
    async def prefix_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the prefix command."""
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.TooManyArguments):
            emb = utl.make_embed(desc="Please enter a symbol between " + str(available_prefixes), color=discord.Colour.green())
            await utl.send_embed(ctx, emb);
        elif isinstance(error, commands.MissingPermissions):
            pass
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("teams", error)
    
                
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            emb = utl.make_embed(desc="You do not have the permission to run this command.", color=discord.Colour.red())
            await utl.send_embed(ctx, emb)
        else:
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("COG_utilities", error)
import discord
from discord.colour import Color
from discord.ext import commands
from utils import utils as utl

import sys, os.path

import config
from config import MAIN_PATH, Config

class Warzone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot;
    
    @commands.command(aliases=['wz'])
    @commands.has_permissions(administrator = True)
    async def warzone(self, ctx, arg1: str, arg2: str):
        """Set prefix of the bot."""
        available_prefixes = ['!', '.', '#', '=', '-']
        pass
    
    def is_wzmaster():
        def predicate(ctx):
            return ctx.guild is not None #and ctx.author.roles[0]
        return commands.check(predicate)

    @commands.check_any(is_wzmaster(), commands.has_permissions(administrator = True))
    async def send_help(self, ctx):
        pass
    
    @commands.command()
    async def wzmaster(self, ctx, arg1: discord.Role):
        await ctx.send(type(arg1))
    
    @wzmaster.error
    async def wzmaster_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the wzmaster command."""
        emb = discord.Embed(title="Error!", description="Please enter a valid role.", color=discord.Colour.red())
        emb.add_field(name="Usage:", value=Config.read_config(ctx.guild)["command_prefix"]+"wzmaster @Role")

        if isinstance(error, commands.RoleNotFound):
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.MissingRequiredArgument):
            await utl.send_embed(ctx, emb)
        else:
            error_emb = discord.Embed(title="Error!", description="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("wzmaster", error)
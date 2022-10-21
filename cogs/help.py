import datetime

import discord
from discord.ext import commands

from config import Config

class Help(commands.Cog):
    """
    Sends this help message
    """

    def __init__(self, bot: commands.Bot):
        """! 
        Constructor
        @param bot The bot instance to be used.
        """
        self.bot = bot
    
    def is_gm(ctx: commands.Context):
        id = Config.read_config(ctx.guild)["gm_role"]
        return ctx.guild is not None and (discord.utils.find(lambda r: r.id == id, ctx.user.roles) is not None or ctx.channel.permissions_for(ctx.user).administrator == True)

    @commands.hybrid_command(name='help')
    async def help(self, ctx: commands.Context):
        # starting to build embed
        emb = discord.Embed(title='Help Commands :grey_question:', color=discord.Color.light_gray())
        
        icon = ''
        if ctx.guild.icon != None:
            icon = ctx.guild.icon.url

        emb.set_author(name=ctx.guild.name, icon_url=icon)
        emb.add_field(name=':mag_right:  **__Find__**', value="**/find <member>** : Find a member's UID\n**/find <uid>** : Find a member from a given UID", inline=False)
        emb.add_field(name='<:exaltair_Logo:937199287807377458> **__Guild__**', value="**/gb check** : Check your guild battle progress and warnings\n**/gb progress** : Check the weekly guild battle progress\n", inline=False)
        emb.add_field(name='<:EXPPC1:1031556662017921064> **__EX-PPC__**', value="**/exppc** : Check required score for achievement roles (EX-PPC)")
        emb.set_footer(text=self.bot.user, icon_url=self.bot.user.display_avatar.url)
        emb.timestamp = datetime.datetime.now()
        await ctx.send(embed=emb)
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
        """Get help."""
        # starting to build embed
        emb = discord.Embed(title='Help Commands :grey_question:', color=discord.Color.light_gray())

        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar.url)
        if ctx.guild.id == 887647011904557068:
            emb.add_field(name=':mag_right:  **__Find__**', value="**/find <member>** : Find a member's UID\n**/find <uid>** : Find a member from a given UID", inline=False)
            emb.add_field(name='<:exaltair_Logo:937199287807377458> **__Guild__**', value="**/gb check** : Check your guild battle progress and warnings\n**/gb progress** : Check the weekly guild battle progress\n", inline=False)
            emb.add_field(name='<:WeaponResoShard:1077144397306671165> **__Norman__**', value="**/norman remindme** : Set a reminder for Norman everyday for 2 days\n**/norman stop** : Stop the reminder", inline=False)
        emb.add_field(name='<:EXPPC1:1031556662017921064> **__EX-PPC__**', value="**/exppc** : Check maximum EX-PPC scores for this week\n**/boss** : Check individual bosses scores\n**/exppc_link** : Get the links for the spreadsheets")
        emb.set_footer(text='Made by Skye#2926', icon_url='https://cdn.discordapp.com/avatars/150826178842722304/a_ddc30804feb3e6c1ee942f9fc937d4fc.gif?size=1024')
        emb.timestamp = datetime.datetime.now()
        await ctx.send(embed=emb)
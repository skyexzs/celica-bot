import discord
from discord.ext import commands

import os.path

from config import MAIN_PATH, Config
from utils import utils as utl
import scheduler

available_prefixes = ['!', '.', '#', '=', '-']

async def send_ping(channel_id: int, member_id: int):
    channel = Utilities_Instance.bot.get_channel(channel_id)
    await channel.send(f"<@{member_id}>")

class Utilities(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(ignore_extra=False)
    @commands.has_permissions(administrator = True)
    async def prefix(self, ctx, symbol: str):
        """Set prefix of the bot."""
        if (len(symbol) == 1 and symbol in available_prefixes):
            data = Config.read_config(ctx.guild)
            data["command_prefix"] = symbol
            Config.write_config(ctx.guild, data)
            emb = utl.make_embed(desc="Command prefix has been set to " + symbol, color=discord.Colour.green())
            await utl.send_embed(ctx, emb)
        else:
            emb = utl.make_embed(desc="Please enter a symbol between " + str(available_prefixes), color=discord.Colour.green())
            await utl.send_embed(ctx, emb)

    @prefix.error
    async def prefix_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the prefix command."""
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.TooManyArguments):
            emb = utl.make_embed(desc="Please enter a symbol between " + str(available_prefixes), color=discord.Colour.green())
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.MissingPermissions):
            pass
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("teams", error)

    @commands.command(aliases=['lr'])
    @commands.has_permissions(manage_roles = True)
    async def listrole(self, ctx, *roles: discord.Role):
        """List members with the specified role."""
        if (len(roles) == 1):
            if roles[0] is ctx.guild.roles[0]:
                emb = utl.make_embed(desc="Cannot list everyone.", color=discord.Colour.red())
                await utl.send_embed(ctx, emb)
                return
            if roles[0] not in ctx.guild.roles:
                emb = utl.make_embed(desc="Invalid role.", color=discord.Colour.red())
                await utl.send_embed(ctx, emb)
                return
            else:
                role = discord.utils.find(lambda r: r == roles[0], ctx.guild.roles)
                members = ""
                for m in role.members:
                    members += f"\n<@{m.id}>"
                emb = utl.make_embed(desc=f"List of members with role <@&{roles[0].id}>:{members}\nTotal members: {len(role.members)}", color=discord.Colour.green())
                await utl.send_embed(ctx, emb)
                await ctx.send("```" + members + "\n```")
        else:
            m_list = []
            roles_str = ""
            for r in roles:
                if r is ctx.guild.roles[0] or r not in ctx.guild.roles:
                    continue
                elif r in ctx.guild.roles:
                    roles_str += f"<@&{r.id}>, "
                    role = discord.utils.find(lambda _r: _r == r, ctx.guild.roles)
                    if len(m_list) == 0:
                        for m in role.members:
                            m_list.append(m)
                    else:
                        m_list = list(filter(lambda m: m in role.members, m_list))
            members = ""
            for m in m_list:
                members += f"\n<@{m.id}>"
            emb = utl.make_embed(desc=f"List of members with role {roles_str[:-2]}:{members}\nTotal members: {len(m_list)}", color=discord.Colour.green())
            await utl.send_embed(ctx, emb)

    @listrole.error
    async def listrole_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the listrole command."""
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            pass
        elif isinstance(error, commands.MissingRequiredArgument):
            emb = utl.make_embed(desc="Missing argument in command.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}listrole @Role")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.RoleNotFound):
            emb = utl.make_embed(desc="Please enter a valid role.", color=discord.Colour.red())
            emb.add_field(name="Usage:", value=Config.read_config(ctx.guild)["command_prefix"]+"listrole @Role")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.BadArgument):
            emb = utl.make_embed(desc="Invalid argument in command.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}listrole @Role")
            await utl.send_embed(ctx, emb)
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("listrole", error)
    
    @commands.command()
    @commands.has_permissions(administrator = True)
    async def ping(self, ctx: commands.Context, member: discord.Member):
        """Ping someone every second."""
        if member is not None:
            scheduler.schdr.add_job(send_ping, 'interval', seconds=1, args=[ctx.channel.id, member.id], jobstore=str(ctx.guild.id), misfire_grace_time=300, id='ping', replace_existing=True)
        else:
            scheduler.schdr.remove_job(job_id='ping', jobstore=str(ctx.guild.id))
    
    @ping.error
    async def ping_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the ping command."""
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            pass
        elif isinstance(error, commands.MemberNotFound):
            emb = utl.make_embed(desc="Member not found.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}ping @user")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.MissingRequiredArgument):
            scheduler.schdr.remove_job(job_id='ping', jobstore=str(ctx.guild.id))
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("ping", error)
    
    @commands.command()
    async def sync(self, ctx: commands.Context):
        """Syncs application commands"""
        if ctx.author.id != 150826178842722304:
            raise commands.MissingPermissions
        await self.bot.tree.sync()#guild=discord.Object(id=ctx.guild.id))
        emb = utl.make_embed(desc="Syncing application commands.", color=discord.Colour.green())
        await utl.send_embed(ctx, emb)
    
    @sync.error
    async def sync_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the sync command."""
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            pass
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("sync", error)
        
    @commands.command()
    @commands.has_permissions(administrator = True)
    async def gsync(self, ctx: commands.Context):
        """Syncs application commands for guild"""
        if ctx.author.id != 150826178842722304:
            raise commands.MissingPermissions
        await self.bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
        emb = utl.make_embed(desc="Syncing application commands in guild.", color=discord.Colour.green())
        await utl.send_embed(ctx, emb)
    
    @gsync.error
    async def gsync_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the gsync command."""
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            pass
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("gsync", error)

    async def send_logs_to_test_server(message: str = None, emb: discord.Embed = None):
        guild = Utilities_Instance.bot.get_guild(487100763684864010)
        channel = guild.get_channel(1123649180611661925)
        if emb is not None:
            await channel.send(embed=emb)
        elif message is not None:
            await channel.send(message)
        else:
            pass
                
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            emb = utl.make_embed(desc="You do not have the permission to run this command.", color=discord.Colour.red())
            await utl.send_embed(ctx, emb)
        else:
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("COG_utilities", error)

Utilities_Instance : Utilities
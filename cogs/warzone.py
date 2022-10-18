import discord
from discord.ext import commands
from utils import utils as utl

import os.path
import datetime
import pytz
import random

from config import MAIN_PATH, Config
from groups import Groups
import scheduler

def check_if_grouping_available(guild_id: int):
    guild = Warzone_Instance.bot.get_guild(guild_id)
    id = Config.read_config(guild)["participant_role"]
    if guild.get_role(id) == None:
        return False
    else:
        role = guild.get_role(id)
        if len(role.members) < 3:
            return False
    return True

def create_groups(guild_id: int):
    guild = Warzone_Instance.bot.get_guild(guild_id)
    timezone = pytz.timezone("Asia/Jakarta")
    today = datetime.datetime.today().astimezone(timezone).strftime("%d-%m-%Y")
    id = Config.read_config(guild)["participant_role"]
    role = guild.get_role(id)
    Groups.write_default(guild, today)
    data = Groups.read_groups(guild, today)
    members = role.members.copy()
    total_groups = len(members) // 3
    for i in range(total_groups):
        chosen = []
        for i in range(3):
            r = random.choice(members)
            chosen.append({"id":r.id,"name":r.name})
            members.remove(r)
        data["groups"].append(chosen)
    for m in members:
        data["leftovers"].append({"id":m.id,"name":m.name})
    Groups.write_groups(guild, today, data)
    return data

def list_wz_jobs(guild: discord.Guild):
    if scheduler.schdr.get_job(job_id='wzscheduler1', jobstore=str(guild.id)) != None:
        jobslist = []
        jobslist.append(scheduler.schdr.get_job(job_id='wzscheduler1').id)
        jobslist.append(scheduler.schdr.get_job(job_id='wzscheduler2').id)
        return jobslist
    return None

async def send_wz_teams(guild_id: int, channel_id: int):
    guild = Warzone_Instance.bot.get_guild(guild_id)
    channel = guild.get_channel(channel_id)
    if not check_if_grouping_available(guild_id):
        emb = utl.make_embed(desc="Auto WZ Teams failed due to unavailable grouping.", color=discord.Colour.red())
        await channel.send(embed=emb)
    else:
        data = create_groups(guild_id)
        counter = 1
        groups = "Teams for next cycle:"
        for g in data["groups"]:
            groups += f"\nTeam {counter}: <@{g[0]['id']}> - <@{g[1]['id']}> - <@{g[2]['id']}>"
            counter += 1
        leftovers = ""
        if len(data["leftovers"]) > 0:
            leftovers += "\nLeftovers:"
            for l in data["leftovers"]:
                leftovers += f"\n<@{l['id']}>"

        await channel.send(groups+leftovers)

class Warzone(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_wzmaster():
        def predicate(ctx):
            id = Config.read_config(ctx.guild)["wzmaster_role"]
            return ctx.guild is not None and discord.utils.find(lambda r: r.id == id, ctx.author.roles) is not None
        return commands.check(predicate)
    
    def role_exist(self, ctx, id: int):
        if ctx.guild.get_role(id) == None:
            return False
        else:
            return True
    
    def validate_teams(self, ctx):
        teams = Config.read_config(ctx.guild)["teams"]
        for t in teams:
            if not self.role_exist(ctx, t):
                teams.remove(t)  
        Config.insert_config(ctx.guild, "teams", teams)

    async def clear_members_in_teams(self, ctx):
        self.validate_teams(ctx)
        teams = Config.read_config(ctx.guild)["teams"]
        for t in teams:
            role = ctx.guild.get_role(t)
            for m in role.members:
                await m.remove_roles(role, atomic=True)
    
    @commands.command(aliases=['g'])
    @commands.check_any(is_wzmaster(), commands.has_permissions(administrator=True))
    async def groups(self, ctx, mode: str, *, date: str = None):
        timezone = pytz.timezone("Asia/Jakarta")
        today = datetime.datetime.today().astimezone(timezone).strftime("%d-%m-%Y")
        if date == None:
            if mode == "create":
                id = Config.read_config(ctx.guild)["participant_role"]
                if not self.role_exist(ctx, id):
                    Config.insert_config(ctx.guild, "participant_role", 0)
                    emb = utl.make_embed(desc="Participant role is not yet set.", color=discord.Colour.red())
                    await utl.send_embed(ctx, emb)
                    return
                else:
                    role = ctx.guild.get_role(id)
                    Groups.write_default(ctx.guild, today)
                    data = Groups.read_groups(ctx.guild, today)
                    if len(role.members) < 3:
                        emb = utl.make_embed(desc=f"There are less than 3 participants in the role <@&{id}>.", color=discord.Colour.red())
                    else:
                        members = role.members.copy()
                        total_groups = len(members) // 3
                        for i in range(total_groups):
                            chosen = []
                            for i in range(3):
                                r = random.choice(members)
                                chosen.append({"id":r.id,"name":r.name})
                                members.remove(r)
                            data["groups"].append(chosen)
                        for m in members:
                            data["leftovers"].append({"id":m.id,"name":m.name})
                        Groups.write_groups(ctx.guild, today, data)
                        emb = utl.make_embed(desc=f"Finished creating a total of {total_groups} group(s) " +
                                                f"with {len(members)} leftover(s) on {data['created_on']}.\n" +
                                                f"To check groups, please type {Config.read_config(ctx.guild)['command_prefix']}groups check {today}",
                                                color=discord.Colour.green())
                    await utl.send_embed(ctx, emb)
            elif mode == "list":
                groups_list = Groups.list_groups(ctx.guild)
                groups_dt = []
                for g in groups_list:
                    g = g.replace(".json", "")
                    groups_dt.append(datetime.datetime.strptime(g, '%d-%m-%Y'))

                groups_dt.sort()

                text = ""
                for g in groups_dt:
                    g_str = g.strftime("%d-%m-%Y")
                    text += f"\n{g_str}"

                emb = utl.make_embed(desc=f"List of groups created:{text}", color=discord.Colour.green())
                await utl.send_embed(ctx, emb)
            elif mode == "reset":
                await self.clear_members_in_teams(ctx)
                emb = utl.make_embed(desc="Participants have been removed from all team channels.", color=discord.Colour.green())
                await utl.send_embed(ctx, emb)
            else:
                raise commands.BadArgument
        else:
            try:
                datetime.datetime.strptime(date, "%d-%m-%Y")
            except ValueError:
                emb = utl.make_embed(desc=f"Invalid date format. Please use dd-MM-YYYY format.", color=discord.Colour.red())
                await utl.send_embed(ctx, emb)
                return

            if mode == "check":
                data = Groups.read_groups(ctx.guild, date)
                
                if data == None:
                    emb = utl.make_embed(desc=f"There are no groups available on {date}", color=discord.Colour.red())
                    await utl.send_embed(ctx, emb)
                else:
                    """
                    groups = ""
                    for g in data["groups"]:
                        groups += f"\n<@{g[0]['id']}> <@{g[1]['id']}> <@{g[2]['id']}>"

                    leftovers = ""
                    if len(data["leftovers"]) > 0:
                        leftovers += "\nLeftovers:"
                        for l in data["leftovers"]:
                            leftovers += f"\n<@{l['id']}>"
                    
                    emb = utl.make_embed(desc=f"List of groups generated on {date}:{groups}{leftovers}", color=discord.Colour.green())
                    await utl.send_embed(ctx, emb)
                    """

                    counter = 1
                    groups = "```"
                    for g in data["groups"]:
                        groups += f"\nTeam {counter}: @{g[0]['name']} - @{g[1]['name']} - @{g[2]['name']}"
                        counter += 1
                    
                    leftovers = ""
                    if len(data["leftovers"]) > 0:
                        leftovers += "\nLeftovers:"
                        for l in data["leftovers"]:
                            leftovers += f"\n@{l['name']}"
                    
                    await ctx.send(groups+leftovers+"```")
                    
            elif mode == "assign":
                data = Groups.read_groups(ctx.guild, date)

                if data == None:
                    emb = utl.make_embed(desc=f"There are no groups available on {date}", color=discord.Colour.red())
                else:
                    groups = data["groups"]
                    teams = Config.read_config(ctx.guild)["teams"]
 
                    for t in teams:
                        if not self.role_exist(ctx, t):
                            teams.remove(t)  
                    Config.insert_config(ctx.guild, "teams", teams)

                    if (len(teams) < len(groups)):
                        emb = utl.make_embed(desc="Cannot assign groups into their roles because number of roles < number of groups.", color=discord.Colour.red())
                    else:
                        await self.clear_members_in_teams(ctx)
                        x = 0
                        for g in groups:
                            for m in g:
                                user = ctx.guild.get_member(m["id"])
                                if (user == None):
                                    await self.clear_members_in_teams(ctx)
                                    raise commands.UserNotFound(f"User {m['name']} with id {m['id']} could not be found in the server.")
                                else:
                                    await user.add_roles(ctx.guild.get_role(teams[x]), atomic=True)
                            x += 1

                        emb = utl.make_embed(desc="Successfully added participants to their individual channels.", color=discord.Colour.green())
                await utl.send_embed(ctx, emb)

            else:
                raise commands.BadArgument

    @groups.error
    async def groups_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the groups command."""
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            pass
        elif isinstance(error, commands.MissingRequiredArgument):
            emb = utl.make_embed(desc="Missing argument in command.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}groups [check/assign] (date)\n{pfx}groups [create/list/reset]")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.UserNotFound):
            emb = utl.make_embed(desc="One of the participants could not be found. Reverting role assignments.", color=discord.Colour.red())
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.BadArgument):
            emb = utl.make_embed(desc="Invalid argument in command.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}groups [check/assign] (date)\n{pfx}groups [create/list/reset]")
            await utl.send_embed(ctx, emb)
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("groups", error)
    
    @commands.command(aliases=['p'])
    @commands.check_any(is_wzmaster(), commands.has_permissions(administrator=True))
    async def participant(self, ctx, role: discord.Role):
        if role is ctx.guild.roles[0]:
            emb = utl.make_embed(desc="Participant role should not be set to everyone.", color=discord.Colour.red())
        else:
            Config.insert_config(ctx.guild, "participant_role", role.id)
            emb = utl.make_embed(desc="Participant role set to <@&" + str(role.id) + ">.", color=discord.Colour.green())
        await utl.send_embed(ctx, emb)

    @participant.error
    async def participant_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the participant command."""
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            pass
        elif isinstance(error, commands.RoleNotFound):
            emb = utl.make_embed(desc="Please enter a valid role.", color=discord.Colour.red())
            emb.add_field(name="Usage:", value=Config.read_config(ctx.guild)["command_prefix"]+"participant @Role")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.MissingRequiredArgument):
            try:
                id = Config.read_config(ctx.guild)["participant_role"]
            except KeyError:
                id = 0
            if (self.role_exist(ctx, id)):
                role = discord.utils.find(lambda r: r.id == id, ctx.guild.roles)
                amount = len(role.members)
                emb = utl.make_embed(desc="Participant role has been set to <@&" + str(id) + f">.\nAmount of participants: {amount}", color=discord.Colour.green())
            else:
                if (id > 0):
                    Config.insert_config(ctx.guild, "participant_role", 0)
                emb = utl.make_embed(desc="Participant role is not yet set.", color=discord.Colour.red())
            await utl.send_embed(ctx, emb)
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("participant", error)

    @commands.command(aliases=['t'])
    @commands.check_any(is_wzmaster(), commands.has_permissions(administrator=True))
    async def teams(self, ctx, mode: str, *, role: discord.Role = None):
        if role != None:
            if role is not None and role not in ctx.guild.roles:
                emb = utl.make_embed(desc="Invalid role.", color=discord.Colour.red())
                await utl.send_embed(ctx, emb)
                return
            if role is ctx.guild.roles[0]:
                emb = utl.make_embed(desc="Cannot use everyone in teams.", color=discord.Colour.red())
                await utl.send_embed(ctx, emb)
                return
            if mode == "add":
                data = Config.read_config(ctx.guild)
                if role.id in data["teams"]:
                    emb = utl.make_embed(desc="Team <@&" + str(role.id) + "> is already added.", color=discord.Colour.red())
                else:
                    data["teams"].append(role.id)
                    Config.write_config(ctx.guild, data)
                    emb = utl.make_embed(desc="Added <@&" + str(role.id) + "> to teams.", color=discord.Colour.green())
                await utl.send_embed(ctx, emb)
            elif mode == "remove":
                data = Config.read_config(ctx.guild)
                if role.id in data["teams"]:
                    data["teams"].remove(role.id)
                    Config.write_config(ctx.guild, data)
                    emb = utl.make_embed(desc="Removed <@&" + str(role.id) + "> to teams.", color=discord.Colour.green())
                else:
                    emb = utl.make_embed(desc="Team <@&" + str(role.id) + "> has not been added.", color=discord.Colour.red())
                await utl.send_embed(ctx, emb)
            else:
                raise commands.BadArgument
        else:
            if mode == "list":
                data = Config.read_config(ctx.guild)

                text = ""
                for t in data["teams"]:
                    if self.role_exist(ctx, t):
                        text += f"\n<@&{t}>"
                    else:
                        data["teams"].remove(t)
                
                amount = len(data["teams"])
                
                Config.write_config(ctx.guild, data)

                emb = utl.make_embed(desc=f"Total teams count: {amount}{text}", color=discord.Colour.green())
                await utl.send_embed(ctx, emb)
            else:
                raise commands.BadArgument
    
    @teams.error
    async def teams_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the teams command."""
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            pass
        elif isinstance(error, commands.RoleNotFound):
            emb = utl.make_embed(desc="Invalid role.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}teams [add/remove] @Role\n{pfx}teams list")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.MissingRequiredArgument):
            emb = utl.make_embed(desc="Missing argument in command.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}teams [add/remove] @Role\n{pfx}teams list")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.BadArgument):
            emb = utl.make_embed(desc="Invalid argument in command.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}teams [add/remove] @Role\n{pfx}teams list")
            await utl.send_embed(ctx, emb)
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("teams", error)
    
    @commands.command(aliases=['wzm'])
    @commands.has_permissions(administrator=True)
    async def wzmaster(self, ctx, role: discord.Role):
        if role is ctx.guild.roles[0]:
            emb = utl.make_embed(desc="WZMaster role should not be set to everyone.", color=discord.Colour.red())
        else:
            Config.insert_config(ctx.guild, "wzmaster_role", role.id) 
            emb = utl.make_embed(desc="WZMaster role set to <@&" + str(role.id) + ">.", color=discord.Colour.green())
        await utl.send_embed(ctx, emb)

    @wzmaster.error
    async def wzmaster_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the wzmaster command."""
        if isinstance(error, commands.MissingPermissions):
            pass
        elif isinstance(error, commands.RoleNotFound):
            emb = utl.make_embed(desc="Please enter a valid role.", color=discord.Colour.red())
            emb.add_field(name="Usage:", value=Config.read_config(ctx.guild)["command_prefix"]+"wzmaster @Role")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.MissingRequiredArgument):
            try:
                id = Config.read_config(ctx.guild)["wzmaster_role"]
            except KeyError:
                id = 0
            if (self.role_exist(ctx, id)):
                emb = utl.make_embed(desc="WZMaster role has been set to <@&" + str(id) + ">.", color=discord.Colour.green())
            else:
                Config.insert_config(ctx.guild, "wzmaster_role", 0)
                emb = utl.make_embed(desc="WZMaster role is not yet set.", color=discord.Colour.red())
            await utl.send_embed(ctx, emb)
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("wzmaster", error)
    
    @commands.command(aliases=['r'])
    @commands.check_any(is_wzmaster(), commands.has_permissions(administrator=True))
    async def random(self, ctx, date: str, num: int = 1):
        """Randomizer for WZ Giveaway winners based on cycle."""
        data = Groups.read_groups(ctx.guild, date)
        if data == None:
            emb = utl.make_embed(desc=f"There are no groups available on {date}", color=discord.Colour.red())
            await utl.send_embed(ctx, emb)
        else:
            if num > 0 and num <= sum([len(g) for g in data["groups"]]) + len(data["leftovers"]):
                list_of_names = []
                for g in data["groups"]:
                    list_of_names.append(g[0]['name'])
                    list_of_names.append(g[1]['name'])
                    list_of_names.append(g[2]['name'])
                for l in data["leftovers"]:
                    list_of_names.append(l['name'])
                
                chosen = ""
                for i in range(num):
                    r = random.choice(list_of_names)
                    chosen += f"\n@{r}"
                    list_of_names.remove(r)

                emb = utl.make_embed(desc=f"{num} random winners for the giveaway cycle {date}:{chosen}", color=discord.Colour.green())
                await utl.send_embed(ctx, emb)
            else:
                emb = utl.make_embed(desc=f"The amount of randoms requested is lower or greater than the amount of participants!", color=discord.Colour.red())
                await utl.send_embed(ctx, emb)

    @random.error
    async def random_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the random command."""
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            pass
        elif isinstance(error, commands.MissingRequiredArgument):
            emb = utl.make_embed(desc="Missing argument in command.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}random (date) (amount)")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.BadArgument):
            emb = utl.make_embed(desc="Invalid argument in command.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}random (date) (amount)")
            await utl.send_embed(ctx, emb)
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("random", error)

    @commands.command(aliases=['s'])
    @commands.has_permissions(administrator = True)
    async def scheduler(self, ctx: commands.Context, mode: str, *, channel: discord.TextChannel = None):
        """Scheduler for WZ Teams."""
        if channel != None:
            if channel is not None and channel not in ctx.guild.channels:
                emb = utl.make_embed(desc="Invalid channel.", color=discord.Colour.red())
                await utl.send_embed(ctx, emb)
                return
            if mode == "start":
                if not check_if_grouping_available(ctx.guild.id):
                    emb = utl.make_embed(desc="Unable to create scheduler due to unavailable grouping.", color=discord.Colour.red())
                    await utl.send_embed(ctx, emb)
                    return
                elif list_wz_jobs(ctx.guild) != None:
                    emb = utl.make_embed(desc="Unable to create schedulers because they already exist.", color=discord.Colour.red())
                    await utl.send_embed(ctx, emb)
                    return
                else:
                    scheduler.schdr.add_job(send_wz_teams, 'cron', day_of_week='sun', hour='20', minute='30', args=[ctx.guild.id, channel.id], jobstore=str(ctx.guild.id), misfire_grace_time=7200, id='wzscheduler1', replace_existing=True, max_instances=1000)
                    scheduler.schdr.add_job(send_wz_teams, 'cron', day_of_week='wed', hour='20', minute='30', args=[ctx.guild.id, channel.id], jobstore=str(ctx.guild.id), misfire_grace_time=7200, id='wzscheduler2', replace_existing=True, max_instances=1000)
                    emb = utl.make_embed(desc=f"Created 2 schedulers for Warzone in <#{channel.id}>.", color=discord.Colour.green())
                    await utl.send_embed(ctx, emb)
            else:
                raise commands.BadArgument
        else:
            if mode == "list":
                joblist = list_wz_jobs(ctx.guild)
                if joblist != None:
                    nl = '\n'
                    emb = utl.make_embed(desc=f"There are {len(joblist)} schedulers in this server:{nl}{nl.join(joblist)}", color=discord.Colour.green())
                    await utl.send_embed(ctx, emb)
                else:
                    emb = utl.make_embed(desc=f"There are no schedulers available on this server.", color=discord.Colour.red())
                    await utl.send_embed(ctx, emb)
            elif mode == "clear":
                joblist = list_wz_jobs(ctx.guild)
                if joblist != None:
                    for j in joblist:
                        scheduler.schdr.remove_job(job_id=j, jobstore=str(ctx.guild.id))
                    emb = utl.make_embed(desc=f"Cleared all WZ schedulers in this server.", color=discord.Colour.green())
                else:
                    emb = utl.make_embed(desc=f"There are no schedulers available on this server.", color=discord.Colour.red())
                await utl.send_embed(ctx, emb)
            else:
                raise commands.BadArgument
    
    @scheduler.error
    async def scheduler_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the scheduler command."""
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            pass
        elif isinstance(error, commands.MissingRequiredArgument):
            emb = utl.make_embed(desc="Missing argument in command.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}scheduler start (textchannel)\n{pfx}scheduler [list/clear]")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.BadArgument):
            emb = utl.make_embed(desc="Invalid argument in command.", color=discord.Colour.red())
            pfx = Config.read_config(ctx.guild)["command_prefix"]
            emb.add_field(name="Usage:", value=f"{pfx}scheduler start (textchannel)\n{pfx}scheduler [list/clear]")
            await utl.send_embed(ctx, emb)
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("scheduler", error)

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            emb = utl.make_embed(desc="You do not have the permission to run this command.", color=discord.Colour.red())
            await utl.send_embed(ctx, emb)
        elif hasattr(ctx.command, 'on_error'):
            return
        else:
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("COG_warzone", error)

Warzone_Instance : Warzone
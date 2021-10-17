from os import read
import discord
from discord.ext import commands
from utils import utils as utl

import os.path
import datetime
import random

from config import MAIN_PATH, Config
from groups import Groups

class Warzone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot;

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
        today = datetime.date.today().strftime("%d-%m-%Y")
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

                text = ""
                for g in groups_list:
                    g_str = g.replace(".json", "")
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
            id = Config.read_config(ctx.guild)["participant_role"]
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
            id = Config.read_config(ctx.guild)["wzmaster_role"]
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
            
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.CheckAnyFailure):
            emb = utl.make_embed(desc="You do not have the permission to run this command.", color=discord.Colour.red())
            await utl.send_embed(ctx, emb)
        elif hasattr(ctx.command, 'on_error'):
            return
        else:
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("COG_warzone", error)
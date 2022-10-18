import os
import re
from typing import Literal, Optional
import gspread
from gspread.exceptions import SpreadsheetNotFound
from gspread.exceptions import APIError

import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice

from utils import utils as utl
from utils.utils import ViewTimedOutError
from utils.models import Button_UI
from utils.models import Button_View
from config import Config
import scheduler
import mongo

"""
Special Cog for the Exaltair Guild
"""

def spreadsheet_not_found_embed():
    utl.make_embed(desc="Spreadsheet cannot be found.", color=discord.Colour.red())

def is_gm():
    def predicate(interaction: discord.Interaction) -> bool:
        id = Config.read_config(interaction.guild)["gm_role"]
        return interaction.guild is not None and (discord.utils.find(lambda r: r.id == id, interaction.user.roles) is not None or interaction.channel.permissions_for(interaction.user).administrator == True)
    return app_commands.check(predicate)

def role_exist(interaction: discord.Interaction, id: int):
    if interaction.guild.get_role(id) == None:
        return False
    else:
        return True

def name_sort(e):
    return e[1].lower()

class Confirm_Or_Cancel_View(Button_View):
    def __init__(self, timeout = 10):
        super().__init__(timeout)
        self.add_item(Button_UI('Confirm', discord.ButtonStyle.green))
        self.add_item(Button_UI('Cancel', discord.ButtonStyle.red))

    async def send(self, interaction: discord.Interaction, text: str):
        emb = utl.make_embed(desc=text, color=discord.Colour.yellow())
        await interaction.response.send_message(embed=emb, view=self, ephemeral=True)
    
    async def send_edit(self, interaction: discord.Interaction, text:str):
        emb = utl.make_embed(desc=text, color=discord.Colour.yellow())
        await interaction.edit_original_response(embed=emb, view=self)
    
    async def callback(self, interaction: discord.Interaction, label: str):
        if label == 'Cancel':
            await interaction.response.defer()
            self.stop()
            self.value = label
            emb = utl.make_embed(desc='Cancelled...', color=discord.Colour.red())
            await interaction.edit_original_response(embed=emb, view=None)
            return
        await super().callback(interaction, label)

class PGR_Guild(commands.Cog):
    def __init__(self, bot: commands.Bot, gc):
        self.bot = bot
        self.gc = gc

        self.main_data = None
        self.sub_data = None

        try:
            self.sh = self.gc.open_by_url(os.getenv('EXALTAIR_SPREADSHEET'))
            self.main_ws = self.sh.worksheet('Main')
            self.sub_ws = self.sh.worksheet('Sub')
            self.get_data('Main')
            self.get_data('Sub')
        except:
            raise

    def get_data(self, guild_type: str):
        if guild_type == 'Main':
            self.main_data = self.main_ws.batch_get(['B2:E81'])[0] # [0] for 1st range, if input is ('A1:A2','B1:B2') [0] is A1:A2, [1] is B1:B2
            self.main_data  = [x for x in self.main_data if x]
            self.main_data.sort(key=name_sort)
        else:
            self.sub_data = self.sub_ws.batch_get(['B2:E81'])[0]
            self.sub_data  = [x for x in self.sub_data if x]
            self.sub_data.sort(key=name_sort)

    async def add_member_to_guild(self, guild: Literal['Main', 'Sub'], member: discord.Member, uid: int):
        to_add = None
        if guild == 'Main':
            to_add = self.main_data
        else:
            to_add = self.sub_data
        to_add.append([str(member.id), str(member), str(uid)])
        to_add.sort(key=name_sort)
        await self.update_data(guild)
    
    async def remove_member_from_guild(self, guild: Literal['Main', 'Sub'], uid: int):
        if guild == 'Main':
            self.main_data = [x for x in self.main_data if x[2] != str(uid)]
            self.main_data.sort(key=name_sort)
        else:
            self.sub_data = [x for x in self.sub_data if x[2] != str(uid)]
            self.sub_data.sort(key=name_sort)
        await self.clear_data(guild)
        await self.update_data(guild)

    async def get_main_data(self):
        self.get_data('Main')

    async def get_sub_data(self):
        self.get_data('Sub')
    
    async def update_data(self, guild: Literal['Main', 'Sub']):
        if guild == 'Main':
            self.main_ws.batch_update([{
                'range': 'B2:E81',
                'values': self.main_data,
            }])
        else:
            self.sub_ws.batch_update([{
                'range': 'B2:E81',
                'values': self.sub_data,
            }])
            
    async def clear_data(self, guild: Literal['Main', 'Sub']):
        if guild == 'Main':
            self.main_ws.batch_clear(['B2:E81'])
        else:
            self.sub_ws.batch_clear(['B2:E81'])

    GM = app_commands.Group(name='gm', description='Commands to set Guild Manager', default_permissions=discord.Permissions(administrator=True))
    members = app_commands.Group(name='members', description='Commands to manage guild members', default_permissions=discord.Permissions(ban_members=True))

    @app_commands.command(name='link')
    @is_gm()
    async def link(self, interaction: discord.Interaction) -> None:
        """Get the link to the Exaltair spreadsheet"""
        url = os.getenv('EXALTAIR_SPREADSHEET')
        emb = discord.Embed(title='Exaltair Spreadsheet', url=url)
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @GM.command(name='set')
    @app_commands.describe(
        gm_role='Enter a role for guild manager',
        exaltairs_role='Enter the role for Exaltairs',
        main_role='Enter the role for Main Guild',
        sub_role='Enter the role for Sub Guild')
    async def gm_set(self, interaction: discord.Interaction, gm_role: discord.Role, exaltairs_role: discord.Role, main_role: discord.Role, sub_role: discord.Role) -> None:
        """Set the roles for Guild Management"""
        roles = [gm_role.id, exaltairs_role.id, main_role.id, sub_role.id]
        if interaction.guild.id in roles:
            emb = utl.make_embed(desc="Role should not be set to everyone.", color=discord.Colour.red())
        else:
            Config.insert_config(interaction.guild, "gm_role", gm_role.id)
            Config.insert_config(interaction.guild, "exaltairs_role", exaltairs_role.id)
            Config.insert_config(interaction.guild, "main_role", main_role.id)
            Config.insert_config(interaction.guild, "sub_role", sub_role.id)
            msg = f'Guild Manager role set to <@&{gm_role.id}>.\nExaltairs role set to <@&{exaltairs_role.id}>.\nMain Guild role set to <@&{main_role.id}>.\nSub Guild role set to <@&{sub_role.id}>.'
            emb = utl.make_embed(desc=msg, color=discord.Colour.green())
        await interaction.response.send_message(embed=emb)
    
    @GM.command(name='check')
    async def gm_check(self, interaction: discord.Interaction) -> None:
        """Check the roles set for Guild Management"""
        try:
            id = Config.read_config(interaction.guild)["gm_role"]
            id2 = Config.read_config(interaction.guild)["exaltairs_role"]
            id3 = Config.read_config(interaction.guild)["main_role"]
            id4 = Config.read_config(interaction.guild)["sub_role"]
        except KeyError:
            id = 0
            id2 = 0
            id3 = 0
            id4 = 0
        if (role_exist(interaction, id)):
            msg = f'Guild Manager role set to <@&{id}>.\nExaltairs role set to <@&{id2}>.\nMain Guild role set to <@&{id3}>.\nSub Guild role set to <@&{id4}>.'
            emb = utl.make_embed(desc=msg, color=discord.Colour.green())
        else:
            Config.insert_config(interaction.guild, "gm_role", 0)
            Config.insert_config(interaction.guild, "exaltairs_role", 0)
            Config.insert_config(interaction.guild, "main_role", 0)
            Config.insert_config(interaction.guild, "sub_role", 0)
            emb = utl.make_embed(desc="Guild Management roles are not yet set.", color=discord.Colour.red())
        await interaction.response.send_message(embed=emb)
    
    @members.command(name='add')
    @is_gm()
    @app_commands.describe(
        guild='Which guild to add member to?',
        member='The member to add',
        uid="The member's in-game UID (e.g 18612020)",
        add_roles="Add Exaltairs and Guild role to the new member? (default = False)")
    @app_commands.choices(guild=[
        Choice(name='Main', value=1),
        Choice(name='Sub', value=2)
    ])
    async def members_add(self, interaction: discord.Interaction, guild: Choice[int], member: discord.Member, uid: app_commands.Range[int, 10000000, 19999999], add_roles: Optional[bool] = False) -> None:
        """Adds a member to the guild"""
        # Not needed anymore due to app_commands.Range but leaving it here
        if re.match(r'^1[0-9]{7}$', str(uid)) == None:
            emb = utl.make_embed(desc="In-game UID is invalid. It must start with a 1 and be 8 numbers in length.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
        else:
            data = None
            if guild.name == 'Main':
                data = self.main_data
            else:
                data = self.sub_data
            
            if len(data) > 79:
                emb = utl.make_embed(desc=f":x: The {guild.name} guild is currently full!", color=discord.Colour.red())
                await interaction.response.send_message(embed=emb, ephemeral=True)
                return
            
            # If the UID is already in the records
            if any(str(uid) in x for x in data):
                emb = utl.make_embed(desc=f":x: There is already a member in {guild.name} guild with UID: {uid}.", color=discord.Colour.red())
                await interaction.response.send_message(embed=emb, ephemeral=True)
                return

            # If the member is not in the records yet
            if not any(str(member.id) in x for x in data):
                await self.add_member_to_guild(guild.name, member, uid)
                if add_roles:
                    try:
                        exaltairs = Config.read_config(interaction.guild)["exaltairs_role"]
                        main = Config.read_config(interaction.guild)["main_role"]
                        sub = Config.read_config(interaction.guild)["sub_role"]
                        
                        if guild.name == 'Main':
                            await member.add_roles(discord.Object(exaltairs), discord.Object(main))
                        else:
                            await member.add_roles(discord.Object(exaltairs), discord.Object(sub))
                    except KeyError:
                        pass
                emb = utl.make_embed(desc=f"Added <@{member.id}> (UID: {uid}) to {guild.name} guild.", color=discord.Colour.green())
                await interaction.response.send_message(embed=emb)
                return
            
            # If member is in the records but with a different UID (for members who play multiple accounts)
            records = [r for r in data if r[0] == (str(member.id))]
            uids = []
            for r in records:
                uids.append(r[2])
            confirm = Confirm_Or_Cancel_View(20)
            await confirm.send(interaction, f'<@{records[0][0]}> is already in {guild.name} guild with UID: {", ".join(uids)}\nDo you still want to add another record for <@{member.id}> with the UID: {uid}?')
            await confirm.wait()

            if confirm.value == None:
                raise ViewTimedOutError
            elif confirm.value == 'Confirm':
                await self.add_member_to_guild(guild.name, member, uid)
                emb = utl.make_embed(desc=f"Added <@{member.id}> (UID: {uid}) to {guild.name} guild.", color=discord.Colour.green())
                await interaction.edit_original_response(embed=emb, view=None)
                return
    
    @members.command(name='remove')
    @is_gm()
    @app_commands.describe(
        guild='Which guild to remove member from?',
        member='The member to remove',
        remove_roles="Remove Exaltairs and Guild role from the member? (default = False)")
    @app_commands.choices(guild=[
        Choice(name='Main', value=1),
        Choice(name='Sub', value=2)
    ])
    async def members_remove(self, interaction: discord.Interaction, guild: Choice[int], member: discord.Member, remove_roles: Optional[bool] = False) -> None:
        """Remove a member from the guild"""
        data = None
        if guild.name == 'Main':
            data = self.main_data
        else:
            data = self.sub_data

        # If member is not in the records yet
        if not any(str(member.id) in x for x in data):
            emb = utl.make_embed(desc=f"<@{member.id}> is not in {guild.name} guild.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return
        
        records = [m for m in data if m[0] == (str(member.id))]
        # If member has multiple ids
        if len(records) > 1:
            idview = Button_View(20)
            for r in records:
                idview.add_item(Button_UI(str(r[2]), discord.ButtonStyle.blurple))
            emb = utl.make_embed(desc='Which UID to remove from the member?', color=discord.Colour.yellow())
            await interaction.response.send_message(embed=emb, view=idview, ephemeral=True)
            await idview.wait()

            if idview.value == None:
                raise ViewTimedOutError
            else:
                await self.remove_member_from_guild(guild.name, int(idview.value))
                emb = utl.make_embed(desc=f"Removed <@{member.id}> (UID: {idview.value}) from {guild.name} guild.", color=discord.Colour.green())
                await interaction.edit_original_response(embed=emb, view=None)
                return
        
        # If member has only 1 id
        uid = records[0][2]
        await self.remove_member_from_guild(guild.name, int(uid))
        emb = utl.make_embed(desc=f"Removed <@{member.id}> (UID: {uid}) from {guild.name} guild.", color=discord.Colour.green())
        await interaction.response.send_message(embed=emb)
        return
    
    @members.command(name='removebyindex')
    @is_gm()
    @app_commands.describe(
        guild='Which guild to remove member from?',
        index='The index to remove')
    @app_commands.choices(guild=[
        Choice(name='Main', value=1),
        Choice(name='Sub', value=2)
    ])
    async def members_removebyindex(self, interaction: discord.Interaction, guild: Choice[int], index: app_commands.Range[int, 1, 80]) -> None:
        """Remove a member by index from the guild"""
        data = None
        if guild.name == 'Main':
            data = self.main_data
        else:
            data = self.sub_data

        # If index is out of bounds
        if index > len(data):
            emb = utl.make_embed(desc=f"Entered index is higher than the amount of members.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return
        
        # If index is below 1 BUT not needed anymore due to app_commands.Range
        if index < 1:
            emb = utl.make_embed(desc=f"Index cannot be zero or negative.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return
        
        # If member has only 1 id
        removed = data.pop(index-1)
        await self.clear_data(guild.name)
        await self.update_data(guild.name)
        emb = utl.make_embed(desc=f"Removed <@{removed[0]}> (UID: {removed[2]}) from {guild.name} guild.", color=discord.Colour.green())
        await interaction.response.send_message(embed=emb)
        return
    
    @members.command(name='list')
    @is_gm()
    async def members_list(self, interaction: discord.Interaction) -> None:
        """List members in the guild"""
        emb = discord.Embed(color=discord.Colour.blue())
        if interaction.guild.icon != None:
            emb.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
            emb.set_thumbnail(url=interaction.guild.icon.url)
        emb.add_field(name='Main', value=f"{len(self.main_data)}/80", inline=True)           
        emb.add_field(name='Sub', value=f"{len(self.sub_data)}/80", inline=True)

        show_button = Button_View()
        show_button.add_item(Button_UI('List Main', discord.ButtonStyle.blurple))
        show_button.add_item(Button_UI('List Sub', discord.ButtonStyle.blurple))
        
        await interaction.response.send_message(embed=emb, view=show_button)
        await show_button.wait()

        if show_button.value == None:
            return

        if show_button.value == 'List Main':
            mems = '\n'
            for i in range(len(self.main_data)):
                mems += f'\n<@{self.main_data[i][0]}> - {self.main_data[i][2]}'
            emb = utl.make_embed(title=f'List of Main members ({len(self.main_data)}/80):')
        elif show_button.value == 'List Sub':
            mems = '\n'
            for i in range(len(self.sub_data)):
                mems += f'\n<@{self.sub_data[i][0]}> - {self.sub_data[i][2]}'
            emb = utl.make_embed(title=f'List of Sub members ({len(self.sub_data)}/80):')
        emb.description = mems
        await interaction.edit_original_response(embed=emb, view=None)
    
    @members.command(name='edituid')
    @is_gm()
    @app_commands.describe(
        guild='Which guild to edit the member from?',
        member='The member to edit',
        uid="The member's new in-game UID (e.g 18612020)")
    @app_commands.choices(guild=[
        Choice(name='Main', value=1),
        Choice(name='Sub', value=2)
    ])
    async def members_edituid(self, interaction: discord.Interaction, guild: Choice[int], member: discord.Member, uid: app_commands.Range[int, 10000000, 19999999]):
        """Edit a member's UID"""
        data = None
        if guild.name == 'Main':
            data = self.main_data
        else:
            data = self.sub_data

        print(data)
        # If member is not in the records yet
        if not any(str(member.id) in x for x in data):
            emb = utl.make_embed(desc=f"<@{member.id}> is not in {guild.name} guild.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return
        
        # If the new UID is already in the records
        if any(str(uid) in x for x in data):
            emb = utl.make_embed(desc=f":x: There is already a member in {guild.name} guild with UID: {uid}.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return
        
        records = [m for m in data if m[0] == (str(member.id))]
        # If member has multiple ids
        if len(records) > 1:
            idview = Button_View(20)
            for r in records:
                idview.add_item(Button_UI(str(r[2]), discord.ButtonStyle.blurple))
            emb = utl.make_embed(desc='Which UID to change from the member?', color=discord.Colour.yellow())
            await interaction.response.send_message(embed=emb, view=idview, ephemeral=True)
            await idview.wait()

            if idview.value == None:
                raise ViewTimedOutError
            else:
                # Changing the real main/sub data
                for r in data:
                    if r[0] == str(member.id) and r[2] == str(idview.value):
                        r[2] = str(uid)
                await self.update_data(guild.name)
                emb = utl.make_embed(desc=f"Changed <@{member.id}>'s UID from {idview.value} to {uid} in {guild.name} guild.", color=discord.Colour.green())
                await interaction.edit_original_response(embed=emb, view=None)
                return
        
        # If member has only 1 id
        old_uid = records[0][2]
        # Changing the real main/sub data
        for r in data:
            if r[0] == str(member.id):
                r[2] = str(uid)
        await self.update_data(guild.name)
        emb = utl.make_embed(desc=f"Changed <@{member.id}>'s UID from {old_uid} to {uid} in {guild.name} guild.", color=discord.Colour.green())
        await interaction.response.send_message(embed=emb)
        return
    
    @members.command(name='nick')
    @is_gm()
    @app_commands.describe(
        guild='Which guild to nickname the member from?',
        member='The member to nickname',
        nickname="The member's nickname")
    @app_commands.choices(guild=[
        Choice(name='Main', value=1),
        Choice(name='Sub', value=2)
    ])
    async def members_nick(self, interaction: discord.Interaction, guild: Choice[int], member: discord.Member, nickname: str):
        """Set a nickname for the member"""
        data = None
        if guild.name == 'Main':
            data = self.main_data
        else:
            data = self.sub_data
        
        # If member is not in the records yet
        if not any(str(member.id) in x for x in data):
            emb = utl.make_embed(desc=f"<@{member.id}> is not in {guild.name} guild.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return
        
        records = [m for m in data if m[0] == (str(member.id))]
        # If member has multiple ids
        if len(records) > 1:
            idview = Button_View(20)
            for r in records:
                idview.add_item(Button_UI(str(r[2]), discord.ButtonStyle.blurple))
            emb = utl.make_embed(desc='Which UID of the member to add nickname to?', color=discord.Colour.yellow())
            await interaction.response.send_message(embed=emb, view=idview, ephemeral=True)
            await idview.wait()

            if idview.value == None:
                raise ViewTimedOutError
            else:
                # Changing the real main/sub data
                for r in data:
                    if r[0] == str(member.id) and r[2] == str(idview.value):
                        try:
                            r[3] = nickname
                        except IndexError:
                            r.append(nickname)
                await self.update_data(guild.name)
                emb = utl.make_embed(desc=f"Added nickname for <@{member.id}> in {guild.name} guild.", color=discord.Colour.green())
                await interaction.edit_original_response(embed=emb, view=None)
                return
        
        # If member has only 1 id
        # Changing the real main/sub data
        for r in data:
            if r[0] == str(member.id):
                try:
                    r[3] = nickname
                except IndexError:
                    r.append(nickname)
        await self.update_data(guild.name)
        emb = utl.make_embed(desc=f"Added nickname for <@{member.id}> in {guild.name} guild.", color=discord.Colour.green())
        await interaction.response.send_message(embed=emb)
        return
    
    @members.command(name='update')
    @is_gm()
    @app_commands.describe(guild='Which guild to update?')
    @app_commands.choices(guild=[
        Choice(name='Main', value=1),
        Choice(name='Sub', value=2)
    ])
    async def members_update(self, interaction: discord.Interaction, guild: Choice[int]) -> None:
        """Update the discord names of members in the guild"""
        data = None
        if guild.name == 'Main':
            data = self.main_data
        else:
            data = self.sub_data
        
        for r in data:
            r[1] = str(interaction.guild.get_member(int(r[0])))

        await self.update_data(guild.name)
        emb = utl.make_embed(desc=f"Updated the names for members in {guild.name} guild.", color=discord.Colour.green())
        await interaction.response.send_message(embed=emb)
    
    @app_commands.command(name='find')
    @app_commands.describe(member='The member to find')
    async def find(self, interaction: discord.Interaction, member: discord.Member) -> None:
        """Find a member in the guild"""
        id = str(member.id)
        uids = []
        guilds = []
        
        for r in self.main_data:
            if r[0] == id:
                uids.append(r[2])
                guilds.append('Main Guild')
        
        for r in self.sub_data:
            if r[0] == id:
                uids.append(r[2])
                guilds.append('Sub Guild')
        
        # If uid is not found
        if len(uids) == 0:
            emb = utl.make_embed(desc=f"Member <@{member.id}> cannot be found in both guilds.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb)
            return
        # If uid is found
        else:
            text = ''
            for i in range(len(uids)):
                text += f'{uids[i]} - {guilds[i]}\n'
            emb = utl.make_embed(title=f"Search results for {member} ({len(uids)} results):", desc=text, color=discord.Colour.green())
            await interaction.response.send_message(embed=emb)
            return
    
    @app_commands.command(name='find_by_uid')
    @app_commands.describe(uid='The UID to find')
    async def find_by_uid(self, interaction: discord.Interaction, uid: app_commands.Range[int, 10000000, 19999999]) -> None:
        """Find a member in the guild by its in-game UID"""
        uid = str(uid)
        members = []
        guilds = []
        
        for r in self.main_data:
            if r[2] == uid:
                members.append(r[0])
                guilds.append('Main Guild')
        
        for r in self.sub_data:
            if r[2] == uid:
                members.append(r[0])
                guilds.append('Sub Guild')
        
        # If member is not found
        if len(members) == 0:
            emb = utl.make_embed(desc=f"The UID: {uid} cannot be found in both guilds.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb)
            return
        # If member is found
        else:
            text = ''
            for i in range(len(members)):
                text += f'<@{members[i]}> - {guilds[i]}\n'
            
            if len(members) > 1:
                emb = utl.make_embed(title=f"Duplicate ID found for {uid}!", desc=text, color=discord.Colour.dark_red())
                emb.set_footer(text=f"There should only be 1 member with the UID {uid}!\nContact the guild management team to fix this.")
            else:
                emb = utl.make_embed(title=f"Match found!", desc=f'The UID: {uid} is owned by {members[0]} in {guilds[0]}', color=discord.Colour.green())
            await interaction.response.send_message(embed=emb)
            return

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CheckFailure):
            emb = utl.make_embed(desc="You do not have the permission to run this command.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)

Guild_Instance : PGR_Guild
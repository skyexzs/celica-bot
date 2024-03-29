import os
import re
import datetime
from typing import Literal, Optional
from gspread.utils import ValueRenderOption
from xlsxwriter.utility import xl_col_to_name
import aiohttp

import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice

from utils import utils as utl
from utils.utils import ViewTimedOutError
from utils.models import Button_UI
from utils.models import Button_View
import mongo
from config import Config
from bot import gc

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
    if interaction.guild.get_role(id) is None:
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
    def __init__(self, bot: commands.Bot):
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

    def clear_gb_data(self, ws, gb_dates):
        requests = {"requests": [
            {
                "repeatCell": {
                    "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}, "userEnteredValue": {"stringValue": ""}},
                    "range": {"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": 81, "startColumnIndex": 5, "endColumnIndex": 5+len(gb_dates)},
                    "fields": "*"
                }
            }
        ]}
        self.sh.batch_update(requests) # this is batch update function from spreadsheet not worksheet. it calls directly to google apis
    
    def get_data(self, guild_type: str):
        main_gb_dates = self.main_ws.row_values(1)[5:]
        sub_gb_dates = self.sub_ws.row_values(1)[5:]

        if guild_type == 'Main':
            end = xl_col_to_name(4+len(main_gb_dates)) + '81'
            self.main_data = self.main_ws.batch_get([f'B2:{end}'],value_render_option=ValueRenderOption.unformatted)[0] # [0] for 1st range, if input is ['A1:A2','B1:B2'] [0] is A1:A2, [1] is B1:B2
            self.main_data  = [x for x in self.main_data if x[0] != '']
            self.main_data.sort(key=name_sort)
        else:
            end = xl_col_to_name(4+len(sub_gb_dates)) + '81'
            self.sub_data = self.sub_ws.batch_get([f'B2:{end}'],value_render_option=ValueRenderOption.unformatted)[0]
            self.sub_data  = [x for x in self.sub_data if x[0] != '']
            self.sub_data.sort(key=name_sort)

    async def add_member_to_guild(self, guild: Literal['Main', 'Sub'], member: discord.Member, uid: int, data: list = None):
        to_add = None
        ws = None
        self.get_data(guild) # refresh the data before adding
        if guild == 'Main':
            to_add = self.main_data
            ws = self.main_ws
        else:
            to_add = self.sub_data
            ws = self.sub_ws
        if data is None:
            gb_dates = ws.row_values(1)[5:] # get amount of gb dates in the sheet
            new_mem = [str(member.id), str(member), str(uid), '']
            for i in gb_dates:
                new_mem.append('')
            to_add.append(new_mem)
            to_add.sort(key=name_sort)
        else:
            to_add.append(data.copy())
            to_add.sort(key=name_sort)
        await self.update_data(guild)

    async def remove_member_from_guild(self, guild: Literal['Main', 'Sub'], uid: int):
        self.get_data(guild) # refresh the data before removing
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
            gb_dates = self.main_ws.row_values(1)[5:]
            end = xl_col_to_name(4+len(gb_dates)) + '81'
            self.clear_gb_data(self.main_ws, gb_dates)
            self.main_ws.batch_update([{
                'range': f'B2:{end}',
                'values': self.main_data,
            }])
        else:
            gb_dates = self.sub_ws.row_values(1)[5:]
            end = xl_col_to_name(4+len(gb_dates)) + '81'
            self.clear_gb_data(self.sub_ws, gb_dates)
            self.sub_ws.batch_update([{
                'range': f'B2:{end}',
                'values': self.sub_data,
            }])
            
    async def clear_data(self, guild: Literal['Main', 'Sub']):
        if guild == 'Main':
            self.main_ws.batch_clear(['B2:E81'])
        else:
            self.sub_ws.batch_clear(['B2:E81'])

    GM = app_commands.Group(name='gm', description='Commands to set Guild Manager', default_permissions=discord.Permissions(administrator=True))
    members = app_commands.Group(name='members', description='Commands to manage guild members', default_permissions=discord.Permissions(ban_members=True))
    gb = app_commands.Group(name='gb', description='Commands to check guild battle progress')
    player = app_commands.Group(name='player', description="Command to find player")

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
        if re.match(r'^1[0-9]{7}$', str(uid)) is None:
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
            if any(str(uid) in x for x in self.main_data) or any(str(uid) in x for x in self.sub_data) :
                emb = utl.make_embed(desc=f":x: There is already a member in the guild with UID: {uid}.", color=discord.Colour.red())
                await interaction.response.send_message(embed=emb, ephemeral=True)
                return

            # If the member is not in the records yet
            if not any(str(member.id) in x for x in data):
                await interaction.response.defer()
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

                # Add to referral database
                query = { '_id': str(member.id) }
                to_add = {"$set": {"_id": str(member.id), "name": str(member), "created_at": member.created_at, "joined_at": member.joined_at, "referrer": "", "refers": []} }
                await mongo.Mongo_Instance.insert_data(interaction.guild, query, to_add, "memberdata")

                emb = utl.make_embed(desc=f"Added <@{member.id}> (UID: {uid}) to {guild.name} guild.", color=discord.Colour.green())
                await interaction.followup.send(embed=emb)
                return
            
            # If member is in the records but with a different UID (for members who play multiple accounts)
            records = [r for r in data if r[0] == (str(member.id))]
            uids = []
            for r in records:
                uids.append(r[2])
            confirm = Confirm_Or_Cancel_View(20)
            await confirm.send(interaction, f'<@{records[0][0]}> is already in {guild.name} guild with UID: {", ".join(uids)}\nDo you still want to add another record for <@{member.id}> with the UID: {uid}?')
            await confirm.wait()

            if confirm.value is None:
                raise ViewTimedOutError
            elif confirm.value == 'Confirm':
                await self.add_member_to_guild(guild.name, member, uid)
                emb = utl.make_embed(desc=f"Added <@{member.id}> (UID: {uid}) to {guild.name} guild.", color=discord.Colour.green())

                success = utl.make_embed(desc="Success!", color=discord.Colour.green())
                await interaction.edit_original_response(embed=success, view=None)
                await interaction.followup.send(embed=emb)
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

            if idview.value is None:
                raise ViewTimedOutError
            else:
                await self.remove_member_from_guild(guild.name, int(idview.value))
                emb = utl.make_embed(desc=f"Removed <@{member.id}> (UID: {idview.value}) from {guild.name} guild.", color=discord.Colour.green())
                
                success = utl.make_embed(desc="Success!", color=discord.Colour.green())
                await interaction.edit_original_response(embed=success, view=None)
                await interaction.followup.send(embed=emb)
                return
        
        # If member has only 1 id
        uid = records[0][2]
        await interaction.response.defer()
        await self.remove_member_from_guild(guild.name, int(uid))
        if remove_roles:
            try:
                exaltairs = Config.read_config(interaction.guild)["exaltairs_role"]
                main = Config.read_config(interaction.guild)["main_role"]
                sub = Config.read_config(interaction.guild)["sub_role"]
                
                if guild.name == 'Main':
                    await member.remove_roles(discord.Object(exaltairs), discord.Object(main))
                else:
                    await member.remove_roles(discord.Object(exaltairs), discord.Object(sub))
            except KeyError:
                pass
        emb = utl.make_embed(desc=f"Removed <@{member.id}> (UID: {uid}) from {guild.name} guild.", color=discord.Colour.green())
        await interaction.followup.send(embed=emb)
        return
    
    @members.command(name='transfer')
    @is_gm()
    @app_commands.describe(
        guild='Which guild to transfer member from?',
        member='The member to transfer',
        replace_roles="Replace (or add) Main/Sub guild role from the member? (default = False)")
    @app_commands.choices(guild=[
        Choice(name='Main', value=1),
        Choice(name='Sub', value=2)
    ])
    async def members_transfer(self, interaction: discord.Interaction, guild: Choice[int], member: discord.Member, replace_roles: Optional[bool] = False) -> None:
        """Remove a member from the guild"""
        data = None
        data_to = None
        guild_to = ''
        if guild.name == 'Main':
            data = self.main_data
            data_to = self.sub_data
            guild_to = 'Sub'
        else:
            data = self.sub_data
            data_to = self.main_data
            guild_to = 'Main'

        # If member is not in the records yet
        if not any(str(member.id) in x for x in data):
            emb = utl.make_embed(desc=f"<@{member.id}> is not in {guild.name} guild.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return
        
        if len(data_to) > 79:
            emb = utl.make_embed(desc=f":x: The {guild_to} guild is currently full!", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return

        records = [m for m in data if m[0] == (str(member.id))]
        # If member has multiple ids
        if len(records) > 1:
            idview = Button_View(20)
            for r in records:
                idview.add_item(Button_UI(str(r[2]), discord.ButtonStyle.blurple))
            emb = utl.make_embed(desc='Which UID to transfer from the member?', color=discord.Colour.yellow())
            await interaction.response.send_message(embed=emb, view=idview, ephemeral=True)
            await idview.wait()

            if idview.value is None:
                raise ViewTimedOutError
            else:
                member_data = [r for r in records if r[2] == idview.value]
                await self.add_member_to_guild(guild_to, member, int(idview.value), member_data)
                await self.remove_member_from_guild(guild.name, int(idview.value))

                if replace_roles:
                    try:
                        exaltairs = Config.read_config(interaction.guild)["exaltairs_role"]
                        main = Config.read_config(interaction.guild)["main_role"]
                        sub = Config.read_config(interaction.guild)["sub_role"]
                        
                        if guild.name == 'Main':
                            await member.add_roles(discord.Object(exaltairs), discord.Object(sub))
                        else:
                            await member.add_roles(discord.Object(exaltairs), discord.Object(main))
                    except KeyError:
                        pass
                emb = utl.make_embed(desc=f"Transferred <@{member.id}> (UID: {idview.value}) from **{guild.name}** guild to **{guild_to}** guild.", color=discord.Colour.green())
                
                success = utl.make_embed(desc="Success!", color=discord.Colour.green())
                await interaction.edit_original_response(embed=success, view=None)
                await interaction.followup.send(embed=emb)
                return
        
        # If member has only 1 id
        member_data = records[0]
        await interaction.response.defer()
        await self.add_member_to_guild(guild_to, member, int(member_data[2]), member_data)
        await self.remove_member_from_guild(guild.name, int(member_data[2]))
        if replace_roles:
            try:
                exaltairs = Config.read_config(interaction.guild)["exaltairs_role"]
                main = Config.read_config(interaction.guild)["main_role"]
                sub = Config.read_config(interaction.guild)["sub_role"]
                
                if guild.name == 'Main':
                    await member.remove_roles(discord.Object(main))
                    await member.add_roles(discord.Object(sub))
                else:
                    await member.remove_roles(discord.Object(sub))
                    await member.add_roles(discord.Object(main))
            except KeyError:
                pass
        emb = utl.make_embed(desc=f"Transferred <@{member.id}> (UID: {member_data[2]}) from **{guild.name}** guild to **{guild_to}** guild.", color=discord.Colour.green())
        await interaction.followup.send(embed=emb)
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

        await interaction.response.defer()
        removed = data[index-1]
        await self.remove_member_from_guild(guild.name, int(removed[2]))
        emb = utl.make_embed(desc=f"Removed <@{removed[0]}> (UID: {removed[2]}) from {guild.name} guild.", color=discord.Colour.green())
        await interaction.followup.send(embed=emb)
        return
    
    @members.command(name='list')
    @is_gm()
    async def members_list(self, interaction: discord.Interaction) -> None:
        """List members in the guild"""
        emb = discord.Embed(color=discord.Colour.blue())
        if interaction.guild.icon is not None:
            emb.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
            emb.set_thumbnail(url=interaction.guild.icon.url)
        emb.add_field(name='Main', value=f"{len(self.main_data)}/80", inline=True)           
        emb.add_field(name='Sub', value=f"{len(self.sub_data)}/80", inline=True)

        show_button = Button_View()
        show_button.add_item(Button_UI('List Main', discord.ButtonStyle.blurple))
        show_button.add_item(Button_UI('List Sub', discord.ButtonStyle.blurple))
        
        await interaction.response.send_message(embed=emb, view=show_button)
        await show_button.wait()

        if show_button.value is None:
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
        self.get_data(guild.name)
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

            if idview.value is None:
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
    
    @members.command(name='editdiscordid')
    @is_gm()
    @app_commands.describe(
        guild='Which guild to edit the member from?',
        uid="The in-game UID to change discord ID (e.g 18612020)",
        member="The UID's new discord ID")
    @app_commands.choices(guild=[
        Choice(name='Main', value=1),
        Choice(name='Sub', value=2)
    ])
    async def members_editdiscordid(self, interaction: discord.Interaction, guild: Choice[int], uid: app_commands.Range[int, 10000000, 19999999], member: discord.Member):
        """Edit the discord ID of a UID"""
        self.get_data(guild.name)
        data = None
        if guild.name == 'Main':
            data = self.main_data
        else:
            data = self.sub_data
        
        # If the UID is not in guild
        if not any(str(uid) in x for x in data):
            emb = utl.make_embed(desc=f":x: There are no records of UID {uid} in {guild.name} guild.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return
        
        records = [m for m in data if m[2] == (str(uid))]
        
        # If member is same as old one
        if records[0][0] == str(member.id):
            emb = utl.make_embed(desc=f":x: UID {uid} is already owned by <@{member.id}>.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return

        old_discord_id = records[0][0]
        # Changing the real main/sub data
        for r in data:
            if r[2] == str(uid):
                r[0] = str(member.id)
        await self.update_data(guild.name)
        emb = utl.make_embed(desc=f"Changed discord ID of UID {uid} from <@{old_discord_id}> ({old_discord_id}) to <@{member.id}> ({member.id}) in {guild.name} guild.", color=discord.Colour.green())
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
        self.get_data(guild.name)
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

            if idview.value is None:
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
        self.get_data(guild.name)
        data = None
        if guild.name == 'Main':
            data = self.main_data
        else:
            data = self.sub_data
        
        members_to_remove = []
        uid_to_remove = []
        for r in data:
            m = interaction.guild.get_member(int(r[0]))
            if m is None:
                members_to_remove.append(r[1])
                uid_to_remove.append(r[2])
            else:
                r[1] = str(m)

        emb = utl.make_embed(desc='Updating...', color=discord.Colour.yellow())
        await interaction.response.send_message(embed=emb)
        await self.update_data(guild.name)
        
        for u in uid_to_remove:
            await self.remove_member_from_guild(guild.name, int(u))
        
        text = ''
        if len(uid_to_remove) > 0:
            text = f'\n:warning: Removed {len(uid_to_remove)} members ({", ".join(members_to_remove)}) because they cannot be found in the server.'
        emb = utl.make_embed(desc=f"Updated the names for members in {guild.name} guild.{text}", color=discord.Colour.green())
        await interaction.edit_original_response(embed=emb)
    
    @members.command(name='populatedb')
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role='Role to add from?')
    async def members_populatedb(self, interaction: discord.Interaction, role: discord.Role) -> None:
        """Adds all current guild members to the server database"""
        emb = utl.make_embed(desc='Adding guild members to database...', color=discord.Colour.yellow())
        await interaction.response.send_message(embed=emb, ephemeral=True)
        members_raw : list[discord.Member] = role.members
        members_final: list[dict] = []
        for m in members_raw:
            members_final.append({"_id": str(m.id), "name": str(m), "created_at": m.created_at, "joined_at": m.joined_at, "referrer": "", "refers": []})
        await mongo.Mongo_Instance.insert_many(interaction.guild, members_final, "memberdata")

        emb = utl.make_embed(desc=f'Successfully added members from <@&{role.id}> to database!', color=discord.Colour.green())
        await interaction.edit_original_response(embed=emb)

    @members.command(name='addref')
    @is_gm()
    @app_commands.describe(referrer='The one who invites.', refers="The one who got invited.")
    async def members_addref(self, interaction: discord.Interaction, referrer: discord.Member, refers: discord.Member) -> None:
        """Sets a referrer for a guild member"""
        if referrer is refers:
            emb = utl.make_embed(desc=f'Referrer cannot be the same person as the referred.', color=discord.Colour.red())
            await interaction.response.send_message(embed=emb)
            return
        
        query = { '_id': str(referrer.id) }
        query2 = { '_id': str(refers.id) }
        rfrer = await mongo.Mongo_Instance.get_data(interaction.guild, query, 'memberdata')
        rfred = await mongo.Mongo_Instance.get_data(interaction.guild, query2, 'memberdata')

        if rfrer != None and rfred != None:
            if rfrer['referrer'] != "":
                emb = utl.make_embed(desc=f'<@{referrer.id}> already has a referrer, they cannot refer others!', color=discord.Colour.red())
                await interaction.response.send_message(embed=emb)
                return
            elif len(rfred['refers']) > 0:
                emb = utl.make_embed(desc=f'<@{refers.id}> is already a referrer, they cannot be referred by others!', color=discord.Colour.red())
                await interaction.response.send_message(embed=emb)
                return
            elif rfred['referrer'] != "":
                emb = utl.make_embed(desc=f'<@{refers.id}> already has a referrer, they cannot be referred by someone else!', color=discord.Colour.red())
                await interaction.response.send_message(embed=emb)
                return
            else:
                # Add referred to referrer
                refs = rfrer['refers']
                refs.append(str(refers.id))
                data = { '$set': {'refers': refs} }
                await mongo.Mongo_Instance.insert_data(interaction.guild, query, data, 'memberdata')
                
                # Add referrer to referred
                data2 = { '$set': {'referrer': str(referrer.id)} }
                await mongo.Mongo_Instance.insert_data(interaction.guild, query2, data2, 'memberdata')

                emb = utl.make_embed(desc=f'Successfully added <@{referrer.id}> as the referrer of <@{refers.id}>!', color=discord.Colour.green())
                await interaction.response.send_message(embed=emb)
                return
        else:
            r = referrer.id if rfrer is None else refers.id
            emb = utl.make_embed(desc=f'<@{r}> cannot be found in database!', color=discord.Colour.red())
            await interaction.response.send_message(embed=emb)
            return
        
    @members.command(name='delref')
    @is_gm()
    @app_commands.describe(member='The member whose referral status will be deleted.')
    async def members_delref(self, interaction: discord.Interaction, member: discord.Member) -> None:
        """Deletes a member's referral status"""
        query = { '_id': str(member.id) }
        member_data = await mongo.Mongo_Instance.get_data(interaction.guild, query, 'memberdata')

        if member_data['referrer'] != '':
            # Member has a referrer
            referrer = member_data['referrer']
            query2 = { '_id': referrer }
            referrer_data = await mongo.Mongo_Instance.get_data(interaction.guild, query2, 'memberdata')

            data = { '$set': {'referrer': ''} }
            await mongo.Mongo_Instance.insert_data(interaction.guild, query, data, 'memberdata')

            refers : list[str] = referrer_data['refers']
            refers.remove(str(member.id))
            data2 = { '$set': {'refers': refers} }
            await mongo.Mongo_Instance.insert_data(interaction.guild, query2, data2, 'memberdata')

            emb = utl.make_embed(desc=f'Successfully removed <@{member.id}> from all referrals!', color=discord.Colour.green())
            await interaction.response.send_message(embed=emb)
            return
        elif len(member_data['refers']) > 0:
            # Member has referred people
            confirm = Confirm_Or_Cancel_View(20)
            await confirm.send(interaction, f'You are about to remove <@{member.id}> who is a referrer. Are you sure?')
            await confirm.wait()

            if confirm.value is None:
                raise ViewTimedOutError
            elif confirm.value == 'Confirm':
                refers : list[str] = member_data['refers']
                for r in refers:
                    query2 = { '_id': r }
                    data2 = { '$set': {'referrer': ''} }
                    await mongo.Mongo_Instance.insert_data(interaction.guild, query2, data2, 'memberdata')
                data = { '$set': {'refers':[]} }
                await mongo.Mongo_Instance.insert_data(interaction.guild, query, data, 'memberdata')

                await interaction.edit_original_response(content='Done!', embed=None, view=None)

                emb = utl.make_embed(desc=f'Successfully removed <@{member.id}> from all referrals!', color=discord.Colour.green())
                await interaction.followup.send(embed=emb)
                return
        else:
            # No referrals
            emb = utl.make_embed(desc=f'<@{member.id}> has no referrals!', color=discord.Colour.red())
            await interaction.response.send_message(embed=emb)
            return
    
    @members.command(name='referrals')
    @is_gm()
    async def members_referrals(self, interaction: discord.Interaction) -> None:
        """List member referrals"""
        await interaction.response.defer(thinking=True)
        query = { 'refers': { '$ne': [] } }
        data = await mongo.Mongo_Instance.get_multi_data(interaction.guild, query, 'memberdata')

        if data is None or len(data) == 0:
            # No referrals
            emb = utl.make_embed(desc=f'There is currently no single referral yet!', color=discord.Colour.red())
            await interaction.followup.send(embed=emb)
            return

        referrers = {}
        for d in data:
            referrers[d['_id']] = d['refers']

        emb = discord.Embed(title='Referral List', color=discord.Colour.blue())
        if interaction.guild.icon is not None:
            emb.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
            emb.set_thumbnail(url=interaction.guild.icon.url)
        emb.set_footer(text=interaction.user, icon_url=interaction.user.display_avatar.url)
        emb.timestamp = datetime.datetime.now()

        text = ''
        for r in referrers.keys():
            refers = referrers[r]
            refers = [f"<@{refs}>" for refs in refers]
            text += f'**<@{r}> ({len(refers)})** -> {", ".join(refers)}\n'
        emb.description = text
        await interaction.followup.send(embed=emb)


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
                emb = utl.make_embed(title=f"Match found!", desc=f'The UID: {uid} is owned by <@{members[0]}> in {guilds[0]}', color=discord.Colour.green())
            await interaction.response.send_message(embed=emb)
            return
    
        
    def get_progress_up_to_date(self, gb_dates, progress, start_of_week, up_to_before: bool = False):
        prog = []
        start_of_week = datetime.datetime.strptime(start_of_week, "%d/%m/%Y")
        if up_to_before is True:
            for i in range(len(gb_dates)):
                try:
                    if datetime.datetime.strptime(gb_dates[i], "%d/%m/%Y") < start_of_week:
                        prog.append(progress[i])
                except IndexError:
                    prog.append('')
        else:
            for i in range(len(gb_dates)):
                try:
                    if datetime.datetime.strptime(gb_dates[i], "%d/%m/%Y") <= start_of_week:
                        prog.append(progress[i])
                except IndexError:
                    prog.append('')
        return prog
        
    @gb.command(name='check')
    @app_commands.describe(member='The member to check')
    async def gb_check(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """Check your guild battle progress"""
        mem = interaction.user
        # if searching for other member's gb
        if member is not None and member.id != mem.id:
            try:
                id = Config.read_config(interaction.guild)["gm_role"]
            except KeyError:
                id = 0
            if interaction.user.get_role(id) is None:
                emb = utl.make_embed(desc="You do not have the permission to check other people's guild battle progress.", color=discord.Colour.red())
                await interaction.response.send_message(embed=emb)
                return
            else:
                mem = member
        
        await interaction.response.defer()
        
        main = self.main_ws.findall(str(mem.id))
        sub = self.sub_ws.findall(str(mem.id))

        guild = ''
        data = None
        cell = None
        gb_dates = None
        ws = None

        # if member is not found
        if len(main) + len(sub) == 0:
            emb = utl.make_embed(desc=f"Cannot find <@{mem.id}> in guild.", color=discord.Colour.red())
            await interaction.followup.send(embed=emb)
            return
        # if member appears more than one time
        elif len(main) + len(sub) > 1:
            # ask which uid to check
            idview = Button_View(15)
            for i in main:
                id = self.main_ws.get(f'D{i.row}')[0][0]
                idview.add_item(Button_UI(str(id), discord.ButtonStyle.blurple))
            for i in sub:
                id = self.sub_ws.get(f'D{i.row}')[0][0]
                idview.add_item(Button_UI(str(id), discord.ButtonStyle.blurple))
                
            emb = utl.make_embed(desc=f'There are multiple accounts for <@{mem.id}> in the guild.\nWhich one do you want to check?', color=discord.Colour.yellow())
            await interaction.followup.send(embed=emb, view=idview)
            await idview.wait()
                
            if idview.value is None:
                raise ViewTimedOutError
            else:
                await interaction.edit_original_response(content='Done!', embed=None, view=None)
                cell = self.main_ws.find(idview.value)
                guild = 'Main Guild'
                ws = self.main_ws
                if cell is None:
                    cell = self.sub_ws.find(idview.value)
                    guild = 'Sub Guild'
                    ws = self.sub_ws
        else:
            # if member is only found only once in both guilds
            if len(main) > 0:
                cell = main[0]
                guild = 'Main Guild'
                ws = self.main_ws
            else:
                cell = sub[0]
                guild = 'Sub Guild'
                ws = self.sub_ws
        
        if guild == 'Main Guild':
            data = self.main_ws.row_values(cell.row, value_render_option=ValueRenderOption.unformatted)
            gb_dates = self.main_ws.row_values(1)[5:]
        else:
            data = self.sub_ws.row_values(cell.row, value_render_option=ValueRenderOption.unformatted)
            gb_dates = self.sub_ws.row_values(1)[5:]

        # Get the start of this week's date in string
        today = datetime.date.today()
        start_of_week = (today - datetime.timedelta(days=today.weekday())).strftime("%d/%m/%Y")
        # Member uid from data e.g. ['2', '724646090365050505', 'Bakugan#0000', '10101012', '', False, False, False]
        uid = data[3]
        progress = self.get_progress_up_to_date(gb_dates, data[5:], start_of_week, True)
        # Check the member's gb this week
        this_week = ws.find(start_of_week)
        done = False
        if this_week is not None:
            done = ws.get(f'{xl_col_to_name(this_week.col-1)}{cell.row}', value_render_option=ValueRenderOption.unformatted)
            if len(done) == 0:
                done = None
            else:
                done = done[0][0]
       
        query = { '_id': str(mem.id) }
        player_data = await mongo.Mongo_Instance.get_data(interaction.guild, query, 'memberdata')
        referrer = ''
        refers = []
        if player_data != None:
            referrer = "@"+ str(interaction.guild.get_member(int(player_data['referrer']))) if player_data['referrer'] != '' else ''
            refers_data = player_data['refers']
            for r in refers_data:
                m = interaction.guild.get_member(int(r))
                if m != None:
                    refers.append("@"+str(m))

        emb = utl.make_gb_progress_embed(interaction, mem, uid, guild, progress, done, gb_dates, referrer, refers)
        await interaction.followup.send(embed=emb)

    @gb.command(name='progress')
    @app_commands.describe(guild='Which guild to check?', date='The date to check in dd/mm/yyyy format')
    @app_commands.choices(guild=[
        Choice(name='Main', value=1),
        Choice(name='Sub', value=2)
    ])
    async def gb_progress(self, interaction: discord.Interaction, guild: Choice[int], date: Optional[str] = None):
        """Check the guild's weekly progress"""
        today = datetime.date.today()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        
        if date is not None:
            try:
                today = datetime.datetime.strptime(date, "%d/%m/%Y")
                start_of_week = today - datetime.timedelta(days=today.weekday())
            except ValueError:
                emb = utl.make_embed(desc="Entered date is invalid.", color=discord.Colour.red())
                await interaction.response.send_message(embed=emb, ephemeral=True)
                return
        
        ws = None
        snowflake = ''
        if guild.name == 'Main':
            ws = self.main_ws
            snowflake = '<:snowflakeblue:918047193464725534>'
        else:
            ws = self.sub_ws
            snowflake = '<:snowflakepink:918047193255002133>'

        start_of_week = start_of_week.strftime("%d/%m/%Y")
        this_week = ws.find(start_of_week, in_row=1)

        if this_week is None:
            emb = utl.make_embed(desc=f"There are no records found for {start_of_week}.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
            return
        
        await interaction.response.defer()

        c = xl_col_to_name(this_week.col-1)
        name, progress = ws.batch_get(['C2:C81', f'{c}2:{c}81'], value_render_option=ValueRenderOption.unformatted)
        progress = progress[:len(name)]
        total = len(name)
        done = progress.count([True])
        not_done = progress.count([False])
        exempted = total-done-not_done
        
        icon = ''
        if interaction.guild.icon != None:
            icon = interaction.guild.icon.url
            
        text = f':white_check_mark: Completed: {done}\n:x: **Not Completed: {not_done}**\n:white_circle: Exempted: {exempted}'
        emb = discord.Embed(title=f'{snowflake} {guild.name} Guild', description=f':calendar_spiral: **__Week {start_of_week}__**\n⠀')
        emb.add_field(name=f'Total members: {total}/80',value=text)
        emb.set_author(name='Guild Battle Weekly Progress', icon_url=icon)
        emb.set_thumbnail(url=icon)
        emb.set_footer(text=interaction.user, icon_url=interaction.user.display_avatar.url)
        emb.timestamp = datetime.datetime.now()

        show_buttons = Button_View(15)
        show_buttons.add_item(Button_UI('Completed', discord.ButtonStyle.blurple, disabled=(done == 0)))
        show_buttons.add_item(Button_UI('Not Completed', discord.ButtonStyle.blurple, disabled=(not_done == 0)))
        show_buttons.add_item(Button_UI('Exempted', discord.ButtonStyle.blurple, disabled=(exempted == 0)))
        
        await interaction.followup.send(embed=emb, view=show_buttons)
        await show_buttons.wait()

        if show_buttons.value is None:
            return

        emb = utl.make_embed(title=show_buttons.value)
        emb.set_author(name='Guild Battle Weekly Progress', icon_url=icon)
        emb.set_thumbnail(url=icon)
        emb.set_footer(text=interaction.user, icon_url=interaction.user.display_avatar.url)
        emb.timestamp = datetime.datetime.now()

        check = None
        if show_buttons.value == 'Completed':
            emb.description = f'**{done} member(s)** have completed Guild Battle for Week {start_of_week}.'
            check = [True]
        elif show_buttons.value == 'Not Completed':
            emb.description = f'**{not_done} member(s)** have not completed Guild Battle for Week {start_of_week}.'
            check = [False]
        else:
            emb.description = f'**{exempted} member(s)** have been exempted from Guild Battle for Week {start_of_week}.'
            check = []
        
        mem = []
        for i in range(len(name)):
            if progress[i] == check:
                mem.append(f'@{name[i][0]}')
        
        emb.description += '\n\n' + '\n'.join(mem)
        await interaction.edit_original_response(content='Done!', embed=None, view=None)
        await interaction.followup.send(embed=emb)

    @gb.command(name='warnings')
    @is_gm()
    @app_commands.describe(guild='Which guild to check?')
    @app_commands.choices(guild=[
        Choice(name='Main', value=1),
        Choice(name='Sub', value=2)
    ])
    async def gb_warnings(self, interaction: discord.Interaction, guild: Choice[int]):
        """List the amount of warnings each member in the guild has (mods only)"""
        ws = None
        if guild.name == 'Main':
            ws = self.main_ws
            snowflake = '<:snowflakeblue:918047193464725534>'
        else:
            ws = self.sub_ws
            snowflake = '<:snowflakepink:918047193255002133>'
        
        await interaction.response.defer()
        
        # Get the start of this week's date in string
        today = datetime.date.today()
        start_of_week = (today - datetime.timedelta(days=today.weekday())).strftime("%d/%m/%Y")

        headers = ws.row_values(1)
        gb_dates = headers[5:]
        c = xl_col_to_name(len(headers)-1)
        data = ws.batch_get([f'B2:{c}81'], value_render_option=ValueRenderOption.unformatted)[0]
        data  = [x for x in data if x[0] != ''] # remove empty records (records with no discord ID but added because gb records value exist)

        text = ''
        for m in data:
            gb_progress = m[4:]
            warnings = self.get_progress_up_to_date(gb_dates, gb_progress, start_of_week).count(False)
            if warnings > 2:
                text += f'**({m[2]}) @{m[1]}: {warnings}**\n'
            else:
                text += f'({m[2]}) @{m[1]}: {warnings}\n'

        icon = ''
        if interaction.guild.icon != None:
            icon = interaction.guild.icon.url

        emb = utl.make_embed(title=':warning: Warnings', desc=text)
        emb.set_author(name=f'{guild.name} Guild Warnings', icon_url=icon)
        emb.set_footer(text=self.bot.user, icon_url=self.bot.user.display_avatar.url)
        emb.timestamp = datetime.datetime.now()
        await interaction.followup.send(embed=emb)

    @gb.command(name='adddates')
    @is_gm()
    async def gb_adddates(self, interaction: discord.Interaction):
        """Adds a new gb date to the spreadsheet (mods only)"""
        # Get the start of this week's date in string
        today = datetime.date.today()
        start_of_week = (today - datetime.timedelta(days=today.weekday())).strftime("%d/%m/%Y")

        await interaction.response.defer()
        
        emb = None
        exist = True
        ws = [self.main_ws, self.sub_ws]

        for s in ws:
            # Get available gb dates
            headers = s.row_values(1)
            gb_dates = headers[5:]
        
            if start_of_week in gb_dates:
                continue
            else:
                exist = False
                s.update_cell(1, 6+len(gb_dates), "'" + start_of_week)
                s.format(f"{xl_col_to_name(5+len(gb_dates))}1", {
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "LEFT",
                    "borders": {
                        "top": {
                            "style": "SOLID"
                        },
                        "bottom": {
                            "style": "SOLID"
                        },
                        "left": {
                            "style": "SOLID"
                        },
                        "right": {
                            "style": "SOLID"
                        }
                    }
                })
                requests = {"requests": [
                    {
                        "repeatCell": {
                            "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}, "userEnteredValue": {"boolValue": False}},
                            "range": {"sheetId": s.id, "startRowIndex": 1, "endRowIndex": 81, "startColumnIndex": 5+len(gb_dates), "endColumnIndex": 6+len(gb_dates)},
                            "fields": "*"
                        }
                    }
                ]}
                self.sh.batch_update(requests)
                emb = utl.make_embed(desc=f"Added a new guild battle date entry for '{start_of_week}'.", color=discord.Colour.green())

        if exist is True:
            emb = utl.make_embed(desc=f"The guild battle date '{start_of_week}' already exist.", color=discord.Colour.red())

        await interaction.edit_original_response(embed=emb)

    @player.command(name='find')
    @app_commands.describe(uid='The UID to find.', server='Which server to find from?')
    @app_commands.choices(server=[
        Choice(name='AP', value=1),
        Choice(name='NA', value=2),
        Choice(name='EU', value=3)
    ])
    async def player_find(self, interaction: discord.Interaction, server: Choice[int], uid: app_commands.Range[int, 10000000, 19999999]) -> None:
        srv = ''
        longsrv = ''
        if server.name == 'AP':
            srv = 'ap'
            longsrv = 'Asia-Pacific'
        elif server.name == 'NA':
            srv = 'na'
            longsrv = 'America'
        else:
            srv = 'eu'
            longsrv = 'Europe'
        url = f"https://kennel.doggostruct.com/live/servers/{srv}/players/{uid}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
        
        if data['status'] == 'error' and data['message'] == "player not found":
            emb = utl.make_embed(desc=f"Cannot find player with UID {uid} in {longsrv} server!", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb)
            return
        elif data['status'] != 'success':
            emb = utl.make_embed(desc=f"An unknown error has occured! Please contact the administrator to fix this.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb)
            return
        
        data = data['data']
        player = data['player']
        profile_url = "https://huaxu.doggostruct.com/pgr/assets/product/texture/image/" + player['portrait'] + ".webp"
        start_date = None
        if data['start_date'] != None:
            start_date = int(datetime.datetime.fromisoformat(data['start_date']).timestamp())
 
        emb = discord.Embed(title=f'{player["name"]} (Lv.{player["level"]})', description=player["sign"], url=f"https://huaxu.doggostruct.com/players/{srv}/{uid}/characters")
        emb.set_author(name=f'{longsrv} • {player["id"]}')
        emb.set_thumbnail(url=profile_url)
        if start_date:
            emb.add_field(name=":calendar_spiral: Started", value=f"<t:{start_date}:D> (<t:{start_date}:R>)", inline=False)
        else:
            emb.add_field(name=":calendar_spiral: Started", value=f"`Unknown`", inline=False)
        emb.add_field(name="<:flag:977902975030796288> Guild", value=f'`{player["guild_name"]}`', inline=False)
        emb.add_field(name=":star: Likes", value=f'`{player["likes"]}`', inline=False)
        emb.set_footer(text=f"Powered by HUAXU", icon_url="https://github.com/skyexzs/database/blob/main/misc/huaxu-doggostruct/huaxu.png?raw=true")
        emb.timestamp = datetime.datetime.now()

        await interaction.response.send_message(embed=emb)


    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CheckFailure):
            emb = utl.make_embed(desc="You do not have the permission to run this command.", color=discord.Colour.red())
            try:
                await interaction.response.send_message(embed=emb, ephemeral=True)
            except discord.errors.InteractionResponded:
                await interaction.edit_original_response(embed=emb)
            return

async def setup(bot: commands.Bot) -> None:
    global Guild_Instance
    Guild_Instance = PGR_Guild(bot)
    await bot.add_cog(Guild_Instance, guilds=[discord.Object(id=887647011904557068), discord.Object(id=487100763684864010)])

Guild_Instance : PGR_Guild
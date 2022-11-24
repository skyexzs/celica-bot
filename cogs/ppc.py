import os
import re
import math
import datetime
import requests
from typing import List
from gspread.utils import ValueRenderOption
from gspread.exceptions import WorksheetNotFound
from itertools import groupby

import discord
from discord.ext import commands
from discord import app_commands

from utils import utils as utl
from utils.utils import ViewTimedOutError
import mongo

# initial data to add to Mongo DB
query = [
    {'_id': 'Alpha', 'aliases':['Alpha'], 'emoji':'<:Alpha:1031863371169022013>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Alpha.png'},
    {'_id': 'Amberia', 'aliases':['Amberia'], 'emoji':'<:Amberia:1031863374138593341>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Amberia.png'},
    {'_id': 'Camu', 'aliases':['Camu'], 'emoji':'<:Camu:1031863377292701696>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Amberia.png'},
    {'_id': 'Gabriel', 'aliases':['Gabriel'], 'emoji':'<:Gabriel:1031863382988554240>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Gabriel.png'},
    {'_id': 'Huaxu', 'aliases':['Huaxu'], 'emoji':'<:Huaxu:1031863385727451167>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Huaxu.png'},
    {'_id': 'Iron Maiden', 'aliases':['Iron Maiden','Tifa'], 'emoji':'<:IronMaiden:1031863388357275670>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Iron%20Maiden.png'},
    {'_id': 'Machiavelli', 'aliases':['Machiavelli'], 'emoji':'<:Machiavelli:1031863392182480916>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Machiavelli.png'},
    {'_id': 'Musashi', 'aliases':['Musashi', 'Musashi IX'], 'emoji':'<:Musashi:1031863395592458301>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Musashi.png'},
    {'_id': 'Nozzle', 'aliases':['Nozzle'], 'emoji':'<:Nozzle:1031863397756710992>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Nozzle.png'},
    {'_id': 'Pterygota Queen', 'aliases':['Pterygota Queen', 'Xenophera'], 'emoji':'<:PterygotaQueen:1031863399941943296>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Pterygota%20Queen.png'},
    {'_id': 'Roland', 'aliases':['Roland'], 'emoji':'<:Roland:1031863401892298773>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Roland.png'},
    {'_id': 'Roseblade', 'aliases':['Roseblade'], 'emoji':'<:Roseblade:1031863404744429568>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Roseblade.png'},
    {'_id': 'Rosetta', 'aliases':['Rosetta'], 'emoji':'<:Rosetta:1031863406954807362>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Rosetta.png'},
    {'_id': 'Sharkspeare', 'aliases':['Sharkspeare'], 'emoji':'<:Sharkspeare:1031863410222178314>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Sharkspeare.png'},
    {'_id': 'Vassago', 'aliases':['Vassago'], 'emoji':'<:Vassago:1031863412763922452>', 'thumbnail': 'https://raw.githubusercontent.com/skyexzs/database/main/pgr-icons/Vassago.png'}
]

SS_TOTAL_SCORE_CELL = 'C12'
WHALE_TOTAL_SCORE_CELL = 'J4'

def is_owner(interaction: discord.Interaction) -> bool:
    return interaction.user.id == 150826178842722304

class EX_PPC_BOSSES_DROPDOWN(discord.ui.Select):
    def __init__(self, parent, bosses: List[str], boss_icons, min_val, max_val):
        options = []
        for b in bosses:
            e = None
            icon = [r for r in boss_icons if b == r['_id']]
            if len(icon) > 0:
                e = icon[0]['emoji']
            options.append(discord.SelectOption(label=b, value=b, emoji=e))

        super().__init__(placeholder='Tap to select bosses...', min_values=min_val, max_values=max_val, options=options)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        await self.parent.callback(interaction)

class EX_PPC_BOSSES_VIEW(discord.ui.View):
    def __init__(self, bosses: List[str], boss_icons, min_val, max_val, timeout = 30):
        super().__init__()

        # Adds the dropdown to our view object.
        self.dropdown = EX_PPC_BOSSES_DROPDOWN(self, bosses, boss_icons, min_val, max_val)
        self.add_item(self.dropdown)
        self.timeout = timeout
        self.success = False
        self.values = None

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.success = True
        self.values = self.dropdown.values
        self.stop()

# The ['Boss_Button_View'] bit is for type hinting purposes to tell your IDE or linter
# what the type of `self.view` is. It is not required.
class Boss_Button_UI(discord.ui.Button['Boss_Button_View']):
    def __init__(self, emoji: str, emb: discord.Embed, id: str, disabled: bool = False):
        super().__init__(emoji=emoji, style=discord.ButtonStyle.primary, disabled=disabled)
        self.emb = emb
        self.id = id
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        await self.view.callback(interaction, self.id, self.emb)

class Boss_Button_View(discord.ui.View):
    def __init__(self, ss_emb: discord.Embed, splus_emb: discord.Embed, timeout = 120):
        super().__init__()
        self.ss_btn = Boss_Button_UI('<:SS:1041604124942270514>', emb=ss_emb, id='ss', disabled=True)
        self.splus_btn = Boss_Button_UI('<:SSSPlus:1041604127773442058>', emb=splus_emb, id='splus')
        self.add_item(self.ss_btn)
        self.add_item(self.splus_btn)
        self.timeout = timeout
    
    async def callback(self, interaction: discord.Interaction, btn_id: str, emb: discord.Embed):
        if btn_id == 'ss':
            self.ss_btn.disabled = True
            self.splus_btn.disabled = False
        else:
            self.ss_btn.disabled = False
            self.splus_btn.disabled = True
        await interaction.response.edit_message(embed=emb, view=self)

class PPC(commands.Cog):
    def __init__(self, bot: commands.Bot, gc):
        self.bot = bot
        self.gc = gc
        self.bosses = []
        self.boss_icons = []

        try:
            self.ss_sh = self.gc.open_by_url(os.getenv('SS_PPC_SPREADSHEET'))
            self.whale_sh = self.gc.open_by_url(os.getenv('WHALE_PPC_SPREADSHEET'))
            self.update_bosses()
        except:
            raise
    
    def update_bosses(self):
        try:
            self.boss_icons = mongo.Mongo_Instance.get_resources('boss_icons', {})

            self.bosses.clear()

            # --- SS Spreadsheet --- #
            ss_ws = self.ss_sh.worksheets()[2:]
            
            for ws in ss_ws:
                # Get the bosses and check with aliases to change it into universal key
                title = ws.title.strip()
                
                record = [r for r in self.boss_icons if title in r['aliases']]

                if len(record) > 0:
                    title = record[0]['_id']
                    self.bosses.append(title)
        except:
            raise

    @app_commands.command(name="exppc")
    async def exppc(self, interaction: discord.Interaction) -> None:
        """Get EX-PPC Scores required for Achievement Roles"""
        dropdown = EX_PPC_BOSSES_VIEW(self.bosses, self.boss_icons, min_val=3, max_val=3)

        emb = discord.Embed(
            title="EX-PPC Scores",
            description="Select three bosses from the list below.",
            color=discord.Colour.blue())

        emb.set_author(name=interaction.guild.name)
        if interaction.guild.icon != None:
            emb.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
            emb.set_thumbnail(url=interaction.guild.icon.url)

        emb.set_footer(text=interaction.user, icon_url=interaction.user.display_avatar.url)
        emb.timestamp = datetime.datetime.now()

        await interaction.response.send_message(embed=emb, view=dropdown, ephemeral=True)
        await dropdown.wait()

        # if the dropdown view timed out
        if dropdown.success is False:
            raise ViewTimedOutError
        
        raw_ss_total = 0
        raw_whale_total = 0
        
        icon0 = ''
        icon1 = ''
        icon2 = ''
        aliases = []
        for i in self.boss_icons:
            if i['_id'] == dropdown.values[0]:
                icon0 = i['emoji'] + ' '
                aliases.append(i['aliases'])
            if i['_id'] == dropdown.values[1]:
                icon1 = i['emoji'] + ' '
                aliases.append(i['aliases'])
            if i['_id'] == dropdown.values[2]:
                icon2 = i['emoji'] + ' '
                aliases.append(i['aliases'])

        emb = discord.Embed(
            title=f"{icon0}{dropdown.values[0]} - {icon1}{dropdown.values[1]} - {icon2}{dropdown.values[2]}",
            color=discord.Colour.blue())
        emb.set_author(name=interaction.guild.name)
        if interaction.guild.icon != None:
            emb.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
            emb.set_thumbnail(url=interaction.guild.icon.url)
        
        emb.set_footer(text=interaction.user, icon_url=interaction.user.display_avatar.url)
        emb.timestamp = datetime.datetime.now()
        
        # These are differentiated so it will still run if one fails
        try:
            for i in range(len(dropdown.values)):
                # Get from SS scores
                alias = aliases[i][0]
                ssws = self.ss_sh.worksheet(alias)

                raw_ss_total += int(ssws.acell(SS_TOTAL_SCORE_CELL).value)
        except :
            raw_ss_total = 0
        try:
            for i in range(len(dropdown.values)):
                # Get from Whale scores
                alias = aliases[i][0]
                if len(aliases[i]) > 1:
                    alias = aliases[i][1]

                wws = self.whale_sh.worksheet(alias)
                raw_whale_total = int(wws.acell(WHALE_TOTAL_SCORE_CELL).value)
        except:
            raw_whale_total = 0

        text = ''
        if raw_whale_total != 0:
            # Whale max scores rounded down to nearest 10k (for S+)
            overlord = math.floor(raw_whale_total / 10000) * 10000
            text += f'<:EXPPC1:1031556662017921064> <@&983931530005057586>: {overlord}\n'
        if raw_ss_total != 0:
            # SS max scores rounded up to nearest 10k (for SSS)
            legend = math.ceil(raw_ss_total / 10000) * 10000
            # SS max scores rounded down to nearest 10k and -10k (for SS)
            conqueror = math.floor(raw_ss_total / 10000) * 10000 - 10000
            text += f'<:EXPPC2:1031556773880008734> <@&1031387046016720908>: {legend}\n'
            text += f'<:EXPPC3:1031556870994939934> <@&977900757972029461>: {conqueror}'

        emb.add_field(name='Required scores for roles:', value=text, inline=False)
        emb.add_field(name='Max achievable scores:', value=f'Whale spreadsheet: {raw_whale_total}\nSS spreadsheet: {raw_ss_total}')

        success = utl.make_embed(desc="Success!", color=discord.Colour.green())
        await interaction.edit_original_response(embed=success, view=None)
        await interaction.followup.send(embed=emb)
    
    @app_commands.command(name="boss")
    async def boss(self, interaction: discord.Interaction) -> None:
        """Get EX-PPC bosses information from spreadsheet."""

        dropdown = EX_PPC_BOSSES_VIEW(self.bosses, self.boss_icons, min_val=1, max_val=1)

        emb = discord.Embed(
            title="EX-PPC Bosses",
            description="Select a boss from the list below to get their scores.",
            color=discord.Colour.blue())

        emb.set_author(name=interaction.guild.name)
        if interaction.guild.icon != None:
            emb.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
            emb.set_thumbnail(url=interaction.guild.icon.url)

        emb.set_footer(text=interaction.user, icon_url=interaction.user.display_avatar.url)
        emb.timestamp = datetime.datetime.now()

        await interaction.response.send_message(embed=emb, view=dropdown, ephemeral=True)
        await dropdown.wait()

        # if the dropdown view timed out
        if dropdown.success is False:
            raise ViewTimedOutError

        # for testing
        # dropdown.values = ['Sharkspeare']

        thb = ''
        emoji = ''
        aliases = []
        for i in self.boss_icons:
            if i['_id'] == dropdown.values[0]:
                thb = i['thumbnail']
                emoji = i['emoji']
                aliases = i['aliases']

        diff = ['Test','Elite','Knight','Chaos','Hell']

        # Create SS Embed Template
        ss_emb = discord.Embed(
            title=f"{emoji} {dropdown.values[0]} Scores (SS Sheet) <:SS:1041604124942270514>",
            color=discord.Colour.blue())
        ss_emb.set_author(name=interaction.guild.name)
        if interaction.guild.icon != None:
            ss_emb.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
            ss_emb.set_thumbnail(url=thb)
        ss_emb.set_footer(text=interaction.user, icon_url=interaction.user.display_avatar.url)
        ss_emb.timestamp = datetime.datetime.now()

        # Get score data from the SS sheet
        ssws = None
        for a in aliases:
            try:
                ssws = self.ss_sh.worksheet(a)
                break
            except WorksheetNotFound:
                continue

        scores = ssws.batch_get(['C2:E10'], value_render_option=ValueRenderOption.formula)[0]
        c = 0
        for s in scores:
            # example data: [[20262, '', '=HYPERLINK("https://youtu.be/oWRo7r32nfM", "0:09")'], []]
            # if it's not a row divider but a score entry
            if len(s) != 0:
                score = s[0]
                x = re.search(r'\(\"(.*)\",\"(.*)\"\)', s[2].replace(' ', ''))
                link = ''
                time = ''
                if x != None:
                    link, time = x.groups()
                else:
                    time = s[2]

                text = f'Score: **{score}**\nTime: **{time}**\n'
                
                if link != '':
                    text += f'**[Example]({link})**'

                ss_emb.add_field(name=diff[c], value=text, inline=True)
                c += 1
        
        # Create Whale Embed Template
        emb = discord.Embed(
            title=f"{emoji} {dropdown.values[0]} Scores (Whale Sheet) <:SSSPlus:1041604127773442058>",
            color=discord.Colour.blue())
        emb.set_author(name=interaction.guild.name)
        if interaction.guild.icon != None:
            emb.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
            emb.set_thumbnail(url=thb)
        emb.set_footer(text=interaction.user, icon_url=interaction.user.display_avatar.url)
        emb.timestamp = datetime.datetime.now()

        # Get score data from the Whale sheet
        split_condition = lambda x: x == []
        wws = None
        
        alias = aliases[0]
        if len(aliases) > 1:
            alias = aliases[1]

        wws = self.whale_sh.worksheet(alias)

        col = wws.col_values(3)[2:]
        data = wws.batch_get([f'C3:G{3+len(col)-1}'])[0]
        #print(data)
        grouper = groupby(data, key=split_condition)
        scores = [list(group) for key, group in grouper if not key]
        #print(scores)

        # Get hyperlink data from Whale sheet
        links = []
        ranges = ''
        row = 3
        for d in data:
            if len(d) != 0:
                ranges += f'ranges={alias}!H{row}&'
            row += 1
        
        if ranges != '':
            url = f'https://sheets.googleapis.com/v4/spreadsheets/1YzOGbhTKaGTzfGbQJDdI6PSw8lXxcDpEQeeVLF4u2Dw?{ranges}fields=sheets(data(rowData(values(hyperlink))))'
            res = requests.get(url, headers={"Authorization": "Bearer " + self.gc.auth.token})
            links = res.json()['sheets'][0]['data']
            for i in range(len(links)):
                if len(links[i]) == 0:
                    links[i] = ''
                else:
                    links[i] = links[i]['rowData'][0]['values'][0]['hyperlink']

        # Add a field for each score
        c = 0
        for i in range(len(scores)):
            for sc in scores[i]:
                text = f'Score: **{sc[0]}**\nTime: **{sc[1]}**\n'
                for j in sc[2:]:
                    try:
                        char = j.split('\n')
                        text += f'**{char[0]}**: {char[1]}\n'
                    except IndexError:
                        continue
                if len(links) != 0:
                    if links[c] != '':
                        text += f'**[Example]({links[c]})**'
                    c += 1
                emb.add_field(name=diff[i], value=text, inline=True)

        # Button for pagination
        pagination = Boss_Button_View(ss_emb, emb)

        # Send message
        success = utl.make_embed(desc="Success!", color=discord.Colour.green())
        await interaction.edit_original_response(embed=success, view=None)
        await interaction.followup.send(embed=ss_emb, view=pagination)

    @app_commands.command(name="exppc_update")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(is_owner)
    async def exppc_update(self, interaction: discord.Interaction) -> None:
        """Updates the EX-PPC scores from the spreadsheet"""
        emb = utl.make_embed(desc='Updating...', color=discord.Colour.yellow())
        await interaction.response.send_message(embed=emb, ephemeral=True)
        self.update_bosses()
        emb = utl.make_embed(desc='EX-PPC scores updated!', color=discord.Colour.green())
        await interaction.edit_original_response(embed=emb)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CheckFailure):
            emb = utl.make_embed(desc="You do not have the permission to run this command.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
    
PPC_Instance : PPC
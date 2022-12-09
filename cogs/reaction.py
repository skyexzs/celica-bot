import os
import json
import random
import emojis
from pathlib import Path
from typing import Literal

import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice

from utils import utils as utl
from config import MAIN_PATH
    
REACTION_FOLDER = 'reactions'

class ReactionDataEmptyError(discord.app_commands.AppCommandError):
    """Raised when reaction data is empty."""
    pass

class ReactData():
    def __init__(self, message: str, type: Literal['message', 'reply', 'reaction', 'sticker', 'dm'], wildcard: bool, response: list):
        self.message = message
        self.type = type
        self.wildcard = wildcard
        self.response = response
    
    def get_dict(self):
        return {'message': self.message, 'type': self.type, 'wildcard': self.wildcard, 'response': self.response}

class Reaction(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_folder()

    def check_folder(self):
        p = Path(os.path.join(MAIN_PATH, REACTION_FOLDER))
        p.mkdir(parents=True, exist_ok=True)

    def get_reaction_data(self, guild: discord.Guild):
        reaction_file = os.path.join(MAIN_PATH, REACTION_FOLDER, str(guild.id) + ".json")
        if (not(os.path.isfile(reaction_file))):
            return None
        
        with open(reaction_file, 'r') as f:
            data = json.load(f)
            return data
    
    def add_reaction_data(self, guild: discord.Guild, react_data: ReactData):
        data = self.get_reaction_data(guild)
        if data is None:
            data = {}
        data[react_data.message] = react_data.get_dict()

        self.write_reaction_data(guild, data)
    
    def write_reaction_data(self, guild: discord.Guild, data: dict):
        reaction_file = os.path.join(MAIN_PATH, REACTION_FOLDER, str(guild.id) + ".json")
        with open(reaction_file, 'w') as f:
            json.dump(data, f, indent=2)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
        if msg.guild is None:
            return
        
        """ code for development in Test Server"""
        #if msg.guild.id != 487100763684864010:
            #return

        reaction_data = self.get_reaction_data(msg.guild)

        if reaction_data is None:
            return
        
        message = msg.content.lower().strip()
        
        response_data = []
        
        for r in reaction_data:
            if reaction_data[r]['wildcard'] is True:
                if reaction_data[r]['message'] in message:
                    response_data.append(reaction_data[r])
            else:
                if reaction_data[r]['message'] == message:
                    response_data.append(reaction_data[r])
        
        if len(response_data) == 0:
            return
        
        for r in response_data:
            type = r['type']
            response = r['response']

            response : str = random.choice(response)

            args = {
                '{user}': f'<@{msg.author.id}>'}

            for a in args:
                response = response.replace(a, args[a])

            if type == 'message':
                await msg.channel.send(response)
            elif type == 'reply':
                await msg.reply(response)
            elif type == 'reaction':
                try:
                    int(response)
                    await msg.add_reaction(self.bot.get_emoji(int(response)))
                except ValueError:
                    await msg.add_reaction(emojis.encode(response))
            elif type == 'sticker':
                await msg.channel.send(stickers=[await msg.guild.fetch_sticker(int(response))])
            else:
                await msg.author.send(response)
    
    rc = app_commands.Group(name='reaction', description='Commands to set Reaction stuffs', default_permissions=discord.Permissions(administrator=True))
    
    @rc.command(name="add")
    @app_commands.describe(
        message='What message to respond to?',
        type='What type of response should it be (message, reply, reaction, sticker)',
        wildcard='Should the command be searched anywhere in the message (True) or only if exact match (False).',
        response="What's the response? Use '[|]' to make randomized replies.")
    @app_commands.choices(type=[
        Choice(name='message', value=1),
        Choice(name='reply', value=2),
        Choice(name='reaction', value=3),
        Choice(name='sticker', value=4),
        Choice(name='dm', value=5)
    ])
    async def reaction_add(self, interaction: discord.Interaction, message: str, type: Choice[int], wildcard: bool, response: str) -> None:
        """Add a new reaction response"""
        sticker = None
        response = response.split('[|]')

        if type.name == 'sticker':
            try:
                for r in response:
                    sticker = await interaction.guild.fetch_sticker(int(r))
            except:
                emb = utl.make_embed(desc=f"Sticker ID is not valid or cannot be found in this server.", color=discord.Colour.red())
                await interaction.response.send_message(embed=emb, ephemeral=True)
                return
        elif type.name == 'reaction':
            try:
                for i in range(len(response)):
                    e = emojis.get(emojis.encode(response[i]))
                    if len(e) > 0:
                        response[i] = emojis.decode(e.pop())
                        continue
                    if self.bot.get_emoji(int(response[i])) == None:
                        raise
            except:
                emb = utl.make_embed(desc=f"Emoji cannot be used by the bot.", color=discord.Colour.red())
                await interaction.response.send_message(embed=emb, ephemeral=True)
                return
    
        message = message.lower().strip()
        reaction_data = ReactData(message, type.name, wildcard, response)

        self.add_reaction_data(interaction.guild, reaction_data)

        emb = utl.make_embed(desc=f"Added '{message}' to reactions.", color=discord.Colour.green())
        await interaction.response.send_message(embed=emb, ephemeral=True)
    
    @rc.command(name="delete")
    @app_commands.describe(message='What message to respond to?')
    async def reaction_delete(self, interaction: discord.Interaction, message: str):
        """Delete a reaction"""
        reaction_data = self.get_reaction_data(interaction.guild)
        emb = None

        if reaction_data is None:
            raise ReactionDataEmptyError

        try:
            reaction_data.pop(message.lower().strip())
            self.write_reaction_data(interaction.guild, reaction_data)
            emb = utl.make_embed(desc=f"Reaction '{message.lower().strip()}' has been deleted.", color=discord.Colour.green())
        except:
            emb = utl.make_embed(desc=f"Reaction '{message.lower().strip()}' does not exist.", color=discord.Colour.red())

        await interaction.response.send_message(embed=emb, ephemeral=True)
    
    @rc.command(name="list")
    async def reaction_list(self, interaction: discord.Interaction):
        """List registered reactions"""
        reaction_data = self.get_reaction_data(interaction.guild)

        if reaction_data is None:
            raise ReactionDataEmptyError

        c = 0
        text = ''
        for r in reaction_data.keys():
            c += 1
            text += f'{c}. {r}\n'

        emb = utl.make_embed(title="Reactions:", desc=text, color=discord.Colour.green())
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @app_commands.command(name="sticker_id")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(msg_id="The message ID to be checked")
    async def get_sticker_id(self, interaction: discord.Interaction, msg_id: str):
        """Get a sticker's ID from a message"""
        emb = ''
        try:
            msg : discord.Message = await interaction.channel.fetch_message(int(msg_id))
            if len(msg.stickers) > 0:
                emb = utl.make_embed(desc=f"Sticker {msg.stickers[0].name}'s ID is {msg.stickers[0].id}", color=discord.Colour.green())
            else:
                emb = utl.make_embed(desc="There is no sticker in that message.", color=discord.Colour.red())
        except:
            emb = utl.make_embed(desc=f"Failed to retrieve message ID: {msg_id} from this channel.", color=discord.Colour.red())
        await interaction.response.send_message(embed=emb, ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, ReactionDataEmptyError):
            emb = utl.make_embed(desc=f"There is no reaction added yet.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)
        elif isinstance(error, app_commands.CheckFailure):
            emb = utl.make_embed(desc="You do not have the permission to run this command.", color=discord.Colour.red())
            await interaction.response.send_message(embed=emb, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    global Reaction_Instance
    Reaction_Instance = Reaction(bot)
    await bot.add_cog(Reaction_Instance, guilds=[discord.Object(id=887647011904557068), discord.Object(id=487100763684864010)])

Reaction_Instance : Reaction
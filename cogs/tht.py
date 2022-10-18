import datetime
import os.path
from apscheduler.job import Job

import discord
from discord.ext import commands
from discord import app_commands

from utils import utils as utl
from config import MAIN_PATH, Config
import scheduler
import mongo

def check_tht_jobs_exist(guild_id) -> bool:
    thtjob = scheduler.schdr.get_job(job_id='thtscheduler', jobstore=str(guild_id))
    tht15job = scheduler.schdr.get_job(job_id='tht15scheduler', jobstore=str(guild_id))
    if thtjob != None or tht15job != None:
        return True
    else:
        return False

async def get_tht_jobs(guild_id):
    thtjob = scheduler.schdr.get_job(job_id='thtscheduler', jobstore=str(guild_id))
    tht15job = scheduler.schdr.get_job(job_id='tht15scheduler', jobstore=str(guild_id))
    return thtjob, tht15job
    
async def check_player_tht_message(msg: discord.Message, job: Job):
    channel_id = job.args[1]

    if msg.channel.id == channel_id:
        query = { '_id': str(msg.author.id) }
        player_data = await mongo.Mongo_Instance.get_data(msg.guild, query, 'thtdata')

        if player_data != None:

            chat_count = player_data['chat_count'] + 1
            if chat_count >= 2:
                muted_role_id = Config.read_config(msg.guild)['tht_role_muted']
                await msg.author.add_roles(msg.guild.get_role(muted_role_id))
        
        else:
            player_data = { '$set':
            {   '_id': str(msg.author.id),
                'name': str(msg.author),
                'chat_count': 1 }
            }
            await mongo.Mongo_Instance.insert_data(msg.guild, query, player_data, 'thtdata')

async def stop_tht_event(guild_id: int, channel_id: int, role_id: int, type: str):
    guild = THT_Instance.bot.get_guild(guild_id)
    channel = guild.get_channel(channel_id)
    role = guild.get_role(role_id)

    if type != '15min':
        await mongo.Mongo_Instance.delete_data(guild, {}, 'thtdata')
        muted_role = guild.get_role(Config.read_config(guild)['tht_role_muted'])
        for m in muted_role.members:
            await m.remove_roles(muted_role)

    emb = utl.make_embed(desc='The THT event is now over. Please wait for the next announcement.', color=discord.Colour.red())
    await channel.set_permissions(role, send_messages=False, read_messages=True)
    await channel.send(embed=emb)

class Button_UI(discord.ui.Button):
    def __init__(self, label: str, style: discord.ButtonStyle, disabled: bool = False):
        super().__init__(label=label, style=style, disabled=disabled)
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        await self.view.callback(interaction, self.label)

class THT_Button_View(discord.ui.View):
    def __init__(self, timeout = 10):
        super().__init__()
        self.value = None
        self.timeout = timeout
    
    async def callback(self, interaction: discord.Interaction, label: str):
        await interaction.response.defer()
        self.value = label
        self.stop()

class THT_Stop_View(THT_Button_View):
    def __init__(self, timeout = 10):
        super().__init__(timeout)

class THT_Create_Or_Stop_View(THT_Button_View):
    def __init__(self, guild_id: int, timeout = 10):
        super().__init__(timeout)
        self.add_item(Button_UI('Create', discord.ButtonStyle.green))
        self.add_item(Button_UI('Stop', discord.ButtonStyle.red, disabled=not check_tht_jobs_exist(guild_id)))

    """
    @discord.ui.button(label='Create', style=discord.ButtonStyle.green)
    async def create(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.value = 'Create'
        self.stop()

    @discord.ui.button(label='Stop', style=discord.ButtonStyle.red, disabled=check_tht_jobs_exist())
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.value = 'Stop'
        self.stop()
    """

class THT_Mode_Dropdown_UI(discord.ui.Select):
    def __init__(self, parent):
        options = [
            discord.SelectOption(label='Normal', value='normal', emoji='<:nanamiscream:728515428724244530>'),
            discord.SelectOption(label='Specific Zone', value='specific', emoji='<:QuScream:719833336888950805>'),
            discord.SelectOption(label='Special', value='special', emoji='<:ScreamRosetta:892739847603765248>'),
            discord.SelectOption(label='Surprise Special', value='surprise', emoji='<:ScreamAlpha:897855688880050256>'),
            discord.SelectOption(label='SOLO Specific', value='solo', emoji='<:BiancaScream:884098835050295356>'),
            discord.SelectOption(label='Class Specific', value='class', emoji='<:AylaScream:722561152382402611>'),
            discord.SelectOption(label='15 MIN Random', value='15min', emoji='<:ScreamVera:899144731395760128>')
        ]

        super().__init__(placeholder='Choose the type of THT...', min_values=1, max_values=1, options=options)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        await self.parent.callback(interaction)

class THT_Mode_Selection_View(discord.ui.View):
    def __init__(self, timeout = 30):
        super().__init__()

        # Adds the dropdown to our view object.
        self.dropdown = THT_Mode_Dropdown_UI(self)
        self.add_item(self.dropdown)
        self.timeout = timeout
        self.success = False
        self.value = None

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.success = True
        self.value = self.dropdown.values[0]
        self.stop()

class THT_Modal(discord.ui.Modal, title="Create a THT Event"):
    submitted = False

    name = discord.ui.TextInput(
        label='name',
        placeholder='Enter a name for the THT event...',
        min_length=5,
        max_length=30
    )
    description = discord.ui.TextInput(
        label='Description',
        placeholder='Enter a description for the type of event...',
        default='Please check <#942612957047717909> for more information.',
        required=False,
        style=discord.TextStyle.long,
        max_length=150
    )
    requirements = discord.ui.TextInput(
        label='Requirements',
        placeholder='Enter a requirement for the submission...',
        required=False,
        max_length=100
    )
    start_date = discord.ui.TextInput(
        label='Start Date',
        placeholder='e.g: 24/10/2022',
        min_length=10,
        max_length=10
    )
    custom_thumbnail = discord.ui.TextInput(
        label='Custom Thumbnail URL',
        placeholder='https://',
        required=False,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            date = datetime.datetime.strptime(self.start_date.value, '%d/%m/%Y')
            self.submitted = True
            emb = utl.make_embed(desc='Updated THT message!', color=discord.Colour.green())
        except ValueError:
            emb = utl.make_embed(desc='Start date is not in valid format (dd/mm/yyyy)!', color=discord.Colour.red())
        finally:
            await interaction.response.send_message(embed=emb, ephemeral=True)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
        await interaction.response.send_message(embed=error_emb, ephemeral=True)

        raise error

class THT(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
            
        """ code for development in Test Server"""
        #if msg.guild.id != 487100763684864010:
            #return

        if msg.channel.permissions_for(msg.author).administrator == True:
            return

        thtjob, tht15job = await get_tht_jobs(msg.guild.id)

        if thtjob != None:
            await check_player_tht_message(msg, thtjob)

        if tht15job != None:
            await check_player_tht_message(msg, tht15job)

    @app_commands.command(name="tht")
    @app_commands.default_permissions(administrator=True)
    async def tht(self, interaction: discord.Interaction) -> None:
        """Starts THT Event."""
        try:
            role = Config.read_config(interaction.guild)["tht_role"]
            muted_role = Config.read_config(interaction.guild)["tht_role_muted"]
            if role == 0 or interaction.guild.get_role(role) == None or muted_role == 0 or interaction.guild.get_role(muted_role) == None:
                Config.insert_config(interaction.guild, "tht_role", 0)
                Config.insert_config(interaction.guild, "tht_role_muted", 0)
                emb = utl.make_embed(desc="THT roles are not yet set.", color=discord.Colour.red())
                await interaction.response.send_message(embed=emb, ephemeral=True)
            else:
                view = THT_Create_Or_Stop_View(interaction.guild.id)
                emb = utl.make_embed(desc="Do you want to create or stop a THT event?", color=discord.Colour.yellow())
                await interaction.response.send_message(embed=emb, ephemeral=True, view=view)
                await view.wait()
                if view.value is None:
                    raise utl.ViewTimedOutError
                elif view.value == 'Create':
                    dropdown = THT_Mode_Selection_View()

                    emb = discord.Embed(
                        title="THT Event",
                        description="Choose the type of THT in the list below to start.",
                        color=discord.Colour.gold())
                    emb.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
                    emb.set_footer(text=self.bot.user, icon_url=self.bot.user.display_avatar.url)
                    emb.timestamp = datetime.datetime.now()
                    await interaction.edit_original_response(embed=emb, view=dropdown)
                    await dropdown.wait()

                    # if the dropdown view timed out
                    if dropdown.success is False:
                        raise utl.ViewTimedOutError

                    # if the user interacted with the dropdown
                    else:
                        thtjob = scheduler.schdr.get_job(job_id='thtscheduler', jobstore=str(interaction.guild.id))
                        tht15job = scheduler.schdr.get_job(job_id='tht15scheduler', jobstore=str(interaction.guild.id))
                        if dropdown.value in ('normal', 'specific', 'solo', 'class', 'special', 'surprise') and thtjob != None:
                            emb = utl.make_embed(desc="There is a normal THT event running already.", color=discord.Colour.red())
                            await interaction.edit_original_response(embed=emb, view=None)
                            return
                        elif dropdown.value == '15min' and tht15job != None:
                            emb = utl.make_embed(desc="There is a 15 Min THT event running already.", color=discord.Colour.red())
                            await interaction.edit_original_response(embed=emb, view=None)
                            return
                            
                        confirmview = THT_Button_View()
                        confirmview.add_item(Button_UI('Confirm', discord.ButtonStyle.green))

                        emb = utl.make_embed(desc=f"Are you sure you want to create a [{dropdown.value}] THT?", color=discord.Colour.yellow())
                        await interaction.edit_original_response(embed=emb, view=confirmview)
                        await confirmview.wait()

                        if confirmview.value is None:
                            raise utl.ViewTimedOutError

                        query = { '_id': 'tht_message' }
                        message_data = await mongo.Mongo_Instance.get_data(interaction.guild, query)

                        if message_data == None:
                            emb = utl.make_embed(desc="THT message to be sent is not yet set.", color=discord.Colour.red())
                            await interaction.edit_original_response(embed=emb, view=None)
                            return

                        emb = discord.Embed(title=message_data['name'], description=message_data['description'])
                        emb.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
                        start_date = datetime.datetime.strptime(message_data['start_date'], '%d/%m/%Y')
                        start_date = start_date.replace(hour = 15, minute = 0, second = 0, tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
                        emb.set_footer(text=self.bot.user, icon_url=self.bot.user.display_avatar.url)
                        emb.timestamp = datetime.datetime.now()

                        end_date = 0
                        url = ''
                        job_id = 'thtscheduler'
                        if dropdown.value in ('normal', 'specific', 'solo', 'class'):
                            end_date = start_date + datetime.timedelta(days=7)
                            if dropdown.value == 'normal':
                                url = 'https://cdn.discordapp.com/attachments/738687482467450880/1028890473688997948/THT_1.png'
                            if dropdown.value == 'specific':
                                url = 'https://cdn.discordapp.com/attachments/738687482467450880/1028890474175528960/THT_2.png'
                            if dropdown.value == 'solo':
                                url = 'https://cdn.discordapp.com/attachments/738687482467450880/1028890475467382844/THT_5.png'
                            if dropdown.value == 'class':
                                url = 'https://cdn.discordapp.com/attachments/738687482467450880/1028890476029411410/THT_6.png'
                            pass
                        elif dropdown.value in ('special','surprise'):
                            end_date = start_date + datetime.timedelta(days=5)
                            if dropdown.value == 'special':
                                url = 'https://cdn.discordapp.com/attachments/738687482467450880/1028890474687250432/THT_3.png'
                            if dropdown.value == 'surprise':
                                url = 'https://cdn.discordapp.com/attachments/738687482467450880/1028890475081506906/THT_4.png'
                            pass
                        elif dropdown.value == '15min':
                            start_date = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=8)))
                            end_date = start_date + datetime.timedelta(minutes=15)
                            #end_date = datetime.datetime.fromtimestamp(1665993480, tz=datetime.timezone(datetime.timedelta(hours=8))) for testing
                            url = 'https://cdn.discordapp.com/attachments/738687482467450880/1028890476457246761/THT_7.png'
                            job_id = 'tht15scheduler'
                            pass
                            
                        emb.add_field(name='Start', value=f"<t:{int(start_date.timestamp())}>", inline=True)           
                        emb.add_field(name='End', value=f"<t:{int(end_date.timestamp())}>", inline=True)
                        if len(message_data['requirements']) != 0:
                            emb.add_field(name='Requirements', value=message_data['requirements'], inline=False)
                        if len(message_data['custom_thumbnail']) != 0:
                            emb.set_thumbnail(url=message_data['custom_thumbnail'])
                        else:
                            emb.set_thumbnail(url=url)

                        scheduler.schdr.add_job(stop_tht_event, 'date', run_date=end_date, args=[interaction.guild.id, interaction.channel.id, role, dropdown.value], jobstore=str(interaction.guild.id), misfire_grace_time=7200, id=job_id, replace_existing=True, max_instances=1000)

                        success = utl.make_embed(desc="Success!", color=discord.Colour.green())
                        #await interaction.delete_original_response() // you can delete a ephemeral message this way
                        
                        await interaction.edit_original_response(embed=success, view=None)
                        await interaction.channel.send(embed=emb)
                        await interaction.channel.set_permissions(interaction.guild.get_role(role), send_messages=None, read_messages=True)
                else:
                    # stop THT event if any
                    thtjob = scheduler.schdr.get_job(job_id='thtscheduler', jobstore=str(interaction.guild.id))
                    tht15job = scheduler.schdr.get_job(job_id='tht15scheduler', jobstore=str(interaction.guild.id))

                    stopview = THT_Stop_View()
                    if thtjob != None:
                        stopview.add_item(Button_UI('Normal', discord.ButtonStyle.blurple))
                    if tht15job != None:
                        stopview.add_item(Button_UI('15 Min', discord.ButtonStyle.blurple))

                    emb = utl.make_embed(desc="Which THT event do you want to stop?", color=discord.Colour.yellow())
                    await interaction.edit_original_response(embed=emb, view=stopview)
                    await stopview.wait()

                    if stopview.value is None:
                        raise utl.ViewTimedOutError

                    else:
                        confirmview = THT_Button_View()
                        confirmview.add_item(Button_UI('Confirm', discord.ButtonStyle.green))

                        emb = utl.make_embed(desc=f"Are you sure you want to stop {stopview.value} THT?", color=discord.Colour.yellow())
                        await interaction.edit_original_response(embed=emb, view=confirmview)
                        await confirmview.wait()

                        if confirmview.value is None:
                            raise utl.ViewTimedOutError
                        else:
                            if stopview.value == 'Normal':
                                # Normal THT
                                scheduler.schdr.remove_job(job_id='thtscheduler', jobstore=str(interaction.guild.id))
                                emb = utl.make_embed(desc=f"Stopped scheduler for Normal THT.", color=discord.Colour.green())
                            else:
                                # 15 Min THT
                                scheduler.schdr.remove_job(job_id='tht15scheduler', jobstore=str(interaction.guild.id))
                                emb = utl.make_embed(desc=f"Stopped scheduler for 15 Min THT.", color=discord.Colour.green())
                            await interaction.edit_original_response(embed=emb, view=None)

        except utl.ViewTimedOutError:
            emb = utl.make_embed(desc="Timed out...", color=discord.Colour.red())
            await interaction.edit_original_response(embed=emb, view=None)
            pass
    
    @app_commands.command(name="thtmessage")
    @app_commands.default_permissions(administrator=True)
    async def thtmessage(self, interaction: discord.Interaction) -> None:
        """Edits the message to be sent during /tht."""
        modal = THT_Modal()
        query = { '_id': 'tht_message' }
        message_data = await mongo.Mongo_Instance.get_data(interaction.guild, query)

        if message_data != None:
            modal.name.default = message_data['name']
            modal.description.default = message_data['description']
            modal.requirements.default = message_data['requirements']
            modal.start_date.default = message_data['start_date']
            modal.custom_thumbnail.default = message_data['custom_thumbnail']
        
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.submitted:
            new_message = { '$set':
            {   '_id': 'tht_message',
                'name': modal.name.value,
                'description': modal.description.value,
                'requirements': modal.requirements.value,
                'start_date': modal.start_date.value,
                'custom_thumbnail': modal.custom_thumbnail.value }
            }
                
            await mongo.Mongo_Instance.insert_data(interaction.guild, query, new_message)

            emb = discord.Embed(title=modal.name.value,description=modal.description.value)
            emb.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
            start_date = datetime.datetime.strptime(modal.start_date.value, '%d/%m/%Y')
            start_date = start_date.replace(hour = 15, minute = 0, second = 0, tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
            end_date = start_date + datetime.timedelta(days=7)
            emb.add_field(name='Start', value=f"<t:{int(start_date.timestamp())}>", inline=True)
            emb.add_field(name='End', value=f"<t:{int(end_date.timestamp())}>", inline=True)
            if len (modal.requirements.value) != 0:
                emb.add_field(name='Requirements', value=modal.requirements.value, inline=False)
            if len(modal.custom_thumbnail.value) != 0:
                emb.set_thumbnail(url=modal.custom_thumbnail.value)
            else:
                emb.set_thumbnail(url='https://cdn.discordapp.com/attachments/940719387147640883/1028228531559338014/THT_Sample_1.png')
            emb.set_footer(text=self.bot.user, icon_url=self.bot.user.display_avatar.url)
            emb.timestamp = datetime.datetime.now()

            await interaction.channel.send(content='The message will appear like this:', embed=emb)
    
    @commands.command(aliases=['thtr'])
    @commands.has_permissions(administrator=True)
    async def thtrole(self, ctx, role: discord.Role, role2: discord.Role):
        """Set the role for THT Participants."""
        if role is ctx.guild.roles[0] or role2 is ctx.guild.roles[0]:
            emb = utl.make_embed(desc="THT roles should not be set to everyone.", color=discord.Colour.red())
        elif role == role2:
            emb = utl.make_embed(desc="Normal and Muted THT role should not be the same.", color=discord.Colour.red())
        else:
            Config.insert_config(ctx.guild, "tht_role", role.id)
            Config.insert_config(ctx.guild, "tht_role_muted", role2.id)
            emb = utl.make_embed(desc=f"THT role set to <@&{str(role.id)}> and Muted role set to <@&{str(role2.id)}>.", color=discord.Colour.green())
        await utl.send_embed(ctx, emb)

    @thtrole.error
    async def thtrole_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the thtrole command."""
        if isinstance(error, commands.MissingPermissions):
            pass
        elif isinstance(error, commands.RoleNotFound):
            emb = utl.make_embed(desc="Please enter a valid role.", color=discord.Colour.red())
            emb.add_field(name="Usage:", value=Config.read_config(ctx.guild)["command_prefix"]+"thtrole @Role @MutedRole")
            await utl.send_embed(ctx, emb)
        elif isinstance(error, commands.MissingRequiredArgument):
            try:
                id = Config.read_config(ctx.guild)["tht_role"]
                id2 = Config.read_config(ctx.guild)["tht_role_muted"]
            except KeyError:
                id = 0
                id2 = 0
            if ctx.guild.get_role(id) != None and ctx.guild.get_role(id2) != None:
                emb = utl.make_embed(desc=f"THT role has been set to <@&{str(id)}> and Muted role set to <@&{str(id2)}>.", color=discord.Colour.green())
            else:
                Config.insert_config(ctx.guild, "tht_role", 0)
                Config.insert_config(ctx.guild, "tht_role_muted", 0)
                emb = utl.make_embed(desc="THT roles are not yet set.", color=discord.Colour.red())
            await utl.send_embed(ctx, emb)
        else:
            error_emb = utl.make_embed(desc="An unknown error has occurred. Please contact the administrator.", color=discord.Colour.red())
            await utl.send_embed(ctx, error_emb)
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("thtrole", error)

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            emb = utl.make_embed(desc="You do not have the permission to run this command.", color=discord.Colour.red())
            await utl.send_embed(ctx, emb)
        else:
            with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
                utl.log_error("COG_tht", error)

    # TO DO LIST : ENABLE/DISABLE THT MUTES

THT_Instance : THT
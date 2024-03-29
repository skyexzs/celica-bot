import os, re
import pytz, datetime
from typing import Union

import discord

from discord.errors import Forbidden
from config import MAIN_PATH

### @package utils
#
# The color presets, send_message() and make_embed() functions are
# included in the [discord-bot template by
# nonchris](https://github.com/nonchris/discord-bot)


# color scheme for embeds as rgb
blue_light = discord.Color.from_rgb(20, 255, 255)  # default color
green = discord.Color.from_rgb(142, 250, 60)   # success green
yellow = discord.Color.from_rgb(245, 218, 17)  # warning like 'hey, that's not cool'
orange = discord.Color.from_rgb(245, 139, 17)  # warning - rather critical like 'no more votes left'
red = discord.Color.from_rgb(255, 28, 25)      # error red

### @package utils
#
# Utilities and helper functions
#

async def send_embed(ctx, embed, delay=None):
    """!
    Handles the sending of embeds
    @param ctx context to send to
    @param embed embed to send
    - tries to send embed in channel
    - tries to send normal message when that fails
    - tries to send embed private with information abot missing permissions
    If this all fails: https://youtu.be/dQw4w9WgXcQ
    """
    try:
        await ctx.send(embed=embed, delete_after=delay)
    except Forbidden:
        try:
            await ctx.send("Hey, seems like I can't send embeds. Please check my permissions :)")
        except Forbidden:
            await ctx.author.send(
                f"Hey, seems like I can't send any message in {ctx.channel.name} on {ctx.guild.name}\n"
                f"May you inform the server team about this issue? :slight_smile:", embed=embed)


def make_embed(title="", desc="", color=discord.Colour.teal(), name="", value="‌", footer=None) -> discord.Embed:
    """!
    Function to generate generate an embed in one function call
    please note that name and value can't be empty - name and value contain a zero width non-joiner
    @param title Headline of embed
    @param color RGB Tuple (Red, Green, Blue)
    @param name: Of field (sub-headline)
    @param value: Text of field (actual text)
    @param footer: Text in footer
    @return Embed ready to send
    """
    # make color object
    
    if title != "" and desc != "":
        emb = discord.Embed(title=title, description=desc, color=color)
    elif title != "":
        emb = discord.Embed(title=title, color=color)
    elif desc != "":
        emb = discord.Embed(description=desc, color=color)

    if name != "" and value != "":
        emb.add_field(name=name, value=value)
    if footer is not None:
        emb.set_footer(text=footer)

    return emb

def make_gb_progress_embed(interaction: discord.Interaction, member: discord.Member, uid, guild, progress, this_week: bool, gb_dates, referrer: str, refers: list[str]):
    text = ''
    warnings = 0
    warn_dates = ''

    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    start_of_week = start_of_week.strftime("%d/%m/%Y")
    
    first_date = start_of_week

    done = progress.count(True)
    warnings = progress.count(False)
    exempted = progress.count('')
    total = len(progress)-exempted
    
    c = 0
    for i in range(len(progress)):
        if progress[i] is False:
            c += 1
            warn_dates += f'\n{c}: {gb_dates[i]}'

    if len(gb_dates) > 0:
        first_date = gb_dates[0]
    if total != 0:
        progress_percentage = round(done / total * 100, 2)
        rounded_progress = int(round(progress_percentage * 2 / 10))
        bar = ''
        for i in range(int(rounded_progress)):
            bar += '█'
        for i in range(int(rounded_progress), 20):
            bar += '░'
        text = f'**__Completion rate:__**\n**║{bar}║ ({progress_percentage:g}%)**\n\n`{done} out of {total} guild battles completed since {first_date}`\n⠀'

    g_emoji = ''
    if guild == 'Main Guild':
        g_emoji = '<:snowflakeblue:918047193464725534>'
    else:
        g_emoji = '<:snowflakepink:918047193255002133>'

    icon = ''
    if interaction.guild.icon != None:
        icon = interaction.guild.icon.url

    if text == '':
        text = '`No GB records found yet.`'
    emb = discord.Embed(title=f'{g_emoji} {member} (UID: {uid}) <:exaltair_Logo:937199287807377458>', description=text)
    emb.set_author(name='Guild Battle Progress', icon_url=icon)
    if (member.display_avatar != None):
        emb.set_thumbnail(url=member.display_avatar.url)

    # GB Completion
    if this_week is True:
        emb.add_field(name=f':calendar_spiral: This week {start_of_week}', value=':white_check_mark: The mods have marked your GB completion.', inline=False)
    elif this_week is False:
        emb.add_field(name=f':calendar_spiral: This week {start_of_week}', value=':x: The mods have not marked your GB as completed.', inline=False)
    else:
        emb.add_field(name=f':calendar_spiral: This week {start_of_week}', value=':white_circle: You are exempted from doing GB this week.', inline=False)
    
    # Warnings
    if warnings > 0:
        emb.add_field(name=':warning: Warnings', value=f'You have {warnings} warning(s) for previously missing a guild battle.{warn_dates}', inline=False)
    
    refs = False
    # Referrals
    if referrer != "":
        refs = True
        emb.add_field(name=f':bust_in_silhouette: {referrer} referred you to join Exaltair!', value=f'\u200b', inline=False)
    elif len(refers) > 0:
        refs = True
        emb.add_field(name=f':busts_in_silhouette: You have referred {len(refers)} member(s) to join Exaltair! Thanks <3', value=f':incoming_envelope: {", ".join(refers)}', inline=False)

    if member.joined_at != None:
        jointime = member.joined_at.astimezone(tz=datetime.timezone(datetime.timedelta(hours=8)))
        jointime = jointime.strftime("%d/%m/%Y ")
        boost = '\u200b'
        space = '\u200b\n' if not refs else ''
        if member.premium_since != None:
            boost = '**<:nitro_boost:1041634239541686272> Thanks for boosting this server! ❤️**'
        emb.add_field(name=f'{space}:pencil: You joined this server on {jointime}', value=boost, inline=False)

    emb.set_footer(text=f'〆 Exaltair • {guild}')
    emb.timestamp = datetime.datetime.now()

    return emb

def extract_id_from_string(content: str) -> Union[int, None]:
    """!
    Scans string to extract user/guild/message id\n
    Can extract IDs from mentions or plaintext
    @return extracted id as int if exists, else None
    """
    # matching string that has 18 digits surrounded by non-digits or start/end of string
    match = re.match(r'(\D+|^)(\d{18})(\D+|$)', content)

    return int(match.group(2)) if match else None


def get_member_name(member: discord.Member) -> str:
    """!
    Shorthand to extract wich name to use when addressing member
    @return member.nick if exists else member.name
    """
    return member.nick if member.nick else member.name

def log_error(cause, error):
    timezone = pytz.timezone("Asia/Jakarta")
    today = datetime.datetime.today().astimezone(timezone).strftime("%Y-%m-%d %H-%M-%S")

    with open(os.path.join(MAIN_PATH, 'err.log'), 'a') as f:
        f.write(f'{today} (UTC+7) Unhandled exception ({cause}): {error}\n')

class ViewTimedOutError(discord.app_commands.AppCommandError):
    """Raised when a Discord UI View has timed out."""
    pass
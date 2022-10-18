import os, re
from typing import Union

import discord
import pytz, datetime
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
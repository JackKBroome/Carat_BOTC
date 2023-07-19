import os
from time import gmtime, strftime
from typing import Union

import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands
from nextcord.utils import get

OwnerID = 107209184147185664

WorkingEmoji = '\U0001F504'
CompletedEmoji = '\U0001F955'
DeniedEmoji = '\U000026D4'


def get_channel_type(channel_type):
    if channel_type in ['experimental', 'Experimental', 'exp', 'Exp', 'x', 'X']:
        return "Experimental"
    else:
        return "Regular"


async def dm_user(user: Union[nextcord.User, nextcord.Member], content: str) -> bool:
    try:
        await user.send(content)
        return True
    except nextcord.Forbidden:
        print(f"Could not DM {user} due to lack of permission")
        return False
    except Exception as e:
        print(f"Could not DM {user} due to unknown error: {e}")
        return False


async def deny_command(ctx: commands.Context):
    await ctx.message.add_reaction(DeniedEmoji)
    print(f"-= The {ctx.command.name} command was stopped against " + str(ctx.author.name) + " at " + str(
        strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))


async def start_processing(ctx):
    await ctx.message.add_reaction(WorkingEmoji)


def is_mention(string: str) -> bool:
    return string.startswith("<@") and string.endswith(">") and string[2:-1].isdigit()


class Helper:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        load_dotenv()
        self.Guild = get(bot.guilds, id=int(os.environ['GUILD_ID']))
        self.TextGamesCategory = get(self.Guild.categories, id=int(os.environ['TEXT_GAMES_CATEGORY_ID']))
        self.ArchiveCategory = get(self.Guild.categories, id=int(os.environ['ARCHIVE_CATEGORY_ID']))
        self.ModRole = get(self.Guild.roles, id=int(os.environ['DOOMSAYER_ROLE_ID']))
        self.LogChannel = get(self.Guild.channels, id=int(os.environ['LOG_CHANNEL_ID']))
        self.StorageLocation = os.environ['STORAGE_LOCATION']

    def get_game_channel(self, number: str) -> nextcord.TextChannel:
        for channel in self.TextGamesCategory.channels:
            if number in channel.name and "x" + number not in channel.name:
                return channel

    def get_kibitz_channel(self, number: str) -> nextcord.TextChannel:
        if number[0] == "x":
            name = "experimental-kibitz-" + number[1:]
        else:
            name = "kibitz-game-" + number
        return get(self.Guild.channels, name=name)

    def get_game_role(self, number: str) -> nextcord.Role:
        name = "game" + number
        return get(self.Guild.roles, name=name)

    def get_st_role(self, number: str) -> nextcord.Role:
        name = "st" + number
        return get(self.Guild.roles, name=name)

    def get_kibitz_role(self, number: str) -> nextcord.Role:
        name = "kibitz" + number
        return get(self.Guild.roles, name=name)

    def authorize_st_command(self, author: nextcord.Member, game_number: str):
        return (self.ModRole in author.roles) \
            or (self.get_st_role(game_number) in author.roles) \
            or (author.id == OwnerID)

    def authorize_mod_command(self, author):
        return (self.ModRole in author.roles) or (author.id == OwnerID)

    async def finish_processing(self, ctx):
        await ctx.message.remove_reaction(WorkingEmoji, self.bot.user)
        await ctx.message.add_reaction(CompletedEmoji)
        print(f"-= The {ctx.command.name} command was used successfully by " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    async def log(self, log_string: str):
        await self.LogChannel.send(log_string)

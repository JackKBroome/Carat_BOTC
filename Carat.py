import contextlib
import os
import sys
import traceback
from contextlib import contextmanager

import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands
from nextcord.ext.commands import DefaultHelpCommand, CommandError

import utility
from Cogs.Archive import Archive
from Cogs.Game import Game
from Cogs.Grimoire import Grimoire
from Cogs.Other import Other
from Cogs.TextQueue import TextQueue
from Cogs.Signup import Signup
from Cogs.Users import Users
from Cogs.Townsquare import Townsquare
from utility import Helper

load_dotenv()
token = os.environ['TOKEN']

intents = nextcord.Intents.all()
allowedMentions = nextcord.AllowedMentions.all()
allowedMentions.everyone = False
help_command = DefaultHelpCommand(verify_checks=False, dm_help=None, dm_help_threshold=600)

bot = commands.Bot(command_prefix=">",
                   case_insensitive=True,
                   intents=intents,
                   allowed_mentions=allowedMentions,
                   activity=nextcord.Game(">HelpMe or >help"),
                   help_command=help_command)


# load cogs and print ready message
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('Loading cogs')
    helper = Helper(bot)
    bot.add_cog(Archive(bot, helper))
    bot.add_cog(Game(bot, helper))
    bot.add_cog(Grimoire(bot, helper))
    bot.add_cog(Other(bot, helper))
    bot.add_cog(TextQueue(bot, helper))
    bot.add_cog(Signup(bot, helper))
    bot.add_cog(Users(bot, helper))
    votes_cog = Townsquare(bot, helper)
    await votes_cog.load_emoji()
    bot.add_cog(votes_cog)
    print('Ready')
    print('------')


@bot.event
async def on_command_error(ctx: commands.Context, error: CommandError):
    if isinstance(error, commands.CommandNotFound):
        # filter out emoji like >.> by checking if first character after > is a letter
        if ctx.message.content[1].isalnum() and not ctx.message.content[1].isdigit():
            await utility.dm_user(ctx.author, "Command not found. Use >help for a list of commands, "
                                              "or >HelpMe for a list of commands with explanations.")
    elif isinstance(error, commands.UserInputError):
        await utility.dm_user(ctx.author, f"There was an issue with your input. Usage: "
                                          f"`>{ctx.command.name} {ctx.command.signature}`.")
    else:
        print("An error occurred: " + str(error))
        traceback.print_exception(type(error), error, error.__traceback__)


@bot.command
async def ReloadCogs(ctx: commands.Context):
    if ctx.author.id == utility.OwnerID:
        await ctx.message.add_reaction(utility.WorkingEmoji)
        #TODO: downlaod and reload cogs
        await ctx.message.add_reaction(utility.CompletedEmoji)
    else:
        await utility.deny_command(ctx)


with open("logs.txt", "w") as logfile:
    with contextlib.redirect_stderr(logfile):
        bot.run(token)

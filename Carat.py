import os

import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands
from nextcord.ext.commands import DefaultHelpCommand

import utility
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

bot = commands.Bot(command_prefix=">",
                   case_insensitive=True,
                   intents=intents,
                   allowed_mentions=allowedMentions,
                   activity=nextcord.Game(">HelpMe or >help"),
                   help_command=DefaultHelpCommand(verify_checks=False))


# load cogs and print ready message
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('Loading cogs')
    helper = Helper(bot)
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
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        await utility.dm_user(ctx.author, "Command not found. Use >help for a list of commands, "
                                          "or >HelpMe for a list of commands with explanations.")
    if isinstance(error, commands.UserInputError):
        await utility.dm_user(ctx.author, f"There was an issue with your input. Usage: "
                                          f"`>{ctx.command.name} {ctx.command.signature}`.")
    else:
        print("An error occurred: " + str(error))

bot.run(token)

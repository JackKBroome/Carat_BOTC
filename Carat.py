import os

import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands

from Cogs.Game import Game
from Cogs.Grimoire import Grimoire
from Cogs.Other import Other
from Cogs.TextQueue import TextQueue
from Cogs.Signup import Signup
from Cogs.Users import Users
from Cogs.Votes import Votes
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
                   activity=nextcord.Game(">HelpMe or >help"))


# Output in terminal when bot turns on
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
    bot.add_cog(Votes(bot, helper))
    print('Ready')
    print('------')


bot.run(token)

from nextcord.ext import commands

import utility


class Queue(commands.Cog):
    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper

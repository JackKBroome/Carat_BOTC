from time import strftime, gmtime

import nextcord
from nextcord.ext import commands

import utility


class Votes(commands.Cog):
    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper

    @commands.command()
    async def SetupTownsquare(self, ctx: commands.Context, game_number, players: commands.Greedy[nextcord.Member]):
        pass

    @commands.command()
    async def Nominate(self, ctx: commands.Context, game_number, nominator: nextcord.Member, nominee: nextcord.Member):
        pass

    @commands.command()
    async def Vote(self, ctx: commands.Context, nomination: str, vote: str):
        pass

    @commands.command()
    async def PrivateVote(self, ctx: commands.Context, nomination: str, vote: str):
        pass

    @commands.command()
    async def CountVotes(self, ctx: commands.Context, nomination: str):
        pass


class CountVoteView(nextcord.ui.View):
    def __init__(self):
        super().__init__()

    @nextcord.ui.button(label="Count as yes", custom_id="yes", style=nextcord.ButtonStyle.green)
    def vote_yes_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        pass

    @nextcord.ui.button(label="Count as no", custom_id="no", style=nextcord.ButtonStyle.red)
    def vote_no_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        pass

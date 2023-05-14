import json
import os
import typing
from time import strftime, gmtime

import nextcord
from nextcord.ext import commands
from nextcord.utils import get

import utility


class Votes(commands.Cog):
    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper
        self.TownSquaresStorage = os.path.join(self.helper.StorageLocation, "townsquares.json")
        try:
            with open(self.TownSquaresStorage, 'r') as f:
                self.town_squares: dict = json.load(f)
        except OSError:
            self.town_squares: dict = {}
            with open(self.TownSquaresStorage, 'w') as f:
                json.dump(self.town_squares, f)

    def update_storage(self):
        with open(self.TownSquaresStorage, 'w') as f:
            json.dump(self.town_squares, f)

    @commands.command()
    async def SetupTownSquare(self, ctx: commands.Context, game_number: str, players: commands.Greedy[nextcord.Member]):
        if self.helper.authorize_st_command(ctx.author, game_number):
            player_list = [{"id": p.id, "can_vote": True} for p in players]
            self.town_squares[game_number] = {"Players": player_list, "Nominations": []}
        else:
            await utility.deny_command(ctx, "SetupTownSquare")
            await utility.dm_user(ctx.author, "You are not the storyteller for this game")
        await self.helper.log(f"{ctx.author.mention} has run the SetupTownSquare command for game {game_number}")

    @commands.command()
    async def SetNomThread(self, ctx: commands.Context, game_number: str, thread: nextcord.Thread):
        if self.helper.authorize_st_command(ctx.author, game_number):
            self.town_squares[game_number]["NomThread"] = thread.id
        else:
            await utility.deny_command(ctx, "SetNomThread")
            await utility.dm_user(ctx.author, "You are not the storyteller for this game")
        await self.helper.log(f"{ctx.author.mention} has run the SetNomThread command for game {game_number}")

    @commands.command()
    async def Nominate(self, ctx: commands.Context, game_number: str,
                       nominee: nextcord.Member, nominator: typing.Optional[nextcord.Member]):
        game_role = self.helper.get_game_role(game_number)
        st_role = self.helper.get_st_role(game_number)
        can_nominate = self.helper.authorize_st_command(ctx.author, game_number) or game_role in ctx.author.roles
        if not can_nominate:
            await utility.deny_command(ctx, "Nominate")
            await utility.dm_user("You must participate in the game to nominate!")
        elif not self.helper.authorize_st_command(ctx.author, game_number) and nominator and nominator != ctx.author:
            await utility.deny_command(ctx, "Nominate")
            await utility.dm_user("You may not nominate in the name of others")
        elif nominator and game_role not in nominator.roles and st_role not in nominator.roles:  # Bishop allows ST to nominate
            await utility.deny_command(ctx, "Nominate")
            await utility.dm_user("The nominator must be a game participant")
        elif game_role not in nominee.roles and st_role not in nominee.roles:  # Atheist allows ST to be nominated
            await utility.deny_command(ctx, "Nominate")
            await utility.dm_user("The nominee must be a game participant")
        else:
            if not nominator:
                nominator = ctx.author
            self.town_squares[game_number]["Nominations"].add({"Nominator": nominator, "Nominee": nominee, "Votes": []})
            nom_thread = get(self.helper.Guild.threads, id=self.town_squares[game_number]["NomThread"])
            players = [get(self.helper.Guild.members, id=player_id) for player_id in self.town_squares[game_number]["Players"]]
            reordered_players = players[players.index(nominee) + 1:] + players[:players.index(nominee) + 1]
            embed = nextcord.Embed(title=f"{nominator.display_name} has nominated {nominee.display_name}",
                                   color=0xff0000)
            for player in reordered_players:
                name = player.display_name + " (Nominator)" if player == nominator else player.display_name
                embed.add_field(name=name,
                                value="-",
                                inline=True)
            nom_message = await nom_thread.send(embed=embed)

        await self.helper.log(f"{ctx.author.mention} has run the Nominate command in {ctx.channel.mention}")




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

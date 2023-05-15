import json
import os
from typing import List, Optional, Dict

import nextcord
from nextcord.ext import commands
from nextcord.utils import get
from dataclasses import dataclass
from dataclasses_json import dataclass_json

import utility


@dataclass_json
@dataclass
class Player:
    id: int
    alias: str
    can_vote: bool


@dataclass_json
@dataclass
class Nomination:
    nominator: int
    nominee: int
    votes: Dict[str, str]


@dataclass_json
@dataclass
class TownSquare:
    players: List[Player]
    nomination_thread: Optional[int]
    nominations: List[Nomination]
    organ_grinder: bool


class Votes(commands.Cog):
    bot: commands.Bot
    helper: utility.Helper
    TownSquaresStorage: str
    town_squares: Dict[str, TownSquare]

    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper
        self.TownSquaresStorage = os.path.join(self.helper.StorageLocation, "townsquares.json")
        if not os.path.exists(self.TownSquaresStorage):
            self.town_squares = {}
            self.update_storage()
        else:
            self.town_squares = {}
            with open(self.TownSquaresStorage, 'r') as f:
                json_data = json.load(f)
                for game in json_data:
                    self.town_squares[game] = json_data[game].from_dict()

    def update_storage(self):
        json_data = {}
        for game in self.town_squares:
            json_data[game] = self.town_squares[game].to_dict()
        with open(self.TownSquaresStorage, 'w') as f:
            json.dump(json_data, f)

    @commands.command()
    async def SetupTownSquare(self, ctx: commands.Context, game_number: str, players: commands.Greedy[nextcord.Member]):
        if self.helper.authorize_st_command(ctx.author, game_number):
            player_list = [Player(p.id, p.display_name, True) for p in players]
            self.town_squares[game_number] = TownSquare(player_list, None, [], False)
            self.update_storage()
        else:
            await utility.deny_command(ctx, "SetupTownSquare")
            await utility.dm_user(ctx.author, "You are not the storyteller for this game")
        await self.helper.log(f"{ctx.author.mention} has run the SetupTownSquare command for game {game_number}")

    @commands.command()
    async def SetNomThread(self, ctx: commands.Context, game_number: str, thread: nextcord.Thread):
        if self.helper.authorize_st_command(ctx.author, game_number):
            self.town_squares[game_number].nomination_thread = thread.id
        else:
            await utility.deny_command(ctx, "SetNomThread")
            await utility.dm_user(ctx.author, "You are not the storyteller for this game")
        await self.helper.log(f"{ctx.author.mention} has run the SetNomThread command for game {game_number}")

    @commands.command()
    async def Nominate(self, ctx: commands.Context, game_number: str,
                       nominee: nextcord.Member, nominator: Optional[nextcord.Member]):

        game_role = self.helper.get_game_role(game_number)
        st_role = self.helper.get_st_role(game_number)

        # check permission
        can_nominate = self.helper.authorize_st_command(ctx.author, game_number) or game_role in ctx.author.roles
        if not can_nominate:
            await utility.deny_command(ctx, "Nominate")
            await utility.dm_user(ctx.author, "You must participate in the game to nominate!")
        elif not self.helper.authorize_st_command(ctx.author, game_number) and nominator and nominator != ctx.author:
            await utility.deny_command(ctx, "Nominate")
            await utility.dm_user(ctx.author, "You may not nominate in the name of others")
        elif nominator and game_role not in nominator.roles and st_role not in nominator.roles:  # Bishop allows ST to nominate
            await utility.deny_command(ctx, "Nominate")
            await utility.dm_user(ctx.author, "The nominator must be a game participant")
        elif game_role not in nominee.roles and st_role not in nominee.roles:  # Atheist allows ST to be nominated
            await utility.deny_command(ctx, "Nominate")
            await utility.dm_user(ctx.author, "The nominee must be a game participant")
        else:
            # run command
            if not nominator:
                nominator = ctx.author
            self.town_squares[game_number].nominations.append(Nomination(nominator.id, nominee.id, {}))
            nom_thread = get(self.helper.Guild.threads, id=self.town_squares[game_number].nomination_thread)
            player_names = [p.alias for p in self.town_squares[game_number].players]
            if nominee.id in [p.id for p in self.town_squares[game_number].players:
                last_vote_index = next((i for i in range(len(player_names)) if self.town_squares[game_number].players[i].id == nominee.id))
                reordered_players = players[players.index(nominee) + 1:] + players[:players.index(nominee) + 1]
            else:
                reordered_players = players[players.index(nominator) + 1:] + players[:players.index(nominator) + 1]
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

    @commands.command()
    async def SetAlias(self, ctx: commands.Context, game_number: str, alias: str):
        pass

    @commands.command()
    async def ToggleOrganGrinder(self, ctx: commands.Context, game_number: str):
        pass

    async def TogglePlayerNoms(self, ctx: commands.Context, game_number: str):
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

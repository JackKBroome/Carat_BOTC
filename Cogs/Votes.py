import json
import os
from time import strftime, gmtime
from typing import List, Optional, Dict, Union

import nextcord
from nextcord.ext import commands
from nextcord.utils import get
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json

import utility

see_no_evil_emoji = '\U0001F648'
voted_yes_emoji = '\U00002705'
voted_no_emoji = '\U0000274C'


@dataclass_json
@dataclass
class Player:
    id: int
    alias: str
    can_vote: bool = True
    dead: bool = False


@dataclass_json
@dataclass
class Nomination:
    nominator: Player
    nominee: Player
    votes: Dict[Player, str]
    accusation: str = "TBD"
    defense: str = "TBD"
    message: int = None
    finished: bool = False


@dataclass_json
@dataclass
class TownSquare:
    players: List[Player]
    sts: List[Player]
    nominations: List[Nomination] = field(default_factory=list)
    nomination_thread: int = None
    log_thread: int = None
    organ_grinder: bool = False


def format_nom_message(game_role: nextcord.Role, nom: Nomination, organ_grinder: bool) -> (str, nextcord.Embed):
    if nom.nominee.id in [p.id for p in nom.players]:
        last_vote_index = next(i for i, player in enumerate(nom.players) if player.id == nom.nominee.id)
    elif nom.nominator.id in [p.id for p in nom.players]:
        last_vote_index = next(i for i, player in enumerate(nom.players) if player.id == nom.nominator.id)
    else:
        last_vote_index = len(nom.players) - 1
    reordered_players = nom.players[last_vote_index + 1:] + nom.players[:last_vote_index + 1]
    content = f"{game_role.mention} {nom.nominator.alias} has nominated {nom.nominee.alias}.\n" \
              f"Accusation: {nom.accusation}\n" \
              f"Defense: {nom.defense}"
    # TODO: add votes necessary for block, timeout
    embed = nextcord.Embed(title=Votes,
                           color=0xff0000)
    for player in reordered_players:
        name = player.alias + " (Nominator)" if player == nom.nominator else player.display_name
        embed.add_field(name=name, value=nom.votes[player] if not organ_grinder else see_no_evil_emoji, inline=True)
    return content, embed


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

    def get_log_thread(self, game_number: str) -> nextcord.Thread:
        kibitz = self.helper.get_kibitz_channel(game_number)
        return get(kibitz.threads, id=self.town_squares[game_number].log_thread)

    def update_nom_message(self, game_number: str, nom: Nomination):
        game_role = self.helper.get_game_role(game_number)
        content, embed = format_nom_message(game_role, nom, self.town_squares[game_number].organ_grinder)
        game_channel = self.helper.get_game_channel(game_number)
        nom_thread = get(game_channel.threads, id=self.town_squares[game_number].nomination_thread)
        nom_message = await nom_thread.fetch_message(nom.message)
        nom_message.edit(content=content, embed=embed)

    def get_game_participant(self, game_number: str, identifier: str) -> Union[nextcord.Member, None]:
        participants = self.town_squares[game_number].players + self.town_squares[game_number].sts
        if identifier[:2] == "<@" and identifier[-1] == ">":
            member = get(self.helper.Guild.members, id=int(identifier[2:-1]))
            if member and member.id in [p.id for p in participants]:
                return member
            else:
                return None
        # TODO: extract the following section and repeat for displayname/username
        matching_alias = [p for p in participants if identifier.lower() in p.alias.lower()]
        if len(matching_alias) > 1:
            matching_alias = [p for p in participants if p.alias.lower().startswith(identifier.lower())]
            if len(matching_alias) < 1:
                matching_alias = [p for p in participants if identifier in p.alias]
            elif len(matching_alias) > 1:
                matching_alias = [p for p in participants if p.alias.startswith(identifier)]
                if len(matching_alias) < 1:
                    matching_alias = [p for p in participants if p.alias.lower() == identifier.lower()]
                elif len(matching_alias) > 1:
                    matching_alias = [p for p in participants if p.alias == identifier]
        if len(matching_alias) > 1:
            return None
        if len(matching_alias) == 1:
            return get(self.helper.Guild.members, id=matching_alias[0].id)

    @commands.command()
    async def SetupTownSquare(self, ctx: commands.Context, game_number: str, players: commands.Greedy[nextcord.Member]):
        if self.helper.authorize_st_command(ctx.author, game_number):
            player_list = [Player(p.id, p.display_name) for p in players]
            st_list = [Player(st.id, st.display_name) for st in self.helper.get_st_role(game_number).members]
            self.town_squares[game_number] = TownSquare(player_list, st_list)
            kibitz = self.helper.get_kibitz_channel(game_number)
            log_thread = await kibitz.create_thread(
                name="Nomination & Vote Logging Thread",
                auto_archive_duration=4320,
                type=nextcord.ChannelType.public_thread)
            for st in self.helper.get_st_role(game_number).members:
                await log_thread.add_user(st)
            self.town_squares[game_number].log_thread = log_thread.id
            self.update_storage()
        else:
            await utility.deny_command(ctx, "SetupTownSquare")
            await utility.dm_user(ctx.author, "You are not the storyteller for this game")
        await self.helper.log(f"{ctx.author.mention} has run the SetupTownSquare command for game {game_number}")

    @commands.command()
    async def SetNomThread(self, ctx: commands.Context, game_number: str, thread: nextcord.Thread):
        if self.helper.authorize_st_command(ctx.author, game_number):
            self.town_squares[game_number].nomination_thread = thread.id
            self.update_storage()
        else:
            await utility.deny_command(ctx, "SetNomThread")
            await utility.dm_user(ctx.author, "You are not the storyteller for this game")
        await self.helper.log(f"{ctx.author.mention} has run the SetNomThread command for game {game_number}")

    @commands.command()
    async def Nominate(self, ctx: commands.Context, game_number: str,
                       nominee: nextcord.Member, nominator: Optional[nextcord.Member]):

        time = gmtime()
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
            # TODO: check no running nomination exists
        else:
            # run command
            if not nominator:
                nominator = ctx.author
            converted_nominee = next(
                player for player in self.town_squares[game_number].players if player.id == nominee.id)
            converted_nominator = next(
                player for player in self.town_squares[game_number].players if player.id == nominator.id)
            votes = {}
            for player in self.town_squares[game_number].players:
                votes[player] = "-"
            nom = Nomination(converted_nominator, converted_nominee, votes)

            embed, content = format_nom_message(game_role, nom, self.town_squares[game_number].organ_grinder)
            nom_thread = get(self.helper.Guild.threads, id=self.town_squares[game_number].nomination_thread)
            nom_message = await nom_thread.send(content=content, embed=embed)
            nom.message = nom_message.id
            self.town_squares[game_number].nominations.append(nom)
            self.update_storage()
            log_thread = self.get_log_thread(game_number)
            if nominator.id == ctx.author.id:
                await log_thread.send(f"{converted_nominator.alias} ({nominator.name}) has nominated "
                                      f"{converted_nominee.alias} ({nominee.name}) "
                                      f"at {str(strftime('%a, %d %b %Y %H:%M:%S ', time))}")

        await self.helper.log(f"{ctx.author.mention} has run the Nominate command in {ctx.channel.mention}")

    @commands.command()
    async def AddAccusation(self, ctx: commands.Context, game_number: str, accusation: str,
                            nominee_identifier: Optional[str]):
        if nominee_identifier:
            nominee = self.get_game_participant(game_number, nominee_identifier)
            nom = next(n for n in self.town_squares[game_number].nominations if n.nominee == nominee)
        else:
            nom = next(n for n in self.town_squares[game_number].nominations
                       if n.nominator.id == ctx.author.id)
        if ctx.author.id == nom.nominator.id or self.helper.authorize_st_command(ctx.author, game_number):
            nom.accusation = accusation

            self.update_nom_message(game_number, nom)
            self.update_storage()
        else:
            await utility.deny_command(ctx, "AddAccusation")
            await utility.dm_user(ctx.author, "You must be the ST or nominator to use this command")

    @commands.command()
    async def AddDefense(self, ctx: commands.Context, game_number: str, defense: str,
                         nominee_identifier: Optional[str]):
        if nominee_identifier:
            nominee = self.get_game_participant(game_number, nominee_identifier)
            nom = next(n for n in self.town_squares[game_number].nominations if n.nominee == nominee)
        else:
            nom = next(n for n in self.town_squares[game_number].nominations if n.nominee.id == ctx.author.id)
        if ctx.author.id == nom.nominator.id or self.helper.authorize_st_command(ctx.author, game_number):
            nom.defense = defense
            self.update_storage()
        else:
            await utility.deny_command(ctx, "AddAccusation")
            await utility.dm_user(ctx.author, "You must be the ST or nominator to use this command")

    @commands.command()
    async def Vote(self, ctx: commands.Context, game_number: str, nominee_identifier: str, vote: str):
        game_role = self.helper.get_game_role(game_number)
        if game_role in ctx.author.roles:
            nominee = self.get_game_participant(game_number, nominee_identifier)
            nom = next(n for n in self.town_squares[game_number].nominations if n.nominee == nominee)
            voter = next(p for p in self.town_squares[game_number].players if p.id == ctx.author.id)
            # TODO: check vote isn't a reserved emoji, check voter can vote?
            nom.votes[voter] = vote
            self.update_storage()

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

    @commands.command()
    async def TogglePlayerNoms(self, ctx: commands.Context, game_number: str):
        pass

    @commands.command()
    async def ToggleMarkedDead(self, ctx: commands.Context, game_number: str, player_identifier: str):
        pass

    @commands.command()
    async def ToggleCanVote(self, ctx: commands.Context, game_number: str, player_identifier: str):
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

    @nextcord.ui.button(label="Count triple", custom_id="bureaucrat", style=nextcord.ButtonStyle.grey)
    def bureaucrat_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        pass

    @nextcord.ui.button(label="Count negative", custom_id="thief", style=nextcord.ButtonStyle.grey)
    def thief_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        pass

    @nextcord.ui.button(label="Should be dead", custom_id="die", style=nextcord.ButtonStyle.grey)
    def die_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        pass

    @nextcord.ui.button(label="loses vote", custom_id="deadvote", style=nextcord.ButtonStyle.grey)
    def deadvote_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        pass

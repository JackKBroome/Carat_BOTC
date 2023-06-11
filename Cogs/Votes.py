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
dead_emoji = ''
clock_emoji = '\U000023F0'
bureaucrat_emoji = '\U0001F9D1'
thief_emoji = '\U0001F9B9'


@dataclass_json
@dataclass
class Player:
    id: int
    alias: str
    can_vote: bool = True
    dead: bool = False

    def __eq__(self, other):
        return isinstance(other, (Player, nextcord.User, nextcord.Member)) and self.id == other.id


@dataclass_json
@dataclass
class Nomination:
    nominator: Player
    nominee: Player
    votes: Dict[Player, str]
    private_votes: Dict[Player, str]
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


def format_nom_message(game_role: nextcord.Role, town_square: TownSquare, nom: Nomination, organ_grinder: bool) -> (
        str, nextcord.Embed):
    content = f"{game_role.mention} {nom.nominator.alias} has nominated {nom.nominee.alias}.\n" \
              f"Accusation: {nom.accusation}\n" \
              f"Defense: {nom.defense}"
    # TODO: add votes necessary for block, timeout
    embed = nextcord.Embed(title=Votes,
                           color=0xff0000)
    for player in reordered_players(nom, town_square):
        name = player.alias + " (Nominator)" if player == nom.nominator else player.display_name
        # vote_display =
        # TODO: handle private votes???
        embed.add_field(name=name, value=nom.votes[player] if not organ_grinder else see_no_evil_emoji, inline=True)
    return content, embed


def reordered_players(nom: Nomination, town_square: TownSquare) -> List[Player]:
    if nom.nominee in town_square.players:
        last_vote_index = next(i for i, player in enumerate(town_square.players) if player == nom.nominee)
    elif nom.nominator in town_square.players:
        last_vote_index = next(i for i, player in enumerate(town_square.players) if player == nom.nominator)
    else:
        last_vote_index = len(town_square.players) - 1
    return town_square.players[last_vote_index + 1:] + town_square.players[:last_vote_index + 1]


# TODO: check all relevant commands include start_processing, finish calls, log/update state correctly, handle next() exceptions, verify nom existence etc
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

    async def update_nom_message(self, game_number: str, nom: Nomination):
        game_role = self.helper.get_game_role(game_number)
        content, embed = format_nom_message(game_role, nom, self.town_squares[game_number].organ_grinder)
        game_channel = self.helper.get_game_channel(game_number)
        nom_thread = get(game_channel.threads, id=self.town_squares[game_number].nomination_thread)
        nom_message = await nom_thread.fetch_message(nom.message)
        await nom_message.edit(content=content, embed=embed)

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
    async def UpdateTownSquare(self, ctx: commands.Context, game_number: str,
                               players: commands.Greedy[nextcord.Member]):
        if self.helper.authorize_st_command(ctx.author, game_number):
            player_list = [Player(p.id, p.display_name) for p in players]

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
                player for player in self.town_squares[game_number].players if player == nominee)
            converted_nominator = next(
                player for player in self.town_squares[game_number].players if player == nominator)
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
            if nominator == ctx.author.id:
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
            self.update_storage()
            await self.update_nom_message(game_number, nom)
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
            await self.update_nom_message(game_number, nom)
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
            # TODO: check vote isn't a reserved string, check voter can vote?
            nom.votes[voter] = vote
            self.update_storage()
            await self.update_nom_message(game_number, nom)
        else:
            await utility.deny_command(ctx, "Vote")
            await utility.dm_user(ctx.author,
                                  "You must be a player to vote. If you are, the ST may have to add you to the townsquare.")

    @commands.command()
    async def PrivateVote(self, ctx: commands.Context, game_number: str, nominee_identifier: str, vote: str):
        game_role = self.helper.get_game_role(game_number)
        if game_role in ctx.author.roles:
            # TODO
            pass
        else:
            await utility.deny_command(ctx, "Vote")
            await utility.dm_user(ctx.author,
                                  "You must be a player to vote. If you are, the ST may have to add you to the townsquare.")

    @commands.command()
    async def CountVotes(self, ctx: commands.Context, game_number: str, nominee_identifier: str,
                         override: Optional[str]):
        if self.helper.authorize_st_command(ctx.author, game_number):
            if not override == "public" and ctx.channel in self.helper.TextGamesCategory.channels:
                await utility.dm_user(ctx.author,
                                      'Vote counting should probably not happen in public, or private prevotes might '
                                      'be exposed. If you want to do so anyway, run the command again with `public` '
                                      'added at the end')
                return
            nominee = self.get_game_participant(game_number, nominee_identifier)
            nom = next(n for n in self.town_squares[game_number].nominations if n.nominee == nominee)
            await ctx.send(content="`Count as yes` and `Count as no` will lock the current player's vote in, "
                                   "update the public nomination message and proceed to the next player. Click one of "
                                   "them to begin with the first player. Any other button will not lock the vote in, "
                                   "allowing you to make further adjustments.",
                           view=CountVoteView(self, self.town_squares[game_number], nom, ctx.author))
        else:
            await utility.deny_command(ctx, "CountVotes")
            await utility.dm_user(ctx.author, "You must be the Storyteller to count the votes for a nomination")

    @commands.command()
    async def SetAlias(self, ctx: commands.Context, game_number: str, alias: str):
        game_role = self.helper.get_game_role(game_number)
        if game_role in ctx.author.roles:
            player = next(p for p in self.town_squares[game_number].players if p.id == ctx.author.id)
            player.alias = alias
            self.update_storage()
        else:
            await utility.deny_command(ctx, "SetAlias")
            await utility.dm_user(ctx.author,
                                  "You must be a player to set your alias. If you are, the ST may have to add you to the townsquare.")

    @commands.command()
    async def ToggleOrganGrinder(self, ctx: commands.Context, game_number: str):
        if self.helper.authorize_st_command(ctx.author, game_number):
            self.town_squares[game_number].organ_grinder = not self.town_squares[game_number].organ_grinder
            self.update_storage()
            await utility.dm_user(ctx.author, f"Organ Grinder is now "
                                              f"{'enabled' if self.town_squares[game_number].organ_grinder else 'disabled'}")
        else:
            await utility.deny_command(ctx, "ToggleOrganGrinder")
            await utility.dm_user(ctx.author, "You must be the Storyteller to toggle the Organ Grinder")

    @commands.command()
    async def TogglePlayerNoms(self, ctx: commands.Context, game_number: str):
        pass

    @commands.command()
    async def ToggleMarkedDead(self, ctx: commands.Context, game_number: str, player_identifier: str):
        if self.helper.authorize_st_command(ctx.author, game_number):
            player_user = self.get_game_participant(game_number, player_identifier)
            if not player_user:
                await utility.deny_command(ctx, "ToggleMarkedDead")
                await utility.dm_user(ctx.author, f"Could not find player with identifier {player_identifier}")
                return
            player = next(p for p in self.town_squares[game_number].players if p.id == player_user.id)
            player.dead = not player.dead
            self.update_storage()
            await utility.dm_user(ctx.author, f"{player.alias} is now "
                                              f"{'marked as dead' if player.dead else 'marked as living'}")
        else:
            await utility.deny_command(ctx, "ToggleMarkedDead")
            await utility.dm_user(ctx.author, "You must be the Storyteller to mark a player as dead")

    @commands.command()
    async def ToggleCanVote(self, ctx: commands.Context, game_number: str, player_identifier: str):
        if self.helper.authorize_st_command(ctx.author, game_number):
            player_user = self.get_game_participant(game_number, player_identifier)
            if not player_user:
                await utility.deny_command(ctx, "ToggleCanVote")
                await utility.dm_user(ctx.author, f"Could not find player with identifier {player_identifier}")
                return
            player = next(p for p in self.town_squares[game_number].players if p.id == player_user.id)
            player.can_vote = not player.can_vote
            self.update_storage()
            await utility.dm_user(ctx.author, f"{player.alias} can now "
                                              f"{'vote' if player.can_vote else 'not vote'}")
        else:
            await utility.deny_command(ctx, "ToggleCanVote")
            await utility.dm_user(ctx.author, "You must be the Storyteller to toggle a player's voting ability")


class CountVoteView(nextcord.ui.View):
    cog: Votes
    game_number: str
    nom: Nomination
    author: nextcord.Member
    player_list: list[Player]
    player_index: int = -1
    bureaucrat: bool = False
    thief: bool = False

    def __init__(self, votes_cog: Votes, town_square: TownSquare, nom: Nomination, author: nextcord.Member,
                 game_number: str):
        super().__init__()
        self.cog = votes_cog
        self.nom = nom
        self.author = author
        self.player_list = reordered_players(self.nom, town_square)
        self.game_number = game_number

    # executed when a button is clicked, if it returns False no callback function is called
    async def interaction_check(self, interaction: nextcord.Interaction):
        if not interaction.user == self.author:
            return False
        if self.player_index == -1:
            self.player_index = 0
            await self.update_message(interaction.message)
            return False
        return True

    async def update_message(self, message: nextcord.Message):
        content = f"Nominator: {self.nom.nominator.alias}, Nominee: {self.player_list[self.player_index].alias}"
        for index, player in enumerate(self.player_list):
            if not player.can_vote and not self.nom.votes[player] == voted_yes_emoji:
                line = f"~~{player.alias}~~"
            else:
                line = f"{player.alias}: " \
                       f"{self.nom.private_votes[player] if player in self.nom.private_votes else self.nom.votes[player]}"
            if player.dead:
                line = f"{dead_emoji}{line}"
            if player == self.player_list[self.player_index]:
                if self.bureaucrat:
                    line = f"{bureaucrat_emoji}{line}"
                if self.thief:
                    line = f"{thief_emoji}{line}"
                line = f"{clock_emoji}**{line}**"
            content += f"\n{line}"
        await message.edit(content=content)

    @nextcord.ui.button(label="Count as yes", custom_id="yes", style=nextcord.ButtonStyle.green, row=1)
    def vote_yes_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        vote = voted_yes_emoji
        if self.bureaucrat:
            vote = bureaucrat_emoji + vote
        if self.thief:
            vote = thief_emoji + vote
        self.nom.private_votes.pop(self.player_list[self.player_index], None)
        self.nom.votes[self.player_list[self.player_index]] = vote
        await self.update_message(interaction.message)
        await self.cog.update_nom_message(self.game_number, self.nom)
        self.cog.update_storage()

    @nextcord.ui.button(label="Count as no", custom_id="no", style=nextcord.ButtonStyle.red, row=1)
    def vote_no_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        vote = voted_no_emoji
        if self.bureaucrat:
            vote = bureaucrat_emoji + vote
        if self.thief:
            vote = thief_emoji + vote
        self.nom.private_votes.pop(self.player_list[self.player_index], None)
        self.nom.votes[self.player_list[self.player_index]] = vote
        await self.update_message(interaction.message)
        await self.cog.update_nom_message(self.game_number, self.nom)
        self.cog.update_storage()
        await self.update_message(interaction.message)

    @nextcord.ui.button(label="Count triple", custom_id="bureaucrat", style=nextcord.ButtonStyle.grey, row=1)
    def bureaucrat_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.bureaucrat = not self.bureaucrat
        button.style = nextcord.ButtonStyle.blurple if self.bureaucrat else nextcord.ButtonStyle.grey
        await interaction.response.edit_message(view=interaction.message.view)

    @nextcord.ui.button(label="Count negative", custom_id="thief", style=nextcord.ButtonStyle.grey, row=1)
    def thief_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.thief = not self.thief
        button.style = nextcord.ButtonStyle.blurple if self.thief else nextcord.ButtonStyle.grey
        await interaction.response.edit_message(view=interaction.message.view)

    @nextcord.ui.button(label="Should be dead", custom_id="die", style=nextcord.ButtonStyle.grey, row=2)
    def die_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        town_square = self.cog.town_squares[self.game_number]
        town_square_index = next(
            i for i, player in enumerate(town_square.players) if player == self.player_list[self.player_index])
        town_square.players[town_square_index].dead = True
        self.cog.update_storage()
        await self.update_message(interaction.message)

    @nextcord.ui.button(label="Loses vote", custom_id="deadvote", style=nextcord.ButtonStyle.grey, row=2)
    def deadvote_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        town_square = self.cog.town_squares[self.game_number]
        town_square_index = next(
            i for i, player in enumerate(town_square.players) if player == self.player_list[self.player_index])
        town_square.players[town_square_index].can_vote = False
        self.cog.update_storage()
        await self.update_message(interaction.message)

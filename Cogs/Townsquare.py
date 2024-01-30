from __future__ import annotations
import datetime
import io
import json
import logging
import os
import traceback
from dataclasses import dataclass, field
from math import ceil
from typing import List, Optional, Dict, Union, Callable, Literal

import nextcord
from dataclasses_json import dataclass_json
from nextcord.ext import commands
from nextcord.utils import get, utcnow, format_dt

import utility

not_voted_yet = "-"
confirmed_yes_vote = "confirmed_yes_vote"
confirmed_no_vote = "confirmed_no_vote"
voted_yes_emoji = '\U00002705'  # ✅
voted_no_emoji = '\U0000274C'  # ❌
clock_emoji = '\U0001f566'  # 🕦


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
class Vote:
    vote: str
    bureaucrat: bool = False
    thief: bool = False


@dataclass_json
@dataclass
class Nomination:
    nominator: Player
    nominee: Player
    votes: Dict[int, Vote]
    deadline: str
    private_votes: Dict[int, str] = field(default_factory=dict)
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
    default_nomination_duration: int = 86400  # 1 day
    player_noms_allowed: bool = True
    vote_threshold: int = 0


def format_nom_message(game_role: nextcord.Role, town_square: TownSquare, nom: Nomination,
                       emoji: Dict[str, nextcord.PartialEmoji]) -> (
        str, nextcord.Embed):
    if town_square.vote_threshold == 0:
        votes_needed = ceil(len([player for player in town_square.players if not player.dead]) / 2)
    else:
        votes_needed = town_square.vote_threshold
    players = reordered_players(nom, town_square)
    current_voter = next((player for player in players if player.can_vote and
                          nom.votes[player.id].vote not in [confirmed_yes_vote, confirmed_no_vote]), None)
    content = f"{game_role.mention} {nom.nominator.alias} has nominated {nom.nominee.alias}.\n" \
              f"Accusation: {nom.accusation}\n" \
              f"Defense: {nom.defense}\n" \
              f"Votes close {nom.deadline}. " \
              f"{votes_needed} votes required to put {nom.nominee.alias} on the block.\n"
    embed = nextcord.Embed(title="Votes",
                           color=0xff0000)
    counter = 0
    for player in players:
        name = player.alias + " (Nominator)" if player == nom.nominator else player.alias
        if player.dead:
            name = str(emoji["shroud"]) + " " + name
        if player == current_voter:
            name = clock_emoji + " " + name
        vote = nom.votes[player.id]
        if (not player.can_vote) and vote != confirmed_yes_vote:
            embed.add_field(name=f"~~{name}~~", value="", inline=True)
        else:
            if town_square.organ_grinder:
                embed.add_field(name=name,
                                value=str(emoji["organ_grinder"]),
                                inline=False)
            elif vote.vote == confirmed_yes_vote:
                value = 1
                if vote.thief:
                    value *= -1
                if vote.bureaucrat:
                    value *= 3
                counter += value
                embed.add_field(name=name,
                                value=f"{voted_yes_emoji} ({counter}/{votes_needed})",
                                inline=False)
            elif vote.vote == confirmed_no_vote:
                embed.add_field(name=name,
                                value=voted_no_emoji,
                                inline=False)
            else:
                embed.add_field(name=name,
                                value=nom.votes[player.id].vote,
                                inline=False)
    return content, embed


def reordered_players(nom: Nomination, town_square: TownSquare) -> List[Player]:
    if nom.nominee in town_square.players:
        last_vote_index = next(i for i, player in enumerate(town_square.players) if player == nom.nominee)
    elif nom.nominator in town_square.players:
        last_vote_index = next(i for i, player in enumerate(town_square.players) if player == nom.nominator)
    else:
        last_vote_index = len(town_square.players) - 1
    return town_square.players[last_vote_index + 1:] + town_square.players[:last_vote_index + 1]


class Townsquare(commands.Cog):
    bot: commands.Bot
    helper: utility.Helper
    TownSquaresStorage: str
    town_squares: Dict[str, TownSquare]
    emoji: Dict[str, nextcord.PartialEmoji]
    vote_count_views: List[CountVoteView]

    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper
        self.TownSquaresStorage = os.path.join(self.helper.StorageLocation, "townsquares.json")
        self.emoji = {}
        self.vote_count_views = []
        self.town_squares = {}
        if not os.path.exists(self.TownSquaresStorage):
            self.update_storage()
        else:
            with open(self.TownSquaresStorage, 'r') as f:
                json_data = json.load(f)
                for game in json_data:
                    self.town_squares[game] = TownSquare.from_dict(json_data[game])

    async def load_emoji(self):
        self.emoji = {}
        shroud_emoji = get(self.helper.Guild.emojis, name="shroud")
        if shroud_emoji is not None:
            self.emoji["shroud"] = nextcord.PartialEmoji.from_str('{emoji.name}:{emoji.id}'.format(emoji=shroud_emoji))
        else:
            self.emoji["shroud"] = nextcord.PartialEmoji.from_str('\U0001F480')  # 💀
            await self.helper.log("Shroud emoji not found, using default")
        thief_emoji = get(self.helper.Guild.emojis, name="thief")
        if thief_emoji is not None:
            self.emoji["thief"] = nextcord.PartialEmoji.from_str('{emoji.name}:{emoji.id}'.format(emoji=thief_emoji))
        else:
            self.emoji["thief"] = nextcord.PartialEmoji.from_str('\U0001F48E')  # 💎
            await self.helper.log("Thief emoji not found, using default")
        bureaucrat_emoji = get(self.helper.Guild.emojis, name="bureaucrat")
        if bureaucrat_emoji is not None:
            self.emoji["bureaucrat"] = nextcord.PartialEmoji.from_str(
                '{emoji.name}:{emoji.id}'.format(emoji=bureaucrat_emoji))
        else:
            self.emoji["bureaucrat"] = nextcord.PartialEmoji.from_str('\U0001f4ce')  # 📎
            await self.helper.log("Bureaucrat emoji not found, using default")
        organ_grinder_emoji = get(self.helper.Guild.emojis, name="organ_grinder")
        if organ_grinder_emoji is not None:
            self.emoji["organ_grinder"] = nextcord.PartialEmoji.from_str(
                '{emoji.name}:{emoji.id}'.format(emoji=organ_grinder_emoji))
        else:
            self.emoji["organ_grinder"] = nextcord.PartialEmoji.from_str('\U0001f648')  # 🙈
            await self.helper.log("Organ grinder emoji not found, using default")

    def update_storage(self):
        json_data = {}
        for game in self.town_squares:
            json_data[game] = self.town_squares[game].to_dict()
        with open(self.TownSquaresStorage, 'w') as f:
            json.dump(json_data, f)

    async def log(self, game_number: str, message: str):
        kibitz = self.helper.get_kibitz_channel(game_number)
        log_thread = get(kibitz.threads, id=self.town_squares[game_number].log_thread)
        await log_thread.send((format_dt(utcnow()) + ": " + message)[:2000])

    async def update_nom_message(self, game_number: str, nom: Nomination):
        game_role = self.helper.get_game_role(game_number)
        content, embed = format_nom_message(game_role, self.town_squares[game_number], nom, self.emoji)
        game_channel = self.helper.get_game_channel(game_number)
        nom_thread = get(game_channel.threads, id=self.town_squares[game_number].nomination_thread)
        try:
            nom_message = await nom_thread.fetch_message(nom.message)
            await nom_message.edit(content=content, embed=embed)
        except nextcord.HTTPException as e:
            if e.code == 10008:  # Discord's 404
                logging.error(f"Missing message for nomination of {nom.nominee.alias} in game {game_number}")
                st_role = self.helper.get_st_role(game_number)
                await self.log(game_number, f"{st_role.mention} Could not find the nomination message for the "
                                            f"nomination of {nom.nominee.alias} to update it. Please close the "
                                            f"nomination to prevent this happening again.")
                return
            else:
                raise e
        view = next((v for v in self.vote_count_views if v.nom == nom), None)
        if view is not None:
            await view.update_message()
        logging.debug(f"Updated nomination for game {game_number}: {nom}")

    def get_game_participant(self, game_number: str, identifier: str) -> Union[nextcord.Member, None]:
        participants = self.town_squares[game_number].players + self.town_squares[game_number].sts
        # handle explicit mentions
        if utility.is_mention(identifier):
            member = get(self.helper.Guild.members, id=int(identifier[2:-1]))
            if member is not None and member.id in [p.id for p in participants]:
                return member
            else:
                return None
        # check alternatives for identifying the player
        alias_matches = self.try_get_matching_player(participants, identifier, lambda p: p.alias)
        display_names = {p.id: get(self.helper.Guild.members, id=p.id).display_name for p in participants}
        display_name_matches = self.try_get_matching_player(participants, identifier, lambda p: display_names[p.id])
        usernames = {p.id: get(self.helper.Guild.members, id=p.id).name for p in participants}
        username_matches = self.try_get_matching_player(participants, identifier, lambda p: usernames[p.id])
        if len(alias_matches) == 1:
            target_id = alias_matches[0]
        elif len(alias_matches) > 1:
            if len(set(alias_matches).intersection(set(display_name_matches))) == 1:
                target_id = list(set(alias_matches).intersection(set(display_name_matches)))[0]
            elif len(set(alias_matches).intersection(set(username_matches))) == 1:
                target_id = list(set(alias_matches).intersection(set(username_matches)))[0]
            elif len(set(display_name_matches).intersection(set(display_name_matches)).intersection(
                    set(username_matches))) == 1:
                target_id = list(set(display_name_matches).intersection(set(display_name_matches)).intersection(
                    set(username_matches)))[0]
            else:
                return None
        elif len(display_name_matches) == 1:
            target_id = display_name_matches[0]
        elif len(display_name_matches) > 1:
            if len(set(display_name_matches).intersection(set(username_matches))) == 1:
                target_id = list(set(display_name_matches).intersection(set(username_matches)))[0]
            else:
                return None
        elif len(username_matches) == 1:
            target_id = username_matches[0]
        else:
            return None
        return get(self.helper.Guild.members, id=target_id)

    # runs before each command - checks a town square exists
    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.command.name in ["SetupTownSquare", "SubstitutePlayer"]:
            return True
        args = ctx.message.content.split(" ")
        if len(args) < 2:
            await utility.deny_command(ctx, "You must give a game number")
        elif args[1] not in self.town_squares:
            await utility.deny_command(ctx, "No town square for this game exists.")
            return False
        else:
            return True

    @staticmethod
    def try_get_matching_player(player_list: List[Player], identifier: str, attribute: Callable[[Player], str]) \
            -> List[int]:
        matches = [p.id for p in player_list if identifier.lower() in attribute(p).lower()]
        if len(matches) > 1:
            matches = [p.id for p in player_list if attribute(p).lower().startswith(identifier.lower())]
            if len(matches) < 1:
                matches = [p.id for p in player_list if identifier in attribute(p)]
            elif len(matches) > 1:
                matches = [p.id for p in player_list if attribute(p).startswith(identifier)]
                if len(matches) < 1:
                    matches = [p.id for p in player_list if attribute(p).lower() == identifier.lower()]
                elif len(matches) > 1:
                    matches = [p.id for p in player_list if attribute(p) == identifier]
        return matches

    @commands.command()
    async def SetupTownSquare(self, ctx: commands.Context, game_number: str, players: commands.Greedy[nextcord.Member]):
        """Creates the town square for the given game, with the given players.
        Ping them in order of seating.
        Overwrites information like nominations and votes if a town square existed already.
        Use UpdateTownSquare if that is not what you want."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            player_list = [Player(p.id, p.display_name) for p in players]
            st_list = [Player(st.id, st.display_name) for st in self.helper.get_st_role(game_number).members]
            self.town_squares[game_number] = TownSquare(player_list, st_list)
            kibitz = self.helper.get_kibitz_channel(game_number)
            try:
                log_thread = await kibitz.create_thread(
                    name="Nomination & Vote Logging Thread",
                    auto_archive_duration=4320,
                    type=nextcord.ChannelType.private_thread)
            except nextcord.HTTPException:
                old_logging_threads = [t for t in kibitz.threads if t.name == "Nomination & Vote Logging Thread"]
                old_logging_threads.sort(key=lambda t: t.create_timestamp)
                try:
                    await old_logging_threads[0].delete()
                    log_thread = await kibitz.create_thread(
                        name="Nomination & Vote Logging Thread",
                        auto_archive_duration=4320,
                        type=nextcord.ChannelType.private_thread)
                except nextcord.HTTPException:
                    self.town_squares.pop(game_number)
                    await utility.deny_command(ctx, "Failed to create logging thread.")
                    return
            for st in self.helper.get_st_role(game_number).members:
                await log_thread.add_user(st)
            self.town_squares[game_number].log_thread = log_thread.id
            await self.log(game_number, f"Town square created: {self.town_squares[game_number]}")
            self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You are not the storyteller for this game")

    @commands.command()
    async def UpdateTownSquare(self, ctx: commands.Context, game_number: str,
                               players: commands.Greedy[nextcord.Member]):
        """Updates the town square for the given game, with the given players.
        Ping them in order of seating.The difference to rerunning SetupTownSquare is that the latter will
        lose information like aliases, spent deadvotes, and nominations. UpdateTownSquare will not. However, it will
        stop nominations of or by players who are removed. If you need to prevent that, use SubstitutePlayer."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            new_player_list = [self.reuse_or_convert_player(p, game_number) for p in players]
            removed_players = [p for p in self.town_squares[game_number].players if p not in new_player_list]
            added_players = [p for p in new_player_list if p not in self.town_squares[game_number].players]
            self.town_squares[game_number].players = new_player_list
            for nom in [n for n in self.town_squares[game_number].nominations if not n.finished]:
                if nom.nominator in removed_players or nom.nominee in removed_players:
                    nom.finished = True
                for player in removed_players:
                    nom.votes.pop(player.id)
                for player in added_players:
                    nom.votes[player.id] = Vote(not_voted_yet)
                await self.update_nom_message(game_number, nom)
            self.update_storage()
            await utility.finish_processing(ctx)
            await self.log(game_number, f"{ctx.author.mention} has updated the town square: {new_player_list}")
        else:
            await utility.deny_command(ctx, "You are not the storyteller for this game")

    def reuse_or_convert_player(self, player: nextcord.Member, game_number: str) -> Player:
        existing_player = next((p for p in self.town_squares[game_number].players if p.id == player.id), None)
        if existing_player:
            return existing_player
        else:
            return Player(player.id, player.display_name)

    @commands.command(aliases=["SubPlayer"])
    async def SubstitutePlayer(self, ctx: commands.Context, game_number: str, player: nextcord.Member,
                               substitute: nextcord.Member):
        """Exchanges a player in the town square with a substitute.
        Transfers the position, status, nominations and votes of the exchanged player to the substitute, adds the
        substitute to all threads the exchanged player was in, and adds/removes the game role.
        Can be used without the town square."""
        if game_number not in self.town_squares:
            await self.SubstitutePlayerNoTownsquare(ctx, game_number, player, substitute)
            return
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            player_list = self.town_squares[game_number].players
            current_player = next((p for p in player_list if p.id == player.id), None)
            substitute_existing_player = next((p for p in player_list if p.id == substitute.id), None)
            if substitute_existing_player is not None:
                await utility.deny_command(ctx, f"{substitute.display_name} is already a player.")
                return
            if current_player is None:
                st_list = self.town_squares[game_number].sts
                current_st = next((st for st in st_list if st.id == player.id), None)
                if not current_st:
                    await utility.deny_command(ctx, f"{player.display_name} is not a participant.")
                    return
                current_st.id = substitute.id
                current_st.alias = substitute.display_name
            else:
                game_role = self.helper.get_game_role(game_number)
                await player.remove_roles(game_role, reason="substituted out")
                await substitute.add_roles(game_role, reason="substituted in")
                current_player.id = substitute.id
                current_player.alias = substitute.display_name
                game_channel = self.helper.get_game_channel(game_number)
                for thread in game_channel.threads:
                    thread_members = await thread.fetch_members()
                    if player in [tm.member for tm in thread_members]:
                        await thread.add_user(substitute)
                for nom in [n for n in self.town_squares[game_number].nominations if not n.finished]:
                    nom.votes[substitute.id] = nom.votes.pop(player.id)
                    await self.update_nom_message(game_number, nom)
            await self.log(game_number, f"{ctx.author.mention} has substituted {player.display_name} with "
                                        f"{substitute.display_name}")
            logging.debug(f"Substituted {player} with {substitute} in game {game_number} - "
                          f"current town square: {self.town_squares[game_number]}")
            self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You are not the storyteller for this game")

    async def SubstitutePlayerNoTownsquare(self, ctx: commands.Context, game_number: str, player: nextcord.Member,
                                           substitute: nextcord.Member):
        game_role = self.helper.get_game_role(game_number)
        if game_role not in player.roles:
            await utility.deny_command(ctx, f"{player.display_name} is not a player.")
            return
        elif game_role in substitute.roles:
            await utility.deny_command(ctx, f"{substitute.display_name} is already a player.")
            return
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            await player.remove_roles(game_role, reason="substituted out")
            await substitute.add_roles(game_role, reason="substituted in")
            game_channel = self.helper.get_game_channel(game_number)
            for thread in game_channel.threads:
                thread_members = await thread.fetch_members()
                if player in [tm.member for tm in thread_members]:
                    await thread.add_user(substitute)
            logging.debug(f"Substituted {player} with {substitute} in game {game_number}")
            self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You are not the storyteller for this game")

    @commands.command(aliases=["CreateNomThread", "CreateNominationsThread"])
    async def CreateNominationThread(self, ctx: commands.Context, game_number: str, name: Optional[str]):
        """Creates a thread for nominations to be run in.
        The name of the thread is optional, with `Nominations` as default."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            game_channel = self.helper.get_game_channel(game_number)
            thread = await game_channel.create_thread(name=name if name else "Nominations", auto_archive_duration=4320,
                                                      type=nextcord.ChannelType.public_thread)
            for st in self.helper.get_st_role(game_number).members:
                await thread.add_user(st)
            self.town_squares[game_number].nomination_thread = thread.id
            self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You are not the storyteller for this game")

    @commands.command()
    async def Nominate(self, ctx: commands.Context, game_number: str,
                       nominee_identifier: str, nominator_identifier: Optional[str]):
        """Create a nomination for the given nominee.
        If you are an ST, provide the nominator. If you are a player, leave the nominator out or give yourself.
        In either case, you don't need to ping, a name should work."""
        game_role = self.helper.get_game_role(game_number)
        # check permission
        can_nominate = self.helper.authorize_st_command(ctx.author, game_number) or game_role in ctx.author.roles
        nominee = self.get_game_participant(game_number, nominee_identifier)
        nominator = self.get_game_participant(game_number, nominator_identifier) if nominator_identifier else None
        nom_thread = get(self.helper.Guild.threads, id=self.town_squares[game_number].nomination_thread)
        if not can_nominate:
            await utility.deny_command(ctx, "You must participate in the game to nominate!")
        elif not self.helper.authorize_st_command(ctx.author,
                                                  game_number) and nominator and nominator.id != ctx.author.id:
            await utility.deny_command(ctx, "You may not nominate in the name of others")
        elif nominator_identifier and not nominator:
            await utility.deny_command(ctx, "The nominator must be a game participant")
        elif not nominee:  # Atheist allows ST to be nominated
            await utility.deny_command(ctx, "The nominee must be a game participant")
        elif not nom_thread:
            await utility.deny_command(ctx, "The nomination thread has not been created. Ask an ST to fix this.")
        elif any([nominee.id == nom.nominee.id and not nom.finished for nom in
                  self.town_squares[game_number].nominations]):
            await utility.deny_command(ctx, "That player has already been nominated")
        else:
            await utility.start_processing(ctx)
            participants = self.town_squares[game_number].players + self.town_squares[game_number].sts
            converted_nominee = next((p for p in participants if p.id == nominee.id), None)
            if not converted_nominee:
                await utility.deny_command(ctx,
                                           "The Nominee is not included in the town square. Ask an ST to fix this.")
            if not nominator_identifier:
                converted_nominator = next((p for p in participants if p.id == ctx.author.id), None)
            else:
                converted_nominator = next((p for p in participants if p.id == nominator.id), None)
            if not converted_nominator:
                await utility.deny_command(ctx,
                                           "The Nominator is not included in the town square. Ask an ST to fix this.")
            votes = {}
            for player in self.town_squares[game_number].players:
                votes[player.id] = Vote(not_voted_yet)
            deadline = utcnow() + datetime.timedelta(seconds=self.town_squares[game_number].default_nomination_duration)
            nom = Nomination(converted_nominator, converted_nominee, votes, format_dt(deadline, "R"))

            content, embed = format_nom_message(game_role, self.town_squares[game_number], nom, self.emoji)
            nom_message = await nom_thread.send(content=content, embed=embed)
            nom.message = nom_message.id
            self.town_squares[game_number].nominations.append(nom)
            logging.debug(f"Nomination created: in game {game_number}: {nom}")
            await utility.finish_processing(ctx)
            self.update_storage()
            await self.log(game_number, f"{converted_nominator.alias} has nominated {converted_nominee.alias}")

    @commands.command()
    async def AddAccusation(self, ctx: commands.Context, game_number: str, accusation: str,
                            nominee_identifier: Optional[str]):
        """Add an accusation to the nomination of the given nominee.
        You don't need to ping, a name should work. You must be the nominator or a storyteller for this."""
        if len(accusation) > 900:
            await utility.deny_command(ctx, "Your accusation is too long. Consider posting it in public and "
                                            "setting a link to the message as your accusation.")
            return
        await utility.start_processing(ctx)
        if nominee_identifier:
            nominee = self.get_game_participant(game_number, nominee_identifier)
            if not nominee:
                await utility.deny_command(ctx, f"Could not clearly identify any player from {nominee_identifier}")
                return
            nom = next((n for n in self.town_squares[game_number].nominations if
                        n.nominee.id == nominee.id and not n.finished), None)
        else:
            nom = next((n for n in self.town_squares[game_number].nominations
                        if n.nominator.id == ctx.author.id and not n.finished), None)
        if not nom:
            await utility.deny_command(ctx, f"No relevant nomination found for nominee {nominee_identifier}")
            return
        if ctx.author.id == nom.nominator.id or self.helper.authorize_st_command(ctx.author, game_number):
            nom.accusation = accusation
            self.update_storage()
            await self.update_nom_message(game_number, nom)
            await utility.finish_processing(ctx)
            await self.log(game_number, f"{ctx.author} has added this accusation to the nomination of "
                                        f"{nom.nominee.alias}: {accusation}")
        else:
            await utility.deny_command(ctx, "You must be the ST or nominator to use this command")

    @commands.command(aliases=["AddDefence"])
    async def AddDefense(self, ctx: commands.Context, game_number: str, defense: str,
                         nominee_identifier: Optional[str]):
        """Add a defense to your nomination or that of the given nominee.
        You must be a storyteller for the latter."""
        if len(defense) > 900:
            await utility.deny_command(ctx, "Your defense is too long. Consider posting it in public and "
                                            "setting a link to the message as your defense.")
            return
        await utility.start_processing(ctx)
        if nominee_identifier:
            nominee = self.get_game_participant(game_number, nominee_identifier)
            if not nominee:
                await utility.deny_command(ctx, f"Could not clearly identify any player from {nominee_identifier}")
                return
            nom = next((n for n in self.town_squares[game_number].nominations if
                        n.nominee.id == nominee.id and not n.finished), None)
        else:
            nom = next((n for n in self.town_squares[game_number].nominations if
                        n.nominee.id == ctx.author.id and not n.finished), None)
        if not nom:
            await utility.deny_command(ctx, f"No relevant nomination found for nominee {nominee_identifier}")
            return
        if ctx.author.id == nom.nominee.id or self.helper.authorize_st_command(ctx.author, game_number):
            nom.defense = defense
            self.update_storage()
            await self.update_nom_message(game_number, nom)
            await utility.finish_processing(ctx)
            await self.log(game_number,
                           f"{ctx.author} has added this defense to the nomination of {nom.nominee.alias}: {defense}")
        else:
            await utility.deny_command(ctx, "You must be the ST or nominee to use this command")

    @commands.command()
    async def SetVoteThreshold(self, ctx: commands.Context, game_number: str, target: int):
        """Set the vote threshold to put a player on the block to the given number.
        You must be a storyteller for this."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            if target < 0:
                await utility.deny_command(ctx, "Vote threshold cannot be negative")
                return
            self.town_squares[game_number].vote_threshold = target
            for nom in [nom for nom in self.town_squares[game_number].nominations if not nom.finished]:
                await self.update_nom_message(game_number, nom)
            self.update_storage()
            await utility.finish_processing(ctx)
            await self.log(game_number, f"{ctx.author} has set the vote threshold to {target}")

    @commands.command()
    async def SetDeadline(self, ctx: commands.Context, game_number: str, nominee_identifier: str, time_in_h: float):
        """Set the deadline for the nomination of a given nominee to the given number of hours from now.
        You must be a storyteller for this."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            time = datetime.timedelta(hours=time_in_h)
            if utcnow() + time < utcnow():
                await utility.deny_command(ctx, "Deadline must be in the future")
                return
            nominee = self.get_game_participant(game_number, nominee_identifier)
            if not nominee:
                await utility.deny_command(ctx, f"Could not clearly identify any player from {nominee_identifier}")
                return
            nom = next((n for n in self.town_squares[game_number].nominations if
                        n.nominee.id == nominee.id and not n.finished), None)
            if not nom:
                await utility.deny_command(ctx, f"No relevant nomination found for nominee {nominee_identifier}")
                return
            nom.deadline = format_dt(utcnow() + time, "R")
            self.update_storage()
            await self.update_nom_message(game_number, nom)
            await utility.finish_processing(ctx)
            await self.log(game_number, f"{ctx.author} has set the deadline for the nomination of {nom.nominee.alias} "
                                        f"to {format_dt(utcnow() + time)}")
        else:
            await utility.deny_command(ctx, "You must be the ST to use this command")

    @commands.command()
    async def SetDefaultDeadline(self, ctx: commands.Context, game_number: str, hours: int):
        """Set the default nomination duration for the game to the given number of hours.
        You must be a storyteller for this."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            if hours < 0:
                await utility.deny_command(ctx, "Deadline must be in the future")
                return
            self.town_squares[game_number].default_nomination_duration = hours * 3600
            self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You must be the ST to use this command")

    @commands.command(usage="<game number> [nominee]... [vote]")
    async def Vote(self, ctx: commands.Context, *args):
        """Set your vote for the given nominee or nominees.
        You don't need to ping, name(s) should work.
        Your vote can be anything, but should be something the ST can unambiguously interpret as yes or no when they count it.
        You can change your vote until it is counted by the storyteller."""
        if len(args) < 3:
            await utility.deny_command(ctx, "You must provide the game number, at least one nominee, and your vote")
            return
        game_number = args[0]
        vote = args[-1]
        nominee_identifiers = args[1:-1]
        game_role = self.helper.get_game_role(game_number)
        if not game_role:
            await utility.deny_command(ctx, f"Game '{game_number}' does not exist")
            return
        if len(vote) > 400:
            await utility.deny_command(ctx, "Your vote is too long. Consider simplifying your condition. If that is "
                                            "somehow impossible, just let the ST know.")
            return
        voter = next((p for p in self.town_squares[game_number].players if p.id == ctx.author.id), None)
        if self.town_squares[game_number].organ_grinder and (ctx.channel in self.helper.TextGamesCategory or
                                                             ctx.channel.type == nextcord.ChannelType.public_thread):
            await ctx.message.delete()
            await utility.dm_user(ctx.author, "Please do not vote in public while the Organ Grinder is active. Your "
                                              "vote was not registered.")
            await self.log(game_number, f"{voter.alias} tried to vote '{vote}' on {', '.join(nominee_identifiers)} in "
                                        f"public. Vote was not registered")
            return
        if not voter:
            await utility.deny_command(ctx, "You are not included in the town square. Ask the ST to correct this.")
            return
        if not voter.can_vote:
            await utility.deny_command(ctx, "You seem to have spent your vote already.")
            return
        if vote in [confirmed_yes_vote, confirmed_no_vote, not_voted_yet]:
            await utility.deny_command(ctx, "Nice try. That's a reserved string for internal handling, "
                                            "you cannot set your vote to it.")
            return
        if game_role in ctx.author.roles:
            await utility.start_processing(ctx)
            for nominee_identifier in nominee_identifiers:
                nominee = self.get_game_participant(game_number, nominee_identifier)
                if not nominee:
                    await utility.dm_user(ctx.author,
                                          f"Could not clearly identify any player from {nominee_identifier}")
                    continue
                nom = next((n for n in self.town_squares[game_number].nominations if
                            n.nominee.id == nominee.id and not n.finished), None)
                if not nom:
                    await utility.dm_user(ctx.author, f"No relevant nomination found for nominee {nominee_identifier}")
                    continue
                if nom.votes[voter.id].vote in [confirmed_yes_vote, confirmed_no_vote]:
                    await utility.dm_user(ctx.author, f"Your vote on {nominee_identifier} is already locked in and "
                                                      f"cannot be changed.")
                    continue
                nom.votes[voter.id] = Vote(vote)
                await self.update_nom_message(game_number, nom)
                await self.log(game_number,
                               f"{ctx.author} has set their vote on the nomination of {nom.nominee.alias} to {vote}")
            self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You must be a player to vote. "
                                            "If you are, the ST may have to add you to the town square.")

    @commands.command()
    async def PrivateVote(self, ctx: commands.Context, game_number: str, nominee_identifier: str, vote: str):
        """Same as >Vote, but your vote will be hidden from other players.
        They will still see whether you voted yes or no after your vote is counted. A private vote will always override
        any public vote, even later ones. If you want your public vote to be counted instead,
        you can change your private vote accordingly or use >RemovePrivateVote."""
        game_role = self.helper.get_game_role(game_number)
        if game_role in ctx.author.roles:
            await utility.start_processing(ctx)
            nominee = self.get_game_participant(game_number, nominee_identifier)
            if not nominee:
                await utility.deny_command(ctx, f"Could not clearly identify any player from {nominee_identifier}")
                return
            nom = next((n for n in self.town_squares[game_number].nominations if
                        n.nominee.id == nominee.id and not n.finished), None)
            voter = next((p for p in self.town_squares[game_number].players if p.id == ctx.author.id), None)
            if not nom:
                await utility.deny_command(ctx, f"No relevant nomination found for nominee {nominee_identifier}")
                return
            if not voter:
                await utility.deny_command(ctx,
                                           "You are not included in the town square. Ask the ST to correct this.")
                return
            if nom.votes[voter.id].vote in [confirmed_yes_vote, confirmed_no_vote]:
                await utility.deny_command(ctx, "Your vote is already locked in and cannot be changed.")
                return
            if not voter.can_vote:
                await utility.deny_command(ctx, "You seem to have spent your vote already.")
                return
            if vote in [confirmed_yes_vote, confirmed_no_vote, not_voted_yet]:
                await utility.deny_command(ctx, "Nice try. That's a reserved string for internal handling, "
                                                "you cannot set your vote to it.")
                return
            nom.private_votes[voter.id] = vote
            self.update_storage()
            await utility.finish_processing(ctx)
            await self.log(game_number,
                           f"{ctx.author} has set a private vote on the nomination of {nom.nominee.alias} as {vote}")
        else:
            await utility.deny_command(ctx, "You must be a player to vote. "
                                            "If you are, the ST may have to add you to the town square.")

    @commands.command()
    async def RemovePrivateVote(self, ctx: commands.Context, game_number: str, nominee_identifier: str):
        """Removes your private vote for the given nominee, so that your public vote is counted instead."""
        game_role = self.helper.get_game_role(game_number)
        if game_role in ctx.author.roles:
            await utility.start_processing(ctx)
            nominee = self.get_game_participant(game_number, nominee_identifier)
            if not nominee:
                await utility.deny_command(ctx, f"Could not clearly identify any player from {nominee_identifier}")
                return
            nom = next((n for n in self.town_squares[game_number].nominations if
                        n.nominee.id == nominee.id and not n.finished), None)
            voter = next((p for p in self.town_squares[game_number].players if p.id == ctx.author.id), None)
            if not nom:
                await utility.deny_command(ctx, f"No relevant nomination found for nominee {nominee_identifier}")
                return
            if not voter:
                await utility.deny_command(ctx,
                                           "You are not included in the town square. Ask the ST to correct this.")
                return
            private_vote = nom.private_votes.pop(voter.id, None)
            self.update_storage()
            await utility.finish_processing(ctx)
            if private_vote:
                await utility.dm_user(ctx.author, f"Your private vote on the nomination of {nom.nominee.alias} "
                                                  f"has been removed.")
            else:
                await utility.dm_user(ctx.author, f"You have no private vote on the nomination of {nom.nominee.alias}.")
            await self.log(game_number,
                           f'{ctx.author} has removed their private vote, "{private_vote}", '
                           f'on the nomination of {nom.nominee.alias}')
        else:
            await utility.deny_command(ctx, "You must be a player to vote. "
                                            "If you are, the ST may have to add you to the town square.")

    @commands.command()
    async def CountVotes(self, ctx: commands.Context, game_number: str, nominee_identifier: str,
                         override: Optional[Literal["public"]] = None):
        """Begins counting the votes for the given nominee.
        You must be a storyteller for this."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            if override is None and (ctx.channel in self.helper.TextGamesCategory.channels or
                                     (isinstance(ctx.channel, nextcord.Thread) and
                                      ctx.channel.parent in self.helper.TextGamesCategory.channels)):
                await utility.deny_command(ctx,
                                           'Vote counting should probably not happen in public, or private prevotes '
                                           'might be exposed. If you want to do so anyway, run the command again with '
                                           '`public` added at the end')
                return
            nominee = self.get_game_participant(game_number, nominee_identifier)
            if not nominee:
                await utility.deny_command(ctx, f"Could not clearly identify any player from {nominee_identifier}")
                return
            nom = next((n for n in self.town_squares[game_number].nominations if
                        n.nominee.id == nominee.id and not n.finished), None)
            if not nom:
                await utility.deny_command(ctx, f"No relevant nomination found for nominee {nominee_identifier}")
                return
            view = CountVoteView(self, nom, ctx.author, game_number, self.emoji)
            message = await ctx.send(content="`Count as yes` and `Count as no` will lock the current player's vote in, "
                                             "update the public nomination message and proceed to the next player. "
                                             "Any other button will not lock the vote in, allowing you to make "
                                             "further adjustments. Click any button to begin",
                                     view=view)
            view.message = message
            self.vote_count_views.append(view)
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You must be the Storyteller to count the votes for a nomination")

    @commands.command()
    async def SetVote(self, ctx: commands.Context, game_number: str, nominee_identifier: str, voter_identifier: str,
                      vote: Optional[str]):
        """Sets the vote on the given nominee for the given voter to the given vote. If no vote is given, it is simply
        reset. You must be a storyteller for this. Note that you cannot lock a vote in this way."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            nominee = self.get_game_participant(game_number, nominee_identifier)
            if not nominee:
                await utility.deny_command(ctx, f"Could not clearly identify any player from {nominee_identifier}")
                return
            voter = self.get_game_participant(game_number, voter_identifier)
            if not voter:
                await utility.deny_command(ctx, f"Could not clearly identify any player from {voter_identifier}")
                return
            nom = next((n for n in self.town_squares[game_number].nominations if
                        n.nominee.id == nominee.id and not n.finished), None)
            if not nom:
                await utility.deny_command(ctx, f"No relevant nomination found for nominee {nominee_identifier}")
                return
            if not vote:
                vote = not_voted_yet
            nom.votes[voter.id] = Vote(vote)
            await self.update_nom_message(game_number, nom)
            await utility.finish_processing(ctx)
            await self.log(game_number, f"{ctx.author} has set the vote of {voter.name} on the nomination of "
                                        f"{nom.nominee.alias}")
        else:
            await utility.deny_command(ctx, "You must be the Storyteller to reset a vote")

    @commands.command(aliases=["CloseNom"])
    async def CloseNomination(self, ctx: commands.Context, game_number: str, nominee_identifier: str):
        """Marks the nomination for the given nominee as closed.
        You must be a storyteller for this."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            nominee = self.get_game_participant(game_number, nominee_identifier)
            if not nominee:
                await utility.deny_command(ctx, f"Could not clearly identify any player from {nominee_identifier}")
                return
            nom = next((n for n in self.town_squares[game_number].nominations if
                        n.nominee.id == nominee.id and not n.finished), None)
            if not nom:
                await utility.deny_command(ctx, f"No relevant nomination found for nominee {nominee_identifier}")
                return
            else:
                nom.finished = True
                self.update_storage()
                await utility.finish_processing(ctx)
                await self.log(game_number, f"{ctx.author} has closed the nomination of {nom.nominee.alias}")
        else:
            await utility.deny_command(ctx, "You must be the Storyteller to close a nomination")

    @commands.command()
    async def SetAlias(self, ctx: commands.Context, game_number: str, alias: str):
        """Set your preferred alias for the given game.
        This will be used anytime the bot refers to you. The default is your username.
        Can be used by players and storytellers."""
        game_role = self.helper.get_game_role(game_number)
        st_role = self.helper.get_st_role(game_number)
        if len(alias) > 100 or utility.is_mention(alias):
            await utility.deny_command(ctx, f"not an allowed alias: {alias}"[:2000])
            return
        if game_role in ctx.author.roles:
            await utility.start_processing(ctx)
            player = next((p for p in self.town_squares[game_number].players if p.id == ctx.author.id), None)
            if not player:
                await utility.deny_command(ctx,
                                           "You are not included in the town square. Ask the ST to correct this.")
                return
            player.alias = alias
            self.update_storage()
            await self.log(game_number, f"{ctx.author.name} has set their alias to {alias}")
            await utility.finish_processing(ctx)
        elif st_role in ctx.author.roles:
            await utility.start_processing(ctx)
            st = next((st for st in self.town_squares[game_number].sts if st.id == ctx.author.id), None)
            if not st:
                await utility.deny_command(ctx, "Something went wrong and you are not included in the townsquare. "
                                                "Try dropping and re-adding the grimoire")
                return
            st.alias = alias
            self.update_storage()
            await utility.finish_processing(ctx)
            await self.log(game_number, f"{ctx.author.name} has set their alias to {alias}")
        else:
            await utility.deny_command(ctx, "You must be a player to set your alias. "
                                            "If you are, the ST may have to add you to the town square.")

    @commands.command()
    async def ToggleOrganGrinder(self, ctx: commands.Context, game_number: str):
        """Activates or deactivates Organ Grinder for the display of nominations in the game.
        Finished nominations are not updated.
        You must be a storyteller for this."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            self.town_squares[game_number].organ_grinder = not self.town_squares[game_number].organ_grinder
            self.update_storage()
            for nom in self.town_squares[game_number].nominations:
                if not nom.finished:
                    await self.update_nom_message(game_number, nom)
            await utility.finish_processing(ctx)
            await utility.dm_user(ctx.author, f"Organ Grinder is now "
                                              f"{'enabled' if self.town_squares[game_number].organ_grinder else 'disabled'}")
        else:
            await utility.deny_command(ctx, "You must be the Storyteller to toggle the Organ Grinder")

    @commands.command()
    async def TogglePlayerNoms(self, ctx: commands.Context, game_number: str):
        """Activates or deactivates the ability of players to nominate directly.
        You must be a storyteller for this."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            if game_number not in self.town_squares:
                await utility.deny_command(ctx, "Town square not set up yet.")
                return
            self.town_squares[game_number].player_noms_allowed = not self.town_squares[game_number].player_noms_allowed
            self.update_storage()
            await utility.finish_processing(ctx)
            await utility.dm_user(ctx.author,
                                  f"Player nominations are now "
                                  f"{'enabled' if self.town_squares[game_number].player_noms_allowed else 'disabled'}")
        else:
            await utility.deny_command(ctx, "You must be the Storyteller to toggle player nominations")

    @commands.command()
    async def ToggleMarkedDead(self, ctx: commands.Context, game_number: str, player_identifier: str):
        """Marks the given player as dead or alive for display on nominations.
        You must be a storyteller for this."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            player_user = self.get_game_participant(game_number, player_identifier)
            if not player_user:
                await utility.deny_command(ctx, f"Could not find player with identifier {player_identifier}")
                return
            player = next((p for p in self.town_squares[game_number].players if p.id == player_user.id), None)
            if not player:
                await utility.deny_command(ctx, f"{player_user.display_name} is not included in the town square.")
                return
            player.dead = not player.dead
            self.update_storage()
            await utility.finish_processing(ctx)
            await utility.dm_user(ctx.author, f"{player.alias} is now "
                                              f"{'marked as dead' if player.dead else 'marked as living'}")
            await self.log(game_number, f"{ctx.author} has marked {player.alias} as "
                                        f"{'dead' if player.dead else 'living'}")
        else:
            await utility.deny_command(ctx, "You must be the Storyteller to mark a player as dead")

    @commands.command()
    async def ToggleCanVote(self, ctx: commands.Context, game_number: str, player_identifier: str):
        """Allows or disallows the given player to vote.
        You must be a storyteller for this."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            player_user = self.get_game_participant(game_number, player_identifier)
            if not player_user:
                await utility.deny_command(ctx, f"Could not clearly identify any player from {player_identifier}")
                return
            player = next((p for p in self.town_squares[game_number].players if p.id == player_user.id), None)
            if not player:
                await utility.deny_command(ctx, f"{player_user.display_name} is not included in the town square.")
                return
            player.can_vote = not player.can_vote
            self.update_storage()
            await utility.finish_processing(ctx)
            await utility.dm_user(ctx.author, f"{player.alias} can now "
                                              f"{'vote' if player.can_vote else 'not vote'}")
            await self.log(game_number, f"{ctx.author} has set {player.alias} as "
                                        f"{'able to vote' if player.can_vote else 'unable to vote'}")
        else:
            await utility.deny_command(ctx, "You must be the Storyteller to toggle a player's voting ability")


class CountVoteView(nextcord.ui.View):
    cog: Townsquare
    game_number: str
    nom: Nomination
    author: nextcord.Member
    emoji: Dict[str, nextcord.PartialEmoji]
    player_list: List[Player]
    player_index: int = -1
    message: nextcord.Message

    def __init__(self, votes_cog: Townsquare, nom: Nomination, author: nextcord.Member,
                 game_number: str, emoji: Dict[str, nextcord.PartialEmoji]):
        super().__init__()
        self.cog = votes_cog
        self.nom = nom
        self.author = author
        self.player_list = reordered_players(self.nom, self.cog.town_squares[game_number])
        self.game_number = game_number
        self.emoji = emoji
        self.timeout = 86400  # 24h

    async def on_error(self, error: Exception, item: nextcord.ui.Item, interaction: nextcord.Interaction) -> None:
        traceback_buffer = io.StringIO()
        traceback.print_exception(type(error), error, error.__traceback__, file=traceback_buffer)
        traceback_text = traceback_buffer.getvalue()
        logging.exception(f"Ignoring exception in CountVoteView:\n{traceback_text}")

    # executed when a button is clicked, if it returns False no callback function is called
    async def interaction_check(self, interaction: nextcord.Interaction):
        if not interaction.user == self.author:
            await interaction.send(ephemeral=True, content="Only the command's user may interact with this")
            return False
        return True

    async def check_initial(self):
        if self.player_index == -1:
            self.player_index = 0
            bureaucrat = next((item for item in self.children if item.custom_id == "bureaucrat"))
            bureaucrat.emoji = self.emoji["bureaucrat"]
            thief = next((item for item in self.children if item.custom_id == "thief"))
            thief.emoji = self.emoji["thief"]
            mark_dead = next((item for item in self.children if item.custom_id == "die"))
            mark_dead.emoji = self.emoji["shroud"]
            await self.update_message()
            return True
        return False

    async def update_message(self):
        content = f"Nominator: {self.nom.nominator.alias}, Nominee: {self.nom.nominee.alias}"
        for index, player in enumerate(self.player_list):
            line = player.alias
            if not player.can_vote and not self.nom.votes[player.id].vote == confirmed_yes_vote:
                line = f"~~{line}~~"
            elif self.nom.votes[player.id].vote == confirmed_yes_vote:
                line = f"{line}: {voted_yes_emoji}"
            elif self.nom.votes[player.id].vote == confirmed_no_vote:
                line = f"{line}: {voted_no_emoji}"
            else:
                line = f"{line}: " \
                       f"{self.nom.private_votes[player.id] if player.id in self.nom.private_votes else self.nom.votes[player.id].vote}"
            if player.dead:
                line = f"{self.emoji['shroud']}{line}"
            if index == self.player_index:
                if self.nom.votes[player.id].bureaucrat:
                    line = f"{self.emoji['bureaucrat']}{line}"
                if self.nom.votes[player.id].thief:
                    line = f"{self.emoji['thief']}{line}"
                line = f"{clock_emoji}**{line}**"
            content += f"\n{line}"
        await self.message.edit(content=content, view=self)

    async def lock_vote(self, vote: str):
        self.nom.private_votes.pop(self.player_list[self.player_index].id, None)
        self.nom.votes[self.player_list[self.player_index].id].vote = vote
        self.player_index += 1
        next((item for item in self.children if item.custom_id == "bureaucrat")).style = nextcord.ButtonStyle.grey
        next((item for item in self.children if item.custom_id == "thief")).style = nextcord.ButtonStyle.grey
        next((item for item in self.children if item.custom_id == "die")).disabled = False
        next((item for item in self.children if item.custom_id == "deadvote")).disabled = False
        if self.player_index >= len(self.player_list):
            self.nom.finished = True
            self.clear_items()
            self.stop()
            if self in self.cog.vote_count_views:
                self.cog.vote_count_views.remove(self)
        await self.update_message()
        await self.cog.update_nom_message(self.game_number, self.nom)
        self.cog.update_storage()

    @nextcord.ui.button(label="Count as yes", custom_id="yes", style=nextcord.ButtonStyle.green, row=1)
    async def vote_yes_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        if await self.check_initial():
            return
        await self.lock_vote(confirmed_yes_vote)
        await self.cog.log(self.game_number,
                           f"{self.author} locked vote of {self.player_list[self.player_index - 1].alias}"
                           f" on the nomination of {self.nom.nominee.alias} as yes")

    @nextcord.ui.button(label="Count as no", custom_id="no", style=nextcord.ButtonStyle.red, row=1)
    async def vote_no_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        if await self.check_initial():
            return
        await self.lock_vote(confirmed_no_vote)
        await self.cog.log(self.game_number,
                           f"{self.author} locked vote of {self.player_list[self.player_index - 1].alias}"
                           f" on the nomination of {self.nom.nominee.alias} as no")

    @nextcord.ui.button(label="Count triple", custom_id="bureaucrat", style=nextcord.ButtonStyle.grey, row=1)
    async def bureaucrat_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        if await self.check_initial():
            return
        vote = self.nom.votes[self.player_list[self.player_index].id]
        vote.bureaucrat = not vote.bureaucrat
        button.style = nextcord.ButtonStyle.blurple if vote.bureaucrat else nextcord.ButtonStyle.grey
        await self.update_message()

    @nextcord.ui.button(label="Count negative", custom_id="thief", style=nextcord.ButtonStyle.grey, row=1)
    async def thief_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        if await self.check_initial():
            return
        vote = self.nom.votes[self.player_list[self.player_index].id]
        vote.thief = not vote.thief
        button.style = nextcord.ButtonStyle.blurple if vote.thief else nextcord.ButtonStyle.grey
        await self.update_message()

    @nextcord.ui.button(label="Should be dead", custom_id="die", style=nextcord.ButtonStyle.grey, row=2)
    async def die_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        if await self.check_initial():
            return
        self.player_list[self.player_index].dead = True
        button.disabled = True
        self.cog.update_storage()
        await self.update_message()

    @nextcord.ui.button(label="Loses vote", custom_id="deadvote", style=nextcord.ButtonStyle.grey, row=2)
    async def deadvote_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        if await self.check_initial():
            return
        self.player_list[self.player_index].can_vote = False
        button.disabled = True
        self.cog.update_storage()
        await self.update_message()

    @nextcord.ui.button(label="Ping current player", custom_id="ping_current", style=nextcord.ButtonStyle.red, row=3)
    async def ping_current(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        if await self.check_initial():
            return
        player = get(self.cog.helper.Guild.members, id=self.player_list[self.player_index].id)
        nom_thread = get(self.cog.helper.get_game_channel(self.game_number).threads,
                         id=self.cog.town_squares[self.game_number].nomination_thread)
        await nom_thread.send(f"The clock in the nomination on {self.nom.nominee.alias} is on {player.mention}. "
                              f"Please vote at next opportunity.")

    @nextcord.ui.button(label="Ping all remaining", custom_id="ping_all", style=nextcord.ButtonStyle.red, row=3)
    async def ping_all_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        if await self.check_initial():
            return
        nom_thread = get(self.cog.helper.get_game_channel(self.game_number).threads,
                         id=self.cog.town_squares[self.game_number].nomination_thread)
        for player in [player for player in self.player_list if
                       player.can_vote and self.nom.votes[player.id].vote == not_voted_yet]:
            player_member = get(self.cog.helper.Guild.members, id=player.id)
            await nom_thread.send(f"{player_member.mention}, reminder: you have not yet voted on the nomination of "
                                  f"{self.nom.nominee.alias}")


async def setup(bot: commands.Bot):
    cog = Townsquare(bot, utility.Helper(bot))
    await cog.load_emoji()
    bot.add_cog(cog)

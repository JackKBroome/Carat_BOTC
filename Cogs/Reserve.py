import datetime
import io
import json
import logging
import os
import traceback
from dataclasses import dataclass, field
from datetime import date, timedelta, time
from typing import Optional, Dict, List

import nextcord
from dataclasses_json import dataclass_json
from nextcord.ext import commands, tasks
from nextcord.utils import get, utcnow, format_dt

import utility
from Cogs.TextQueue import TextQueue, Entry, ExplainInvalidChannelType

green_square_emoji = '\U0001F7E9'
red_square_emoji = '\U0001F7E5'
refresh_emoji = '\U0001F504'
min_advance_days = 14


@dataclass_json
@dataclass
class RSVPEntry:
    thread: int
    owner: int
    date: str
    min_players: int
    max_players: int = 0
    script: str = "TBA"
    co_sts: List[int] = field(default_factory=list)
    players: List[int] = field(default_factory=list)


def default_game_channel_overwrites(game_role: nextcord.Role, st_role: nextcord.Role, helper: utility.Helper) \
        -> Dict[nextcord.Role, nextcord.PermissionOverwrite]:
    permissions = {}
    total_ban_role = get(helper.Guild.roles, name="tb")
    if total_ban_role is not None:
        permissions[total_ban_role] = nextcord.PermissionOverwrite(send_messages=False, send_messages_in_threads=False,
                                                                   create_public_threads=False,
                                                                   create_private_threads=False, add_reactions=False)
    game_ban_role = get(helper.Guild.roles, name="gb")
    if game_ban_role is not None:
        permissions[game_ban_role] = nextcord.PermissionOverwrite(send_messages=False, view_channel=False)
    ni_text_role = get(helper.Guild.roles, name="NIText")
    if ni_text_role is not None:
        permissions[ni_text_role] = nextcord.PermissionOverwrite(view_channel=False)
    permissions[game_role] = nextcord.PermissionOverwrite(send_messages_in_threads=True, create_public_threads=False,
                                                          create_private_threads=True, manage_messages=True,
                                                          manage_threads=False)
    permissions[st_role] = nextcord.PermissionOverwrite(manage_channels=True, manage_permissions=True,
                                                        send_messages_in_threads=True, create_public_threads=True,
                                                        create_private_threads=True, manage_messages=True,
                                                        manage_threads=True)
    return permissions


async def default_kibitz_channel_overwrites(game_role: nextcord.Role,
                                            st_role: nextcord.Role,
                                            kibitz_role: nextcord.Role,
                                            helper: utility.Helper
                                            ) -> Dict[nextcord.Role, nextcord.PermissionOverwrite]:
    permissions = {}
    bot_role = get(helper.Guild, name=(await helper.bot.application_info()).name)
    permissions[bot_role] = nextcord.PermissionOverwrite(view_channel=True)
    total_ban_role = get(helper.Guild.roles, name="tb")
    if total_ban_role is not None:
        permissions[total_ban_role] = nextcord.PermissionOverwrite(send_messages=False, send_messages_in_threads=False,
                                                                   create_public_threads=False,
                                                                   create_private_threads=False, add_reactions=False)
    permissions[st_role] = nextcord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
    permissions[game_role] = nextcord.PermissionOverwrite(view_channel=False, send_messages=False)
    permissions[kibitz_role] = nextcord.PermissionOverwrite(view_channel=True, send_messages=True)
    blind_role = get(helper.Guild.roles, name="blind")
    if blind_role is not None:
        permissions[blind_role] = nextcord.PermissionOverwrite(view_channel=False)
    permissions[helper.Guild.default_role] = nextcord.PermissionOverwrite(view_channel=False)
    return permissions


def parse_date(inp: str) -> Optional[date]:
    try:
        # number of days
        days = int(inp)
        return date.today() + timedelta(days=days)
    except ValueError:
        try:
            # ISO 8601
            return date.fromisoformat(inp)
        except ValueError:
            try:
                # MM-DD
                split_date = inp.split("-")
                if len(split_date) == 2:
                    today = date.today()
                    target_date = date(today.year, int(split_date[0]), int(split_date[1]))
                    if target_date < today:
                        target_date = target_date.replace(year=today.year + 1)
                    return target_date
                else:
                    return None
            except ValueError as ve:
                logging.debug(f"Attempted to parse {inp} as date and failed: {ve}")
                return None


async def create_channel(owner: int, helper: utility.Helper,
                         script: str = "", co_sts: List[int] = None, players: List[int] = None):
    # find free game number
    # (will always find one because r-channels will never be every channel in text games category)
    game_number = "r" + str(next(i for i in range(1, len(helper.TextGamesCategory.channels))
                                 if helper.get_game_channel(f"r{i}") is None))
    reason = f"Preparing reserved game {game_number}"
    # get/create roles
    game_role = helper.get_game_role(game_number)
    if game_role is None:
        logging.warning(f"Creating game role for {game_number}")
        game_role = await helper.Guild.create_role(reason=reason, name=f"game{game_number}", mentionable=True)
    st_role = helper.get_st_role(game_number)
    if st_role is None:
        logging.warning(f"Creating ST role for {game_number}")
        st_role = await helper.Guild.create_role(reason=reason, name=f"st{game_number}", mentionable=True)
    kibitz_role = helper.get_kibitz_role(game_number)
    if kibitz_role is None:
        logging.warning(f"Creating kibitz role for {game_number}")
        kibitz_role = await helper.Guild.create_role(reason=reason,
                                                     name=f"kibitz{game_number}",
                                                     mentionable=True)
    # create game channel
    game_channel = await helper.TextGamesCategory.create_text_channel(
        f"{game_number}-starting-{script}",
        reason=reason,
        overwrites=default_game_channel_overwrites(game_role, st_role, helper)
    )
    # get/create kibitz channel
    kibitz_channel = helper.get_kibitz_channel(game_number)
    kibitz_overwrites = await default_kibitz_channel_overwrites(game_role, st_role, kibitz_role, helper)
    if kibitz_channel is None:
        logging.warning(f"Creating kibitz channel for {game_number}")
        kibitz_category = get(helper.Guild.categories, name="kibitz")
        if kibitz_category is not None:
            await kibitz_category.create_text_channel(
                f"rsvp-kibitz-{game_number[1:]}",
                reason=reason,
                overwrites=kibitz_overwrites
            )
        else:
            logging.error("Kibitz category not found")
    else:
        await kibitz_channel.edit(reason=reason, overwrites=kibitz_overwrites)
    # assign roles
    st = get(helper.Guild.members, id=owner)
    await st.add_roles(st_role)
    co_sts = [] if co_sts is None else co_sts
    co_sts = [get(helper.Guild.members, id=st_id) for st_id in co_sts]
    for co_st in co_sts:
        if co_st is not None:
            await co_st.add_roles(st_role)
    players = [] if players is None else players
    players = [(p_id, get(helper.Guild.members, id=p_id)) for p_id in players]
    for p_id, player in players:
        if player is None:
            game_channel.send(f"Warning: Player with ID {p_id} could not be found")
        else:
            player.add_roles(game_role)
    await game_channel.send(f"{st_role.mention} Channel is ready. Have fun!")
    logging.info(f"Setup for game {game_number} complete")


async def switch_to_queue(queue_cog: TextQueue, helper: utility.Helper, entry: RSVPEntry, channel_type: str,
                          availability="At next opportunity"):
    thread = get(helper.ReservingForum.threads, id=entry.thread)
    queue_entry = Entry(entry.owner, entry.script, availability,
                        f"See {thread.mention}")
    queue_cog.queues[channel_type].entries.append(queue_entry)
    full_queue_posted = await queue_cog.update_queue_message(queue_cog.queues[channel_type])
    if not full_queue_posted:
        await queue_cog.helper.log("Queue too long for message - final entry/entries not displayed")
    queue_cog.update_storage()
    pass


def signup_embed(entry: RSVPEntry, helper: utility.Helper) -> nextcord.Embed:
    owner = get(helper.Guild.members, id=entry.owner)
    co_sts = [get(helper.Guild.members, id=st_id).mention for st_id in entry.co_sts]
    embed = nextcord.Embed(title=str(entry.script),
                           description=f"Ran by {owner.mention} with" + ", ".join(co_sts) +
                                       f"\nPress {green_square_emoji} to sign up for the game"
                                       f"\nPress {red_square_emoji} to remove yourself from the game",
                           color=0xff0000)
    for i in range(entry.max_players):
        if i < len(entry.players):
            player = get(helper.Guild.members, id=entry.players[i])
            name = player.display_name
            embed.add_field(name=str(i + 1) + ". " + str(name),
                            value=f"{player.mention} has signed up",
                            inline=False)
        else:
            embed.add_field(name=str(i + 1) + ". ", value=" Awaiting Player", inline=False)
    return embed


class Reserve(commands.Cog):
    bot: commands.Bot
    helper: utility.Helper
    entries: Dict[int, RSVPEntry]
    announced: Dict[int, RSVPEntry]
    ReservedStorage: str

    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper
        self.bot.add_view(PreSignupView(self, helper, RSVPEntry(0, 0, "", 0)))  # registering views for persistence
        self.ReservedStorage = os.path.join(self.helper.StorageLocation, "reserved.json")
        self.entries = {}
        self.announced = {}
        if not os.path.exists(self.ReservedStorage):
            with open(self.ReservedStorage, 'w') as f:
                json.dump({"entries": self.entries, "announced": self.announced}, f, indent=2)
        else:
            with open(self.ReservedStorage, 'r') as f:
                json_data = json.load(f)
                for owner in json_data["entries"]:
                    self.entries[int(owner)] = RSVPEntry.from_dict(json_data["entries"][owner])
                for owner in json_data["announced"]:
                    self.announced[int(owner)] = RSVPEntry.from_dict(json_data["announced"][owner])
        self.check_entries.start()

    def cog_unload(self) -> None:
        self.check_entries.cancel()

    def update_storage(self):
        json_data = {"entries": {}, "announced": {}}
        for owner in self.entries:
            json_data["entries"][owner] = self.entries[owner].to_dict()
        for owner in self.announced:
            json_data["announced"][owner] = self.announced[owner].to_dict()
        with open(self.ReservedStorage, "w") as f:
            json.dump(json_data, f, indent=2)

    def remove_entry(self, owner: int):
        self.entries.pop(owner)
        self.update_storage()

    def remove_announced(self, owner: int):
        self.announced.pop(owner)
        self.update_storage()

    @commands.command()
    async def ReserveGame(self, ctx: commands.Context, min_players: int, start: Optional[str]):
        """Reserves a game for you to ST starting on the given start date.
        You also have to give the number of players you need for the game. Default and minimum for the date is 2 weeks
        after using the command. Accepted date formats are YYYY-MM-DD, MM-DD or the number of days until the date.
        To use the command, create a post in the text game forum for your game."""
        # check author has no entry currently
        if any(entry_owner == ctx.author.id for entry_owner in self.entries):
            await utility.deny_command(ctx, "You already have reserved a game")
            return
        queue_cog: Optional[TextQueue] = self.bot.get_cog("TextQueue")
        if queue_cog is not None and queue_cog.get_queue(ctx.author.id) is not None:
            await utility.deny_command(ctx, "You are already in the queue")
            return
        if start is None:
            start_date = date.today() + timedelta(days=min_advance_days)
        else:
            start_date = parse_date(start)
        if start_date is None:
            await utility.deny_command(ctx, "Invalid start date. Use either a number (of days) or YYYY-MM-DD "
                                            "or MM-DD format, or nothing to set to the earliest option")
            return
        if start_date - date.today() < timedelta(days=min_advance_days):
           await utility.deny_command(ctx, "Start date must be at least two weeks away")
           return
        if isinstance(ctx.channel, nextcord.Thread) and ctx.channel.parent == self.helper.ReservingForum \
                and ctx.author == ctx.channel.owner:
            await utility.start_processing(ctx)
            self.entries[ctx.author.id] = RSVPEntry(ctx.channel.id, ctx.author.id, start_date.isoformat(), min_players)
            self.update_storage()
            await utility.dm_user(ctx.author, f"Registered your entry for {start_date.isoformat()}")
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, f"You must create a post in {self.helper.ReservingForum.mention} and use "
                                            f"this command there to reserve a game")

    @commands.command()
    async def PreSignups(self, ctx: commands.Context, max_players: int, script: str):
        """Posts a message listing the signed up players in the post, with buttons that players can
        use to sign up or leave the game."""
        if ctx.author.id not in self.entries:
            await utility.deny_command(ctx, "You have not reserved a game")
        else:
            await utility.start_processing(ctx)
            entry = self.entries[ctx.author.id]
            entry.max_players = max_players
            entry.script = script
            self.update_storage()
            embed = signup_embed(entry, self.helper)
            thread = get(self.helper.ReservingForum.threads, id=entry.thread)
            await thread.send(embed=embed, view=PreSignupView(self, self.helper, entry))
            await utility.finish_processing(ctx)

    @commands.command()
    async def SwitchToQueue(self, ctx: commands.Context, channel_type: str, availability: Optional[str]):
        """Cancels your reserved game and joins one of the queues.
        You can specify your availability, by default it is the start date that was planned for the reserved game."""
        if ctx.author.id not in self.entries:
            await utility.deny_command(ctx, "You have not reserved a game")
        else:
            await utility.start_processing(ctx)
            channel_type = utility.get_channel_type(channel_type)
            if channel_type is None:
                await utility.deny_command(ctx, ExplainInvalidChannelType)
                return
            entry = self.entries[ctx.author.id]
            if availability is None:
                availability = f"Starting {entry.date}"
            queue_cog: Optional[TextQueue] = self.bot.get_cog("TextQueue")
            if queue_cog is None:
                await utility.deny_command(ctx, "Could not access queue")
                return
            await switch_to_queue(queue_cog, self.helper, entry, channel_type, availability)
            self.remove_entry(ctx.author.id)
            thread = get(self.helper.ReservingForum.threads, id=entry.thread)
            await thread.send(f"The game has been moved to the {channel_type} queue")
            await utility.finish_processing(ctx)

    @commands.command()
    async def CancelGame(self, ctx: commands.Context):
        """Cancels your reserved game."""
        if ctx.author.id not in self.entries:
            await utility.deny_command(ctx, "You have not reserved a game")
        elif ctx.channel.id != self.entries[ctx.author.id].thread:
            await utility.deny_command(ctx,
                                       "Please use the command in the game thread to ensure your players are aware")
        else:
            await utility.start_processing(ctx)
            self.remove_entry(ctx.author.id)
            await utility.finish_processing(ctx)

    @commands.command()
    async def ListNextGames(self, ctx: commands.Context, days: Optional[int] = 7):
        """Lists the reserved games starting in the next week, or in the next specified number of days"""
        await utility.start_processing(ctx)
        cutoff = date.today() + datetime.timedelta(days=days)
        upcoming = sorted([entry for entry in self.entries.values() if date.fromisoformat(entry.date) <= cutoff],
                          key=lambda e: e.date)
        embed = nextcord.Embed(title="Upcoming games",
                               description=f"All reserved games starting in the next {days} days")
        embed.set_thumbnail(self.helper.Guild.icon.url)
        for entry in upcoming:
            owner = get(self.helper.Guild.members, id=entry.owner)
            if owner is None:
                continue
            co_sts = [get(self.helper.Guild.members, id=co_st) for co_st in entry.co_sts]
            co_st_names = [co_st.display_name for co_st in co_sts if co_st is not None]
            name = f"{owner.display_name} running {entry.script}" if entry.script != "TBA" else f"{owner.mention}"
            description = f"{len(entry.players)}/{entry.min_players} players signed up"
            if entry.max_players != 0:
                description += f" (max {entry.max_players} players)"
            description += f"\n{get(self.helper.ReservingForum.threads, id=entry.thread).mention}"
            if len(co_st_names) > 0:
                description = "with " + ", ".join(co_st_names) + "\n" + description
            embed.add_field(name=name, value=description, inline=False)
        await ctx.message.reply(embed=embed)
        await utility.finish_processing(ctx)

    @commands.command()
    async def CreateRGame(self, ctx: commands.Context, st: nextcord.Member):
        """Creates an r-game channel with the given user as ST.
        If they have a game reserved, Carat uses the information from the entry, but it works even if they have not."""
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            if st.id in self.entries:
                entry = self.entries[st.id]
                await create_channel(entry.owner, self.helper, entry.script, entry.co_sts, entry.players)
                self.remove_entry(st.id)
            elif st.id in self.announced:
                entry = self.announced[st.id]
                await create_channel(entry.owner, self.helper, entry.script, entry.co_sts, entry.players)
                self.remove_announced(st.id)
            else:
                await create_channel(st.id, self.helper)
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You do not have permission to use this command")

    @commands.command()
    async def RemoveReservation(self, ctx: commands.Context, st: nextcord.Member):
        """Removes the reservation of the given member."""
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            if st.id in self.entries:
                self.remove_entry(st.id)
            elif st.id in self.announced:
                self.remove_announced(st.id)
            else:
                await utility.dm_user(ctx.author, f"No reservation for {st.display_name} found")
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You do not have permission to use this command")

    @commands.command()
    async def ChangeStartDate(self, ctx: commands.Context, st: nextcord.Member, new_date: str):
        """Updates the start date of the reservation of the given member.
        If the new start date is not in the future, the member will be notified with the next pings.
        If the old date was reached but the new date isn't, they will no longer be able to create a channel until the
        date is reached."""
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            start_day = parse_date(new_date)
            if start_day is None:
                await utility.deny_command(ctx, "Invalid start date. Use either a number (of days) or YYYY-MM-DD "
                                                "or MM-DD format")
                return
            if st.id in self.entries:
                entry = self.entries[st.id]
                entry.date = start_day.isoformat()
                self.update_storage()
            elif st.id in self.announced:
                if start_day > date.today():
                    entry = self.announced[st.id]
                    entry.date = start_day.isoformat()
                    self.entries[st.id] = entry
                    self.remove_announced(st.id)
                    # storage is updated as part of remove_announced
                else:
                    await utility.dm_user(ctx.author, f"The reserved game of {st.display_name} has already reached its "
                                                      f"start date")
            else:
                await utility.dm_user(ctx.author, f"{st.display_name} has no reserved game")
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You do not have permission to use this command")

    @commands.command()
    async def ChangePlayerMinimum(self, ctx: commands.Context, st: nextcord.Member, new_min: int):
        """Changes the required number of players for the reservation of the given member.
        If they already reached the start date and the change affects whether they can start the game,
        they will receive a new announcement with the next pings."""
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            if st.id in self.entries:
                entry = self.entries[st.id]
                entry.min_players = new_min
                self.update_storage()
            elif st.id in self.announced:
                entry = self.announced[st.id]
                if new_min > len(entry.players) >= entry.min_players or new_min <= len(entry.players) < entry.min_players:
                    entry.min_players = new_min
                    self.entries[st.id] = entry
                    self.remove_announced(st.id)
                    # storage is updated as part of remove_announced
                else:
                    await utility.dm_user(ctx.author, f"The reserved game of {st.display_name} has already reached its "
                                                      f"start date and the new minimum would not affect it at this "
                                                      f"point.")
            else:
                await utility.dm_user(ctx.author, f"{st.display_name} has no reserved game")
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You do not have permission to use this command")

    # will run every day at 5 pm UTC
    # (figure that's a good choice to maximize chances of the ST seeing it not much later)
    @tasks.loop(time=time(hour=17, minute=0))
    async def check_entries(self):
        to_announce = [entry for entry in self.entries.values() if date.fromisoformat(entry.date) <= date.today()]
        if len(to_announce) > 0:
            queue_cog: Optional[TextQueue] = self.bot.get_cog("TextQueue")
        for entry in to_announce:
            thread = get(self.helper.ReservingForum.threads, id=entry.thread)
            owner = get(self.helper.Guild.members, id=entry.owner)
            if owner is None:
                await thread.send("Reserved date has arrived, but owner could not be found")
                logging.warning(f"r-game thread owner {entry.owner} for thread {entry.thread} could not be found")
                continue
            if entry.min_players <= len(entry.players):
                await thread.send(content=EnoughPlayersView.message_string(owner),
                                  view=EnoughPlayersView(self, self.helper, entry, queue_cog))
                self.remove_entry(entry.owner)
                self.announced[entry.owner] = entry
            else:
                await thread.send(content=NotEnoughPlayersView.message_string(owner),
                                  view=NotEnoughPlayersView(self, self.helper, entry, queue_cog))
                self.remove_entry(entry.owner)
                self.announced[entry.owner] = entry


class PreSignupView(nextcord.ui.View):
    def __init__(self, cog: Reserve, helper: utility.Helper, entry: RSVPEntry):
        super().__init__(timeout=None)
        self.cog = cog
        self.helper = helper
        self.entry = entry

    async def on_error(self, error: Exception, item: nextcord.ui.Item, interaction: nextcord.Interaction) -> None:
        traceback_buffer = io.StringIO()
        traceback.print_exception(type(error), error, error.__traceback__, file=traceback_buffer)
        traceback_text = traceback_buffer.getvalue()
        logging.exception(f"Ignoring exception in PreSignupView:\n{traceback_text}")

    @nextcord.ui.button(label="Sign Up", custom_id="Sign_Up_Command", style=nextcord.ButtonStyle.green)
    async def signup_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(content=f"{button.label} has been selected!", ephemeral=True)
        if interaction.user.id in self.entry.players:
            await utility.dm_user(interaction.user, "You are already signed up")
        elif interaction.user.id == self.entry.owner or interaction.user.id in self.entry.co_sts:
            await utility.dm_user(interaction.user,
                                  "You are a Storyteller for this game and so cannot sign up for it")
        elif interaction.user.bot:
            pass
        elif len(self.entry.players) >= self.entry.max_players:
            await utility.dm_user(interaction.user, "The game is currently full, please contact the Storyteller")
        else:
            self.entry.players.append(interaction.user.id)
            self.cog.update_storage()
            await interaction.message.edit(embed=signup_embed(self.entry, self.helper), view=self)
            owner = get(self.helper.Guild.members, id=self.entry.owner)
            await utility.dm_user(owner, f"{interaction.user.display_name} ({interaction.user.name}) has signed up for "
                                         f"your reserved {self.entry.script} game")
            await self.helper.log(f"{interaction.user.display_name} ({interaction.user.name}) has signed up for "
                                  f"{owner.name}'s reserved game")

    @nextcord.ui.button(label="Leave Game", custom_id="Leave_Game_Command", style=nextcord.ButtonStyle.red)
    async def leave_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(content=f"{button.label} has been selected!", ephemeral=True)
        if interaction.user.id not in self.entry.players:
            await utility.dm_user(interaction.user, "You are not signed up")
        else:
            self.entry.players.remove(interaction.user.id)
            self.cog.update_storage()
            await interaction.message.edit(embed=signup_embed(self.entry, self.helper), view=self)
            owner = get(self.helper.Guild.members, id=self.entry.owner)
            await utility.dm_user(owner, f"{interaction.user.display_name} ({interaction.user.name}) has left your "
                                         f"reserved {self.entry.script} game")
            await self.helper.log(f"{interaction.user.display_name} ({interaction.user.name}) has left"
                                  f"{owner.name}'s reserved game")


class EnoughPlayersView(nextcord.ui.View):
    @staticmethod
    def message_string(owner: nextcord.Member) -> str:
        timeout = utcnow() + datetime.timedelta(seconds=172800)
        return f"{owner.mention} The date you set for your game has arrived, and you have enough players. Click " \
               f"**Create channel** to get your game channel. If you can't or won't start the game now, you can join " \
               f"the queue or cancel the game.\n" \
               f"This will time out {format_dt(timeout, 'R')} ({format_dt(timeout, 'f')})"

    def __init__(self, cog: Reserve, helper: utility.Helper, entry: RSVPEntry,
                 queue_cog: Optional[TextQueue]):
        super().__init__()
        self.cog = cog
        self.helper = helper
        self.entry = entry
        self.queue_cog = queue_cog
        self.timeout = 172800  # two days

    @nextcord.ui.button(label="Create channel", custom_id="create_channel", style=nextcord.ButtonStyle.green, row=1)
    async def create_channel_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if self.entry.owner not in self.cog.announced:
            await interaction.send(
                ephemeral=True,
                content="Your reservation has been removed or altered. You may no longer create a channel."
            )
            return
        await interaction.send(ephemeral=True, content="Creating channel")
        await create_channel(self.entry.owner, self.helper, self.entry.script, self.entry.co_sts, self.entry.players)
        await self.finish(interaction)

    @nextcord.ui.button(label="Switch to queue", custom_id="switch_to_queue", style=nextcord.ButtonStyle.blurple, row=1)
    async def switch_to_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if self.queue_cog is None:
            await interaction.send(content="Error: Queue not available")
            logging.error(f"Queue not available for switching in RSVP thread {self.entry.thread}")
            return
        queue_buttons = [b for b in self.children
                         if isinstance(b, nextcord.ui.Button) and b.custom_id.startswith("select")]
        for b in queue_buttons:
            b.disabled = False
        await interaction.message.edit(view=self)
        await interaction.send(ephemeral=True, content="You have selected: Switch to queue. Choose the appropraite "
                                                       "queue to confirm.")

    @nextcord.ui.button(label="Cancel the game", custom_id="cancel_game", style=nextcord.ButtonStyle.red, row=1)
    async def cancel_game_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        confirm_button = [b for b in self.children
                          if isinstance(b, nextcord.ui.Button) and b.custom_id == "confirm_cancellation"][0]
        confirm_button.disabled = False
        await interaction.message.edit(view=self)
        await interaction.send(ephemeral=True, content="You have selected: Cancel the game. Press Confirm to confirm")

    @nextcord.ui.button(label="Base Queue", custom_id="select_base_queue", style=nextcord.ButtonStyle.blurple,
                        disabled=True, row=2)
    async def select_base_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining base queue")
        await switch_to_queue(self.queue_cog, self.helper, self.entry, "Base")
        await self.finish(interaction)

    @nextcord.ui.button(label="Regular Queue", custom_id="select_regular_queue", style=nextcord.ButtonStyle.blurple,
                        disabled=True, row=2)
    async def select_regular_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining regular queue")
        await switch_to_queue(self.queue_cog, self.helper, self.entry, "Regular")
        await self.finish(interaction)

    @nextcord.ui.button(label="Experimental Queue", custom_id="select_experimental_queue",
                        style=nextcord.ButtonStyle.blurple, disabled=True, row=2)
    async def select_experimental_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining experimental queue")
        await switch_to_queue(self.queue_cog, self.helper, self.entry, "Experimental")
        await self.finish(interaction)

    @nextcord.ui.button(label="Confirm cancellation", custom_id="confirm_cancellation", style=nextcord.ButtonStyle.red,
                        disabled=True, row=3)
    async def confirm_cancel_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Game cancelled")
        await self.finish(interaction)

    async def finish(self, interaction):
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)
        self.cog.remove_announced(self.entry.owner)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id == self.entry.owner:
            return True
        else:
            await interaction.send(ephemeral=True, content="You are not the thread owner.")
            return False

    async def on_timeout(self) -> None:
        thread = get(self.helper.ReservingForum.threads, id=self.entry.thread)
        await thread.send("Timed out")

    async def on_error(self, error: Exception, item: nextcord.ui.Item, interaction: nextcord.Interaction) -> None:
        traceback_buffer = io.StringIO()
        traceback.print_exception(type(error), error, error.__traceback__, file=traceback_buffer)
        traceback_text = traceback_buffer.getvalue()
        logging.exception(f"Ignoring exception in EnoughPlayersView:\n{traceback_text}")


class NotEnoughPlayersView(nextcord.ui.View):
    @staticmethod
    def message_string(owner: nextcord.Member) -> str:
        timeout = utcnow() + datetime.timedelta(seconds=172800)
        return f"{owner.mention} The date you set for your game has arrived, but unfortunately you don't have enough " \
               f"players. You can join the queue or cancel the game.\n" \
               f"This will time out {format_dt(timeout, 'R')} ({format_dt(timeout, 'f')})" \
               f"Alternatively, you can reuse this thread to >ReserveGame again for another date."

    def __init__(self, cog: Reserve, helper: utility.Helper, entry: RSVPEntry,
                 queue_cog: Optional[TextQueue]):
        super().__init__()
        self.cog = cog
        self.helper = helper
        self.entry = entry
        self.queue_cog = queue_cog
        self.timeout = 172800  # two days

    @nextcord.ui.button(label="Switch to base queue", custom_id="select_base_queue", style=nextcord.ButtonStyle.blurple,
                        row=1)
    async def select_base_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining base queue")
        await switch_to_queue(self.queue_cog, self.helper, self.entry, "Base")
        await self.finish(interaction)

    @nextcord.ui.button(label="Switch to regular queue", custom_id="select_regular_queue",
                        style=nextcord.ButtonStyle.blurple, row=1)
    async def select_regular_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining regular queue")
        await switch_to_queue(self.queue_cog, self.helper, self.entry, "Regular")
        await self.finish(interaction)

    @nextcord.ui.button(label="Switch to experimental queue", custom_id="select_experimental_queue",
                        style=nextcord.ButtonStyle.blurple, row=1)
    async def select_experimental_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining experimental queue")
        await switch_to_queue(self.queue_cog, self.helper, self.entry, "Experimental")
        await self.finish(interaction)

    @nextcord.ui.button(label="Cancel game", custom_id="cancel", style=nextcord.ButtonStyle.red, row=2)
    async def cancel_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Game cancelled")
        await self.finish(interaction)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id == self.entry.owner:
            return True
        else:
            await interaction.send(ephemeral=True, content="You are not the thread owner.")
            return False

    async def on_timeout(self) -> None:
        thread = get(self.helper.ReservingForum.threads, id=self.entry.thread)
        await thread.send("Timed out")

    async def on_error(self, error: Exception, item: nextcord.ui.Item, interaction: nextcord.Interaction) -> None:

        traceback_buffer = io.StringIO()
        traceback.print_exception(type(error), error, error.__traceback__, file=traceback_buffer)
        traceback_text = traceback_buffer.getvalue()
        logging.exception(f"Ignoring exception in NotEnoughPlayersView:\n{traceback_text}")

    async def finish(self, interaction):
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)
        self.cog.remove_announced(self.entry.owner)


def setup(bot: commands.Bot):
    bot.add_cog(Reserve(bot, utility.Helper(bot)))

import datetime
from datetime import date, timedelta, time
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, List

import nextcord
from dataclasses_json import dataclass_json
from nextcord.ext import commands, tasks
from nextcord.utils import get, utcnow, format_dt

import utility
import Cogs.TextQueue


@dataclass_json
@dataclass
class Entry:
    thread: int
    owner: int
    date: str
    min_players: int
    max_players: int = 0
    script: str = ""
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


def default_kibitz_channel_overwrites(game_role: nextcord.Role, st_role: nextcord.Role, kibitz_role: nextcord.Role,
                                      helper: utility.Helper) -> Dict[nextcord.Role, nextcord.PermissionOverwrite]:
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


class Reserve(commands.Cog):
    bot: commands.Bot
    helper: utility.Helper
    entries: Dict[int, Entry]
    ReservedStorage: str

    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper
        self.ReservedStorage = os.path.join(self.helper.StorageLocation, "reserved.json")
        self.entries = {}
        if not os.path.exists(self.ReservedStorage):
            with open(self.ReservedStorage, 'w') as f:
                json.dump(self.entries, f)
        else:
            with open(self.ReservedStorage, 'r') as f:
                json_data = json.load(f)
                for owner in json_data:
                    self.entries[owner] = Entry.from_dict(json_data[owner])
        self.check_entries.start()

    def cog_unload(self) -> None:
        self.check_entries.cancel()

    def update_storage(self):
        json_data = {}
        for owner in self.entries:
            json_data[owner] = self.entries[owner].to_dict()
        with open(self.ReservedStorage, "w") as f:
            json.dump(json_data, f)

    def remove_entry(self, owner: int):
        self.entries.pop(owner)
        self.update_storage()

    @commands.command()
    async def ReserveGame(self, ctx: commands.Context, min_players: int, start: Optional[str]):
        # check author has no entry currently
        if any(entry_owner == ctx.author.id for entry_owner in self.entries):
            await utility.deny_command(ctx, "You already have reserved a game")
            return
        queue_cog: Optional[Cogs.TextQueue.TextQueue] = self.bot.get_cog("TextQueue")
        if queue_cog is not None and queue_cog.get_queue(ctx.author.id) is not None:
            await utility.deny_command(ctx, "You are already in the queue")
            return
        if start is None:
            start_date = date.today() + timedelta(days=14)
        else:
            start_date = parse_date(start)
        if start_date is None:
            await utility.deny_command(ctx, "Invalid start date. Use either a number (of days) or YYYY-MM-DD "
                                            "or MM-DD format, or nothing to set to the earliest option")
            return
        if start_date - date.today() < timedelta(days=14):
            await utility.deny_command(ctx, "Start date must be at least two weeks away")
            return
        if isinstance(ctx.channel, nextcord.Thread) and ctx.channel.parent == self.helper.ReservingForum \
                and ctx.author == ctx.channel.owner:
            await utility.start_processing(ctx)
            self.entries[ctx.author.id] = Entry(ctx.channel.id, ctx.author.id, start_date.isoformat(), min_players)
            self.update_storage()
            await utility.dm_user(ctx.author, f"Registered your entry for {start_date.isoformat()}")
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, f"You must create a thread in {self.helper.ReservingForum.mention} and use "
                                            f"this command there to reserve a game")

    # todo: new Signup version, ListNextGames, CancelRGame, SwitchToQueue;
    #       mod commands: CreateRGame, RemoveReservation, ChangeStartDate, ChangePlayerMinimum

    # will run every day at 5 pm UTC
    # (figure that's a good choice to maximize chances of the ST seeing it not much later)
    @tasks.loop(time=time(hour=17, minute=0))
    async def check_entries(self):
        to_announce = [entry for entry in self.entries.values() if date.fromisoformat(entry.date) <= date.today()]
        if len(to_announce) > 0:
            queue_cog: Optional[Cogs.TextQueue.TextQueue] = self.bot.get_cog("TextQueue")
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
            else:
                await thread.send(content=NotEnoughPlayersView.message_string(owner),
                                  view=NotEnoughPlayersView(self, self.helper, entry, queue_cog))
                self.remove_entry(entry.owner)


async def create_channel(entry: Entry, helper: utility.Helper):
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
        f"{game_number}-starting-{entry.script}",
        reason=reason,
        overwrites=default_game_channel_overwrites(game_role, st_role, helper)
    )
    # get/create kibitz channel
    kibitz_channel = helper.get_kibitz_channel(game_number)
    if kibitz_channel is None:
        logging.warning(f"Creating kibitz channel for {game_number}")
        kibitz_category = get(helper.Guild.categories, name="kibitz")
        if kibitz_category is not None:
            await kibitz_category.create_text_channel(
                f"rsvp-kibitz-{game_number[1:]}",
                reason=reason,
                overwrites=default_kibitz_channel_overwrites(game_role, st_role, kibitz_role, helper)
            )
        else:
            logging.error("Kibitz category not found")
    else:
        await kibitz_channel.edit(
            overwrites=default_kibitz_channel_overwrites(game_role, st_role, kibitz_role, helper),
            reason=reason
        )
    # todo: channel positions??
    # assign roles
    st = get(helper.Guild.members, id=entry.owner)
    await st.add_roles(st_role)
    co_sts = [get(helper.Guild.members, id=st_id) for st_id in entry.co_sts]
    for co_st in co_sts:
        if co_st is not None:
            await co_st.add_roles(st_role)
    players = [(p_id, get(helper.Guild.members, id=p_id)) for p_id in entry.players]
    for p_id, player in players:
        if player is None:
            game_channel.send(f"Warning: Player with ID {p_id} could not be found")
        else:
            player.add_roles(game_role)
    await game_channel.send(f"{st_role.mention} Channel is ready. Have fun!")
    logging.info(f"Setup for game {game_number} complete")


async def switch_to_queue(queue_cog: Cogs.TextQueue.TextQueue, entry: Entry, channel_type: str):
    queue_entry = Cogs.TextQueue.Entry(entry.owner, entry.script, "At next opportunity")
    queue_cog.queues[channel_type].entries.append(queue_entry)
    full_queue_posted = await queue_cog.update_queue_message(queue_cog.queues[channel_type])
    if not full_queue_posted:
        await queue_cog.helper.log("Queue too long for message - final entry/entries not displayed")
    queue_cog.update_storage()
    pass


class EnoughPlayersView(nextcord.ui.View):
    @staticmethod
    def message_string(owner: nextcord.Member) -> str:
        timeout = utcnow() + datetime.timedelta(seconds=172800)
        return f"{owner.mention} The date you set for your game has arrived, and you have enough players. Click " \
               f"**Create channel** to get your game channel. If you can't or won't start the game now, you can join " \
               f"the queue or cancel the game.\n" \
               f"This will time out {format_dt(timeout, 'R')} ({format_dt(timeout, 'f')})"

    def __init__(self, cog: Reserve, helper: utility.Helper, entry: Entry,
                 queue_cog: Optional[Cogs.TextQueue.TextQueue]):
        super().__init__()
        self.cog = cog
        self.helper = helper
        self.entry = entry
        self.queue_cog = queue_cog
        self.timeout = 172800  # two days

    @nextcord.ui.button(label="Create channel", custom_id="create_channel", style=nextcord.ButtonStyle.green, row=1)
    async def create_channel_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(ephemeral=True, content="Creating channel")
        await create_channel(self.entry, self.helper)
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)

    @nextcord.ui.button(label="Switch to queue", custom_id="switch_to_queue", style=nextcord.ButtonStyle.blurple, row=1)
    async def switch_to_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if self.queue_cog is None:
            await interaction.send(content="Error: Queue not available")
            logging.error(f"Queue not available for switching in RSVP thread {self.entry.thread}")
            return
        queue_buttons = [b for b in self.children
                         if isinstance(b, nextcord.Button) and b.custom_id.startswith("select")]
        for b in queue_buttons:
            b.disabled = False
        await interaction.message.edit(view=self)
        await interaction.send(ephemeral=True, content="You have selected: Switch to queue. Choose the appropraite "
                                                       "queue to confirm.")

    @nextcord.ui.button(label="Cancel the game", custom_id="cancel_game", style=nextcord.ButtonStyle.red, row=1)
    async def cancel_game_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        confirm_button = [b for b in self.children
                          if isinstance(b, nextcord.Button) and b.custom_id == "confirm_cancellation"][0]
        confirm_button.disabled = False
        await interaction.message.edit(view=self)
        await interaction.send(ephemeral=True, content="You have selected: Cancel the game. Press Confirm to confirm")

    @nextcord.ui.button(label="Base Queue", custom_id="select_base_queue", style=nextcord.ButtonStyle.blurple,
                        disabled=True, row=2)
    async def select_base_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining base queue")
        await switch_to_queue(self.queue_cog, self.entry, "Base")
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)

    @nextcord.ui.button(label="Regular Queue", custom_id="select_regular_queue", style=nextcord.ButtonStyle.blurple,
                        disabled=True, row=2)
    async def select_regular_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining regular queue")
        await switch_to_queue(self.queue_cog, self.entry, "Regular")
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)

    @nextcord.ui.button(label="Experimental Queue", custom_id="select_experimental_queue",
                        style=nextcord.ButtonStyle.blurple, disabled=True, row=2)
    async def select_experimental_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining experimental queue")
        await switch_to_queue(self.queue_cog, self.entry, "Experimental")
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)

    @nextcord.ui.button(label="Confirm cancellation", custom_id="confirm_cancellation", style=nextcord.ButtonStyle.red,
                        disabled=True, row=3)
    async def confirm_cancel_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Game cancelled")
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id == self.entry.owner:
            return True
        else:
            await interaction.send(ephemeral=True, content="You are not the thread owner.")
            return False

    async def on_timeout(self) -> None:
        thread = get(self.helper.ReservingForum.threads, id=self.entry.thread)
        await thread.send("Timed out")


class NotEnoughPlayersView(nextcord.ui.View):

    @staticmethod
    def message_string(owner: nextcord.Member) -> str:
        timeout = utcnow() + datetime.timedelta(seconds=172800)
        return f"{owner.mention} The date you set for your game has arrived, but unfortunately you don't have enough " \
               f"players. You can join the queue or cancel the game.\n" \
               f"This will time out {format_dt(timeout, 'R')} ({format_dt(timeout, 'f')})" \
               f"Alternatively, you can reuse this thread to >ReserveGame again for another date."

    def __init__(self, cog: Reserve, helper: utility.Helper, entry: Entry,
                 queue_cog: Optional[Cogs.TextQueue.TextQueue]):
        super().__init__()
        self.cog = cog
        self.helper = helper
        self.entry = entry
        self.queue_cog = queue_cog
        self.timeout = 172800  # two days

    @nextcord.ui.button(label="Switch to base queue", custom_id="select_base_queue", style=nextcord.ButtonStyle.blurple,
                        disabled=True, row=1)
    async def select_base_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining base queue")
        await switch_to_queue(self.queue_cog, self.entry, "Base")
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)

    @nextcord.ui.button(label="Switch to regular queue", custom_id="select_regular_queue",
                        style=nextcord.ButtonStyle.blurple, disabled=True, row=1)
    async def select_regular_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining regular queue")
        await switch_to_queue(self.queue_cog, self.entry, "Regular")
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)

    @nextcord.ui.button(label="Switch to experimental queue", custom_id="select_experimental_queue",
                        style=nextcord.ButtonStyle.blurple, disabled=True, row=1)
    async def select_experimental_queue_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Joining experimental queue")
        await switch_to_queue(self.queue_cog, self.entry, "Experimental")
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)

    @nextcord.ui.button(label="Cancel game", custom_id="cancel", style=nextcord.ButtonStyle.red,
                        disabled=True, row=2)
    async def confirm_cancel_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(content="Game cancelled")
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id == self.entry.owner:
            return True
        else:
            await interaction.send(ephemeral=True, content="You are not the thread owner.")
            return False

    async def on_timeout(self) -> None:
        thread = get(self.helper.ReservingForum.threads, id=self.entry.thread)
        await thread.send("Timed out")


def setup(bot: commands.Bot):
    bot.add_cog(Reserve(bot, utility.Helper(bot)))

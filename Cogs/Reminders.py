from __future__ import annotations

import datetime
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json
from nextcord.ext import commands, tasks
from nextcord.utils import utcnow, format_dt

import utility

hours_pattern = re.compile(r"^(\d+):([0-5]\d)$")


def parse_hours(inp: str) -> float:
    matched = hours_pattern.match(inp)
    if matched is not None:
        return int(matched.group(1)) + int(matched.group(2)) / 60.0
    else:
        return float(inp)


@dataclass_json
@dataclass(order=True)
class Reminder:
    time: str
    channel: int
    text: str

    def explain(self) -> str:
        text_elements = self.text.split(" ")
        # remove role pings
        text_elements = [el for el in text_elements[:2] if not el.startswith("<@&")] + text_elements[2:]
        time = datetime.datetime.fromisoformat(self.time)
        if self.text[-4:] == ":t>)":
            event = " ".join(text_elements[:-2])
            explanation = f"{format_dt(time, 'R')} ({format_dt(time, 'f')}): Reminder that `{event}` at " \
                          f"{text_elements[-1][1:-3]}f>"
        else:
            event = " ".join(text_elements)
            explanation = f"{format_dt(time, 'R')} ({format_dt(time, 'f')}): Announcement that `{event}`"
        return explanation

    @staticmethod
    def create(time: datetime.datetime, channel: int, mention: Optional[str], event: str,
               end_of_countdown: datetime.datetime) -> Reminder:
        text = event if mention is None else f"{mention} {event}"
        if time == end_of_countdown:
            return Reminder(time.isoformat(), channel, text)
        text += f" {format_dt(end_of_countdown, 'R')} ({format_dt(end_of_countdown, 't')})"
        return Reminder(time.isoformat(), channel, text)


class Reminders(commands.Cog):
    bot: commands.Bot
    helper: utility.Helper
    reminder_list: list[Reminder]
    ReminderStorage: str

    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper
        self.ReminderStorage = os.path.join(self.helper.StorageLocation, "reminders.json")
        self.reminder_list = []
        if not os.path.exists(self.ReminderStorage):
            with open(self.ReminderStorage, 'w') as f:
                json.dump(self.reminder_list, f, indent=2)
        else:
            with open(self.ReminderStorage, 'r') as f:
                self.reminder_list = [Reminder.from_dict(item) for item in json.load(f)]
            self.reminder_list.sort()
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    def update_storage(self):
        with open(self.ReminderStorage, 'w') as f:
            json.dump([item.to_dict() for item in self.reminder_list], f, indent=2)

    @commands.command(usage="<game_number> [event] [times]... <'ping-st'> <'no-player-ping'>")
    async def SetReminders(self, ctx, *args):
        """At the given times, sends reminders to the players how long they have until the event occurs.
        The event argument is optional and defaults to "Whispers close". Times must be given in hours from the
        current time, either as integer, decimal number or in hh:mm format. You can give any number of times.
        The event is assumed to occur at the latest given time. You can have the reminders also ping Storytellers
        and/or not ping players by adding 'ping-st'/'no-player-ping'"""
        # parse arguments
        ping_st = "ping-st" in args
        no_player_ping = "no-player-ping" in args
        args = tuple(arg for arg in args if arg not in ["ping-st", "no-player-ping"])
        if len(args) < 2:
            await utility.deny_command(ctx, "At least game number and one reminder time are required")
            return
        game_number = args[0]
        game_channel = self.helper.get_game_channel(game_number)
        if game_channel is None:
            await utility.deny_command(ctx, "The first argument must be a valid game number")
            return
        event = "Whispers close"
        try:
            times = [parse_hours(time) for time in args[1:]]
        except ValueError:
            event = args[1]
            try:
                times = [parse_hours(time) for time in args[2:]]
            except ValueError as e:
                await utility.deny_command(ctx, e.args[0])  # looks like: "could not convert string to float: 'bla'"
                return
            if len(times) == 0:
                await utility.deny_command(ctx, "At least one reminder time is required")
                return
        # set the reminders
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            mention = None
            if not no_player_ping:
                game_role = self.helper.get_game_role(game_number)
                mention = game_role.mention
            if ping_st:
                st_role = self.helper.get_st_role(game_number)
                mention = st_role.mention if mention is None else f"{st_role.mention} {mention}"
            times.sort()
            end_of_countdown = utcnow() + datetime.timedelta(hours=times[-1])
            for time in times:
                reminder = Reminder.create(utcnow() + datetime.timedelta(hours=time), game_channel.id, mention, event,
                                           end_of_countdown)
                self.reminder_list.append(reminder)
                logging.debug(f"Added reminder in game {game_number}: {reminder}")
            self.reminder_list.sort()
            self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You must be an ST to use this command")

    @commands.command()
    async def DeleteReminders(self, ctx: commands.Context, game_number: str):
        """Deletes all reminders for the given game number."""
        game_channel_id = self.helper.get_game_channel(game_number).id
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            self.reminder_list = [reminder for reminder in self.reminder_list if reminder.channel != game_channel_id]
            self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You must be an ST to use this command")

    @commands.command()
    async def ShowReminders(self, ctx: commands.Context, game_number: str):
        """Shows all reminders for the given game number."""
        game_channel_id = self.helper.get_game_channel(game_number).id
        await utility.start_processing(ctx)
        reminders = [reminder for reminder in self.reminder_list if reminder.channel == game_channel_id]
        if len(reminders) == 0:
            await utility.dm_user(ctx.author, "There are no reminders for this game")
        else:
            await utility.dm_user(ctx.author, "\n".join([reminder.explain() for reminder in reminders]))
        await utility.finish_processing(ctx)

    @tasks.loop(seconds=15)
    async def check_reminders(self):
        if len(self.reminder_list) == 0:
            return
        earliest_reminder = self.reminder_list[0]
        if datetime.datetime.fromisoformat(earliest_reminder.time) <= utcnow():
            channel = self.bot.get_channel(earliest_reminder.channel)
            await channel.send(earliest_reminder.text)
            self.reminder_list.pop(0)
            self.update_storage()


def setup(bot: commands.Bot):
    bot.add_cog(Reminders(bot, utility.Helper(bot)))

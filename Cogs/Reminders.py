from __future__ import annotations
import datetime
import heapq
import json
import os
from dataclasses import dataclass

from dataclasses_json import dataclass_json
from nextcord.ext import commands, tasks
from nextcord.utils import utcnow, format_dt

import utility


@dataclass(order=True)
@dataclass_json
class Reminder:
    time: datetime.datetime
    channel: int
    text: str

    def explain(self) -> str:
        text_elements = self.text.split(" ")
        if self.text[-2:] == ">)":
            event = " ".join(text_elements[1:-2])
            explanation = f"{format_dt(self.time, 'R')} ({format_dt(self.time, 'f')}): Reminder that `{event}` at " \
                          f"{text_elements[-1].replace('t', 'f')}"
        else:
            event = " ".join(text_elements[1:])
            explanation = f"{format_dt(self.time, 'R')} ({format_dt(self.time, 'f')}): Announcement that `{event}`"
        return explanation

    @staticmethod
    def create(time: datetime.datetime, channel: int, mention: str, event: str, end_of_countdown: datetime.datetime)\
            -> Reminder:
        if time == end_of_countdown:
            return Reminder(time, channel, f"{mention} {event}")
        text = f"{mention} {event} {format_dt(end_of_countdown, 'R')} ({format_dt(end_of_countdown, 't')})"
        return Reminder(time, channel, text)


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
                json.dump(self.reminder_list, f)
        else:
            with open(self.ReminderStorage, 'r') as f:
                self.reminder_list = [Reminder.from_dict(item) for item in json.load(f)]
            heapq.heapify(self.reminder_list)
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    def update_storage(self):
        with open(self.ReminderStorage, 'w') as f:
            json.dump([item.to_dict() for item in self.reminder_list], f)

    @commands.command(usage="<game_number> [event] [times]...")
    async def SetReminders(self, ctx, *args):
        """At the given times, sends reminders to the players how long they have until the event occurs.
        The event argument is optional and defaults to "Whispers close". Times must be given in hours from the
        current time. You can give any number of times. The event is assumed to occur at the latest given time."""
        if len(args) < 2:
            await utility.deny_command(ctx)
            await utility.dm_user(ctx.author, "At least game number and one reminder time are required")
            return
        game_number = args[0]
        game_channel = self.helper.get_game_channel(game_number)
        if not game_channel:
            await utility.deny_command(ctx)
            await utility.dm_user(ctx.author, "The first argument must be a valid game number")
            return
        game_role = self.helper.get_game_role(game_number)
        event = "Whispers close"
        try:
            times = [float(time) for time in args[1:]]
            # would be nice to be able to parce hh:mm format as well
        except ValueError:
            event = args[1]
            try:
                times = [float(time) for time in args[2:]]
            except ValueError as e:
                await utility.deny_command(ctx)
                await utility.dm_user(ctx.author, e.args[0])  # looks like: "could not convert string to float: 'bla'"
                return
            if len(times) == 0:
                await utility.deny_command(ctx)
                await utility.dm_user(ctx.author, "At least one reminder time is required")
                return
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            times.sort()
            end_of_countdown = utcnow() + datetime.timedelta(hours=times[-1])
            for time in times:
                reminder = Reminder.create(utcnow() + datetime.timedelta(hours=time), game_channel.id, game_role.mention, event, end_of_countdown)
                heapq.heappush(self.reminder_list, reminder)
            self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx)
            await utility.dm_user(ctx.author, "You must be an ST to use this command")

    @commands.command()
    async def DeleteReminders(self, ctx: commands.Context, game_number: str):
        """Deletes all reminders for the given game number."""
        game_channel_id = self.helper.get_game_channel(game_number).id
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            self.reminder_list = [reminder for reminder in self.reminder_list if reminder.channel != game_channel_id]
            heapq.heapify(self.reminder_list)
            self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx)
            await utility.dm_user(ctx.author, "You must be an ST to use this command")

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
        earliest_reminder = heapq.heappop(self.reminder_list)
        if earliest_reminder.time < utcnow():
            channel = self.bot.get_channel(earliest_reminder.channel)
            await channel.send(earliest_reminder.text)
            self.reminder_list.remove(earliest_reminder)
            self.update_storage()

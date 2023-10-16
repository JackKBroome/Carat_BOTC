import json
import logging
import os
from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict

import nextcord
from dataclasses_json import dataclass_json
from nextcord import HTTPException
from nextcord.ext import commands
from nextcord.utils import get

import utility

ExplainInvalidChannelType = "Not a valid channel type - accepted forms are `regular, standard, normal, reg, r, s, n` " \
                            "for regular, `experimental, exp, x` for experimental - capitalization doesn't matter."


@dataclass_json
@dataclass
class Entry:
    st: int
    script: str
    availability: str
    notes: Optional[str] = None


@dataclass_json
@dataclass
class StQueue:
    channel_id: int
    message_id: int
    thread_id: Optional[int] = None
    entries: List[Entry] = field(default_factory=list)


class TextQueue(commands.Cog):
    bot: commands.Bot
    helper: utility.Helper
    queues: Dict[str, StQueue]
    QueueStorage: str

    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper
        self.QueueStorage = os.path.join(self.helper.StorageLocation, "queue.json")
        self.queues = {}
        if not os.path.exists(self.QueueStorage):
            with open(self.QueueStorage, 'w') as f:
                json.dump(self.queues, f)
        else:
            with open(self.QueueStorage, 'r') as f:
                json_data = json.load(f)
                for queue in json_data:
                    self.queues[queue] = StQueue.from_dict(json_data[queue])

    async def update_queue_message(self, queue: StQueue) -> bool:
        channel = get(self.helper.Guild.channels, id=queue.channel_id)
        if queue.thread_id is not None:
            thread = get(channel.threads, id=queue.thread_id)
            message = await thread.fetch_message(queue.message_id)
        else:
            message = await channel.fetch_message(queue.message_id)
        embed = message.embeds[0]
        embed.clear_fields()
        spot = 1
        for entry in queue.entries:
            user = get(self.helper.Guild.members, id=entry.st)
            if user is None:
                queue.entries.remove(entry)
                message = f"Removed user with ID {entry.st} from queue due to having left the guild"
                logging.warning(message)
                await self.helper.log(message)
                continue
            entry_string = f"Script: {entry.script}\nAvailability: {entry.availability}\n"
            if entry.notes is not None:
                entry_string += f"Notes: {entry.notes}\n"
            embed.add_field(name=f"{spot}. {user.display_name}"[:256],
                            value=entry_string[:1024],
                            inline=False)  # length limits by discord
            spot = spot + 1
        await self.helper.log(
            f"Queue updated - current entries: "
            f"{str([str(get(self.helper.Guild.members, id=qe.st)) for qe in queue.entries])}"[:1950])
        queue_posted_completely = True
        success = False
        while not success:
            try:
                await message.edit(embed=embed)
                success = True
            except HTTPException:
                embed.remove_field(len(embed.fields) - 1)
                queue_posted_completely = False
        return queue_posted_completely

    async def announce_free_channel(self, game_number, queue_position: int):
        channel = self.helper.get_game_channel(game_number)
        channel_type = "Experimental" if game_number[0] == "x" else "Regular"
        if queue_position >= len(self.queues[channel_type].entries):
            await channel.send("There are no further entries in the queue.")
            return
        next_entry = self.queues[channel_type].entries[queue_position]
        user = get(self.helper.Guild.members, id=next_entry.st)
        if user is not None:
            content = f"{user.mention} This game channel has become free! You are next in the queue.\n" \
                      f"You may claim the grimoire with >ClaimGrimoire {game_number} or the button below.\n" \
                      f"If you are not currently able to run the game, use the button below to decline the grimoire " \
                      f"and inform the next person in the queue."
            await channel.send(content=content,
                               view=FreeChannelNotificationView(self, self.helper, self.queues[channel_type].entries,
                                                                game_number, queue_position))
        else:
            await self.announce_free_channel(game_number, queue_position + 1)

    async def user_leave_queue(self, user: nextcord.Member):
        self.queues["Regular"].entries = [entry for entry in self.queues["Regular"].entries if entry.st != user.id]
        self.queues["Experimental"].entries = [entry for entry in self.queues["Experimental"].entries
                                               if entry.st != user.id]
        await self.update_queue_message(self.queues["Regular"])
        await self.update_queue_message(self.queues["Experimental"])
        await self.update_storage()

    async def update_storage(self):
        json_data = {}
        for queue in self.queues:
            json_data[queue] = self.queues[queue].to_dict()
        with open(self.QueueStorage, "w") as f:
            json.dump(json_data, f)

    def get_queue(self, user_id: int) -> Optional[StQueue]:
        users_in_regular_queue = [entry.st for entry in self.queues["Regular"].entries]
        users_in_exp_queue = [entry.st for entry in self.queues["Experimental"].entries]
        if user_id in users_in_regular_queue:
            return self.queues["Regular"]
        elif user_id in users_in_exp_queue:
            return self.queues["Experimental"]
        else:
            return None

    @commands.command()
    async def InitQueue(self, ctx: commands.Context, channel_type: str,
                        reset: Optional[Literal["reset"]]):
        """Initializes an ST queue for either regular or experimental games in the channel or thread the command was used in.
        Can be reused to create a new queue message for either channel type.
        If existing entries should be deleted, add "reset" at the end."""
        channel_type = utility.get_channel_type(channel_type)
        if not channel_type:
            await utility.deny_command(ctx, ExplainInvalidChannelType)
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            embed = nextcord.Embed(title=channel_type + " storytelling queue", description="Use >JoinTextQueue to join")
            if isinstance(ctx.channel, nextcord.Thread):
                queue = StQueue(ctx.channel.parent.id, -1, ctx.channel.id)
            elif isinstance(ctx.channel, nextcord.TextChannel):
                queue = StQueue(ctx.channel.id, -1)
            else:
                await utility.dm_user(ctx.author, 'Please place the queue in a text channel or thread')
                return

            if not reset:
                queue.entries = self.queues[channel_type].entries

            queue_message = await ctx.send(embed=embed)
            queue.message_id = queue_message.id
            self.queues[channel_type] = queue

            await self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "This command is restricted to moderators")
        await self.helper.log(f"{ctx.author.mention} has run the InitQueue command in {ctx.channel.mention}")

    @commands.command()
    async def JoinTextQueue(self, ctx: commands.Context, channel_type: str, script: str,
                            availability: str, notes: Optional[str]):
        """Adds you to the queue for the given channel type (regular/experimental).
        The queue entry will list the provided information.
        You may not join either queue while you have an entry in either queue.
        Do not join a queue if you are currently storytelling, unless you are just a co-ST.
        Note that if a parameter contains spaces, you have to surround it with quotes."""
        channel_type = utility.get_channel_type(channel_type)
        if not channel_type:
            await utility.deny_command(ctx, ExplainInvalidChannelType)
        users_in_queue = [entry.st for entry in self.queues["Regular"].entries + self.queues["Experimental"].entries]
        if ctx.author.id not in users_in_queue:
            await utility.start_processing(ctx)
            entry = Entry(ctx.author.id, script, availability)
            if notes:
                entry.notes = notes
            self.queues[channel_type].entries.append(entry)
            full_queue_posted = await self.update_queue_message(self.queues[channel_type])
            if not full_queue_posted:
                await self.helper.log("Queue too long for message - final entry/entries not displayed")
                await utility.dm_user(ctx.author, "The queue is too long to display in full. Your entry may not be "
                                                  "displayed currently, but it has been added to the queue.")

            await self.update_storage()
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You may not join a text ST queue while you are already in one")

        await self.helper.log(f"{ctx.author.mention} has run the JoinTextQueue command")

    @commands.command()
    async def LeaveTextQueue(self, ctx: commands.Context):
        """Removes you from the queue you are in currently.
        Note that rejoining will put you at the end, not where you were before."""
        await utility.start_processing(ctx)
        queue = self.get_queue(ctx.author.id)
        if not queue:
            await utility.dm_user(ctx.author, "You are not in a queue at the moment")
            await utility.finish_processing(ctx)
            return

        queue.entries = [e for e in queue.entries if e.st != ctx.author.id]
        full_queue_posted = await self.update_queue_message(queue)
        if not full_queue_posted:
            await self.helper.log("Queue too long for message - final entry/entries not displayed")

        await self.update_storage()

        await utility.finish_processing(ctx)

        await self.helper.log(f"{ctx.author.mention} has run the LeaveTextQueue command")

    @commands.command()
    async def MoveDown(self, ctx: commands.Context, number_of_spots: Optional[int] = 1):
        """Moves you down the given number of spaces in your queue.
        Use if you can't run the game yet but don't want to be pinged every time a channel becomes free.
        Note that you cannot move yourself back up, though you can ask a mod to fix things if you make a mistake"""
        await utility.start_processing(ctx)
        queue = self.get_queue(ctx.author.id)
        if not queue:
            await utility.dm_user(ctx.author, "You are not in a queue at the moment")
            await utility.finish_processing(ctx)
            return
        for index, entry in enumerate(queue.entries):
            if entry.st == ctx.author.id:
                current_index = index
        queue.entries.insert(current_index + number_of_spots, queue.entries.pop(current_index))

        full_queue_posted = await self.update_queue_message(queue)
        if not full_queue_posted:
            await self.helper.log("Queue too long for message - final entry/entries not displayed")
            await utility.dm_user(ctx.author, "The queue is too long to display in full. Your entry may not be "
                                              "displayed currently, but is still in the queue.")
        await self.update_storage()

        await utility.finish_processing(ctx)

    @commands.command()
    async def EditEntry(self, ctx: commands.Context, script: str, availability: str, notes: Optional[str]):
        """Edits your queue entry.
        You cannot change the channel type. You have to give script and availability even if they have not changed."""
        if utility.get_channel_type(script):
            await utility.dm_user(ctx.author, "It seems you gave a channel type as script. Note that EditEntry does "
                                              "not need or expect a channel type. If you didn't intend to give a "
                                              "channel type as your script, simply run the command again without the "
                                              "channel type at the start.")
        await utility.start_processing(ctx)
        queue = self.get_queue(ctx.author.id)
        if not queue:
            await utility.dm_user(ctx.author, "You are not in a queue at the moment")
            await utility.finish_processing(ctx)
            return
        entry = next(e for e in queue.entries if e.st == ctx.author.id)
        entry.script = script
        entry.availability = availability
        if notes:
            entry.notes = notes

        full_queue_posted = await self.update_queue_message(queue)
        if not full_queue_posted:
            await self.helper.log("Queue too long for message - final entry/entries not displayed")
        await self.update_storage()
        await utility.finish_processing(ctx)
        await self.helper.log(f"{ctx.author.mention} has run the EditEntry command")

    @commands.command()
    async def EditNotes(self, ctx: commands.Context, notes: str):
        """Edits only the notes part of your entry."""
        if utility.get_channel_type(notes):
            await utility.dm_user(ctx.author, "It seems you gave a channel type as notes. Note that EditNotes does "
                                              "not need or expect a channel type. If you didn't intend to give a "
                                              "channel type for your notes, simply run the command again without the "
                                              "channel type at the start.")
        await utility.start_processing(ctx)
        queue = self.get_queue(ctx.author.id)
        if not queue:
            await utility.dm_user(ctx.author, "You are not in a queue at the moment")
            await utility.finish_processing(ctx)
            return
        entry = next(e for e in queue.entries if e.st == ctx.author.id)
        entry.notes = notes

        full_queue_posted = await self.update_queue_message(queue)
        if not full_queue_posted:
            await self.helper.log("Queue too long for message - final entry/entries not displayed")
        await self.update_storage()
        await utility.finish_processing(ctx)
        await self.helper.log(f"{ctx.author.mention} has run the EditNotes command")

    @commands.command()
    async def RemoveFromQueue(self, ctx: commands.Context, member: nextcord.Member):
        """Removes the given user from either queue.
        You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user."""
        # mod command
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            queue = self.get_queue(member.id)
            if not queue:
                await utility.dm_user(ctx.author, "The member is not in a queue at the moment")
                await utility.finish_processing(ctx)
                return

            queue.entries = [e for e in queue.entries if e.st != member.id]
            full_queue_posted = await self.update_queue_message(queue)
            if not full_queue_posted:
                await self.helper.log("Queue too long for message - final entry/entries not displayed")
            await self.update_storage()

            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "This command is restricted to moderators")
        await self.helper.log(f"{ctx.author.mention} has run the RemoveFromQueue command")

    @commands.command()
    async def MoveToSpot(self, ctx: commands.Context, member: nextcord.Member, spot: int):
        """Moves the queue entry of the given user to the given spot in their queue, 1 being the top.
        You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user."""
        # mod command
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            queue = self.get_queue(ctx.author.id)
            if not queue:
                await utility.dm_user(ctx.author, "The member is not in a queue at the moment")
                await utility.finish_processing(ctx)
                return
            for index, item in enumerate(queue.entries):
                if item.st == member.id:
                    entry = queue.entries.pop(index)
            queue.entries.insert(spot - 1, entry)

            full_queue_posted = await self.update_queue_message(queue)
            if not full_queue_posted:
                await self.helper.log("Queue too long for message - final entry/entries not displayed")

            await self.update_storage()

            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "This command is restricted to moderators")
        await self.helper.log(f"{ctx.author.mention} has run the MoveToSpot command on {member.display_name}")


class FreeChannelNotificationView(nextcord.ui.View):
    def __init__(self, queue_cog: TextQueue, helper: utility.Helper, queue: list, game_number: str,
                 queue_position: int):
        super().__init__()
        self.queue_cog = queue_cog
        self.helper = helper
        self.queue = queue
        self.game_number = game_number
        self.queue_position = queue_position
        self.timeout = 172800  # two days

    @nextcord.ui.button(label="Claim grimoire", custom_id="claim_grimoire", style=nextcord.ButtonStyle.green)
    async def claim_grimoire_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        st_role = self.helper.get_st_role(self.game_number)
        if st_role.members:
            await interaction.send(
                content=f"The grimoire has been claimed by "
                        f"{', '.join([st.display_name for st in st_role.members])} "
                        f"in the meantime. Try contacting them to clear this up.",
                ephemeral=True)
        else:
            await interaction.user.add_roles(st_role)
            await self.queue_cog.user_leave_queue(interaction.user)
            await interaction.send(content="You have claimed the grimoire. Enjoy your game!", ephemeral=True)
            await self.helper.log(
                f"{interaction.user.mention} has claimed grimoire {self.game_number} through the queue announcement button")
            self.clear_items()
            self.stop()
            await interaction.message.edit(view=self)

    @nextcord.ui.button(label="Decline grimoire", custom_id="decline_grimoire", style=nextcord.ButtonStyle.red)
    async def decline_grimoire_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(
            content="You have declined the grimoire. "
                    "Use >MoveDown if you don't want to be pinged the next time a channel becomes free.",
            ephemeral=True)
        await self.queue_cog.announce_free_channel(self.game_number, self.queue_position + 1)
        self.clear_items()
        self.stop()
        await interaction.message.edit(view=self)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        return interaction.user.id == self.queue[self.queue_position].st

    async def on_timeout(self) -> None:
        game_channel = self.helper.get_game_channel(self.game_number)
        st_role = self.helper.get_st_role(self.game_number)
        if not st_role.members:
            await game_channel.send("Previous queue entry timed out")
            await self.queue_cog.announce_free_channel(self.game_number, self.queue_position + 1)


def setup(bot: commands.Bot):
    bot.add_cog(TextQueue(bot, utility.Helper(bot)))

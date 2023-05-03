import json
import os
import typing
from time import strftime, gmtime

import nextcord
from nextcord.ext import commands
from nextcord.utils import get

import utility

ChannelTypeParameter = typing.Literal[
    'regular', 'Regular', 'standard', 'Standard', 'normal', 'Normal', 'r', 'R', 'n', 'N', 'experimental', 'Experimental', 'exp', 'Exp', 'x', 'X']


class Queue(commands.Cog):
    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper
        self.QueueLocation = os.path.join(self.helper.StorageLocation, "queue.json")
        try:
            with open(self.QueueLocation, 'r') as f:
                self.queues = json.load(f)
        except OSError:
            self.queues = {"Regular": {}, "Experimental": {}}
            with open(self.QueueLocation, 'w') as f:
                json.dump(self.queues, f)

    async def update_queue_message(self, queue: dict):
        channel = get(self.helper.Guild.channels, id=queue["ChannelId"])
        if "ThreadId" in queue:
            thread = get(channel.threads, id=queue["ThreadId"])
            message = await thread.fetch_message(queue["MessageId"])
        else:
            message = await channel.fetch_message(queue["MessageId"])
        embed = message.embeds[0]
        embed.clear_fields()
        for entry in queue["Entries"]:
            user = get(self.helper.Guild.members, id=entry["ST"])
            entry_string = f"Script: {entry['Script']}\nAvailability: {entry['Availability']}"
            if "Notes" in entry:
                entry_string += f"\nNotes: {entry['Notes']}"
            embed.add_field(name=user.display_name, value=entry_string, inline=False)
        await self.helper.log(f"Queue updated - current entries: {queue['Entries']}"[:1000])
        await message.edit(embed=embed)

    async def announce_free_channel(self, game_number, queue_position: int):
        channel = self.helper.get_game_channel(game_number)
        channel_type = "Experimental" if game_number[0] == "x" else "Regular"
        if queue_position > len(self.queues[channel_type]["Entries"]):
            return
        next_entry = self.queues[channel_type]["Entries"][queue_position]
        user = get(self.helper.Guild.members, id=next_entry["ST"])
        if user:
            content = f"{user.mention} This game channel has become free! You are next in the queue.\n" \
                      f"You may claim the grimoire with >ClaimGrimoire {game_number} or the button below.\n" \
                      f"If you are not currently able to run the game, use the button below to decline the grimoire " \
                      f"and inform the next person in the queue"
            await channel.send(content=content,
                               view=FreeChannelNotificationView(self, self.helper, self.queues[channel_type]["Entries"],
                                                                game_number, queue_position))
        else:
            await self.announce_free_channel(game_number, queue_position + 1)

    async def user_leave_queue(self, user: nextcord.Member):
        self.queues["Regular"]["Entries"] = [entry for entry in self.queues["Regular"]["Entries"]
                                             if entry["ST"] != user.id]
        self.queues["Experimental"]["Entries"] = [entry for entry in self.queues["Experimental"]["Entries"]
                                                  if entry["ST"] != user.id]
        await self.update_queue_message(self.queues["Regular"])
        await self.update_queue_message(self.queues["Experimental"])
        with open(self.QueueLocation, "w") as f:
            json.dump(self.queues, f)

    @commands.command()
    async def InitQueue(self, ctx: commands.Context, channel_type: ChannelTypeParameter):
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            channel_type = utility.get_channel_type(channel_type)

            embed = nextcord.Embed(title=channel_type + " storytelling queue", description="Use >Enqueue to join")
            if isinstance(ctx.channel, nextcord.Thread):
                self.queues[channel_type]["ThreadId"] = ctx.channel.id
                self.queues[channel_type]["ChannelId"] = ctx.channel.parent.id
            elif isinstance(ctx.channel, nextcord.TextChannel):
                # remove ThreadId in case the command was previously executed in a thread
                self.queues[channel_type].pop("ThreadId", None)
                self.queues[channel_type]["ChannelId"] = ctx.channel.id
            else:
                await utility.dm_user(ctx.author, 'Please place the queue in a text channel or thread')
                return

            queue_message = await ctx.send(embed=embed)
            self.queues[channel_type]["MessageId"] = queue_message.id
            self.queues[channel_type]["Entries"] = []

            with open(self.QueueLocation, "w") as f:
                json.dump(self.queues, f)
            await self.helper.finish_processing(ctx)
            print("-= The InitQueue command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
        else:
            await utility.deny_command(ctx, "InitQueue")
            await utility.dm_user(ctx.author, "This command is restricted to moderators")
        await self.helper.log(f"{ctx.author.mention} has run the InitQueue command in {ctx.channel.mention}")

    @commands.command()
    async def Enqueue(self, ctx: commands.Context, channel_type: ChannelTypeParameter, script: str, availability: str,
                      notes: typing.Optional[str]):
        channel_type = utility.get_channel_type(channel_type)
        users_in_queue = [entry["ST"]
                          for entry in self.queues["Regular"]["Entries"] + self.queues["Experimental"]["Entries"]]
        if ctx.author.id not in users_in_queue:
            await utility.start_processing(ctx)
            entry = {"ST": ctx.author.id, "Script": script, "Availability": availability}
            if notes:
                entry["Notes"] = notes
            self.queues[channel_type]["Entries"].append(entry)
            await self.update_queue_message(self.queues[channel_type])

            with open(self.QueueLocation, "w") as f:
                json.dump(self.queues, f)
            await self.helper.finish_processing(ctx)
            print("-= The Enqueue command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
        else:
            await utility.deny_command(ctx, "Enqueue")
            await utility.dm_user(ctx.author, "You may not join a text ST queue while you are already in one")

        await self.helper.log(f"{ctx.author.mention} has run the Enqueue command")

    @commands.command()
    async def Dequeue(self, ctx: commands.Context):
        await utility.start_processing(ctx)
        users_in_regular_queue = [entry["ST"] for entry in self.queues["Regular"]["Entries"]]
        users_in_exp_queue = [entry["ST"] for entry in self.queues["Experimental"]["Entries"]]
        if ctx.author.id in users_in_regular_queue:
            channel_type = "Regular"
        elif ctx.author.id in users_in_exp_queue:
            channel_type = "Experimental"
        else:
            await utility.dm_user(ctx.author, "You are not in a queue at the moment")
            await self.helper.finish_processing(ctx)
            return

        self.queues[channel_type]["Entries"] = [e for e in self.queues[channel_type]["Entries"]
                                                if e["ST"] != ctx.author.id]
        await self.update_queue_message(self.queues[channel_type])
        with open(self.QueueLocation, "w") as f:
            json.dump(self.queues, f)

        await self.helper.finish_processing(ctx)
        print("-= The Dequeue command was used successfully by " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

        await self.helper.log(f"{ctx.author.mention} has run the Dequeue command")

    @commands.command()
    async def MoveDown(self, ctx: commands.Context, number_of_spots: typing.Optional[int] = 1):
        await utility.start_processing(ctx)
        users_in_regular_queue = [entry["ST"] for entry in self.queues["Regular"]["Entries"]]
        users_in_exp_queue = [entry["ST"] for entry in self.queues["Experimental"]["Entries"]]
        if ctx.author.id in users_in_regular_queue:
            channel_type = "Regular"
        elif ctx.author.id in users_in_exp_queue:
            channel_type = "Experimental"
        else:
            await utility.dm_user(ctx.author, "You are not in a queue at the moment")
            await self.helper.finish_processing(ctx)
            return
        for index, item in enumerate(self.queues[channel_type]["Entries"]):
            if item["ST"] == ctx.author.id:
                current_index = index
        self.queues[channel_type]["Entries"].insert(current_index + number_of_spots,
                                                    self.queues[channel_type]["Entries"].pop(current_index))

        await self.update_queue_message(self.queues[channel_type])
        with open(self.QueueLocation, "w") as f:
            json.dump(self.queues, f)

        await self.helper.finish_processing(ctx)
        print("-= The MoveDown command was used successfully by " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    @commands.command()
    async def KickFromQueue(self, ctx: commands.Context, member: nextcord.Member):
        # mod command
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            users_in_regular_queue = [entry["ST"] for entry in self.queues["Regular"]["Entries"]]
            users_in_exp_queue = [entry["ST"] for entry in self.queues["Experimental"]["Entries"]]
            if member.id in users_in_regular_queue:
                channel_type = "Regular"
            elif member.id in users_in_exp_queue:
                channel_type = "Experimental"
            else:
                await utility.dm_user(ctx.author, "The member is not in a queue at the moment")
                await self.helper.finish_processing(ctx)
                return

            self.queues[channel_type]["Entries"] = [e for e in self.queues[channel_type]["Entries"]
                                                    if e["ST"] != member.id]
            await self.update_queue_message(self.queues[channel_type])
            with open(self.QueueLocation, "w") as f:
                json.dump(self.queues, f)

            await self.helper.finish_processing(ctx)
            print("-= The KickFromQueue command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
        else:
            await utility.deny_command(ctx, "KickFromQueue")
            await utility.dm_user(ctx.author, "This command is restricted to moderators")

    @commands.command()
    async def MoveToSpot(self, ctx: commands.Context, member: nextcord.Member, spot: int):
        # mod command
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            users_in_regular_queue = [entry["ST"] for entry in self.queues["Regular"]["Entries"]]
            users_in_exp_queue = [entry["ST"] for entry in self.queues["Experimental"]["Entries"]]
            if member.id in users_in_regular_queue:
                channel_type = "Regular"
            elif member.id in users_in_exp_queue:
                channel_type = "Experimental"
            else:
                await utility.dm_user(ctx.author, "The member is not in a queue at the moment")
                await self.helper.finish_processing(ctx)
                return
            for index, item in enumerate(self.queues[channel_type]["Entries"]):
                if item["ST"] == member.id:
                    entry = self.queues[channel_type]["Entries"].pop(index)
            self.queues[channel_type]["Entries"].insert(spot - 1, entry)

            await self.update_queue_message(self.queues[channel_type])
            with open(self.QueueLocation, "w") as f:
                json.dump(self.queues, f)

            await self.helper.finish_processing(ctx)
            print("-= The MoveToSpot command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
        else:
            await utility.deny_command(ctx, "MoveToSpot")
            await utility.dm_user(ctx.author, "This command is restricted to moderators")


class FreeChannelNotificationView(nextcord.ui.View):
    def __init__(self, queue_cog: Queue, helper: utility.Helper, queue: list, game_number: str, queue_position: int):
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

    @nextcord.ui.button(label="Decline grimoire", custom_id="decline_grimoire", style=nextcord.ButtonStyle.red)
    async def decline_grimoire_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.send(
            content="You have declined the grimoire. "
                    "Use >MoveDown if you don't want to be pinged the next time a channel becomes free.",
            ephemeral=True)
        await self.queue_cog.announce_free_channel(self.game_number, self.queue_position + 1)
        self.clear_items()
        self.stop()

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        return interaction.user.id == self.queue[self.queue_position]["ST"]

    async def on_timeout(self) -> None:
        game_channel = self.helper.get_game_channel(self.game_number)
        st_role = self.helper.get_st_role(self.game_number)
        if not st_role.members:
            await game_channel.send("Previous queue entry timed out")

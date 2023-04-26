import json
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
        try:
            with open(self.helper.QueueLocation, 'r') as f:
                self.queues = json.load(f)
        except OSError:
            self.queues = {"Regular": {}, "Experimental": {}}
            with open(self.helper.QueueLocation, 'w') as f:
                json.dump(self.queues, f)

    async def update_queue_message(self, queue: dict):
        channel = get(self.helper.Guild.channels, id=queue["ChannelId"])
        if "ThreadId" in queue:
            thread = get(channel.threads, id=queue["ThreadId"])
            message = thread.fetch_message(queue["MessageId"])
        else:
            message = channel.fetch_message(queue["MessageId"])
        embed = message.embeds[0]
        embed.clear_fields()
        for entry in queue["Entries"]:
            user = get(self.helper.Guild.members, id=entry["ST"])
            entry_string = f"Script: {entry['Script']}\nAvailability: {entry['Availability']}"
            if "Notes" in entry:
                entry_string += f"\nNotes: {entry['Notes']}"
            embed.add_field(name=user.display_name, value=entry_string, inline=False)

        await message.edit(embed=embed)

    @commands.command()
    async def InitQueue(self, ctx: commands.Context, channel_type: ChannelTypeParameter):
        if self.helper.authorize_mod_command(ctx.author):
            await utility.start_processing(ctx)
            channel_type = utility.get_channel_type(channel_type)

            embed = nextcord.Embed(title=channel_type + " storytelling queue", description="Use >Enqueue to join")
            if isinstance(ctx.channel, nextcord.Thread):
                self.queues[channel_type]["ThreadId"] = ctx.channel.id
                self.queues[channel_type]["ChannelId"] = ctx.channel.channel.id
            elif isinstance(ctx.channel, nextcord.TextChannel):
                self.queues[channel_type]["ChannelId"] = ctx.channel.id
            else:
                await utility.dm_user('Please place the queue in a text channel or thread')
                return

            queue_message = await ctx.send(embed=embed)
            self.queues[channel_type]["MessageId"] = queue_message.id
            self.queues[channel_type]["Entries"] = []

            with open(self.helper.QueueLocation, "w") as f:
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

            with open(self.helper.QueueLocation, "w") as f:
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
        pass

    @commands.command()
    async def MoveDown(self, ctx: commands.Context, number_of_spots: typing.Optional[int] = 1):
        pass

    @commands.command()
    async def KickFromQueue(self, ctx: commands.Context, member: nextcord.Member):
        # mod command
        pass

    @commands.command()
    async def MoveToSpot(self, ctx: commands.Context, member: nextcord.Member, spot: int):
        # mod command
        pass

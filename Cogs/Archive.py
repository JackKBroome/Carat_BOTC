import json
import os.path
from dataclasses import dataclass, field
from typing import List, Dict

import nextcord
from dataclasses_json import dataclass_json
from nextcord import InvalidArgument, HTTPException
from nextcord.ext import commands
from nextcord.utils import get

import utility

ivy_id = 183474450237358081


@dataclass_json
@dataclass
class ThreadList:
    private_to_archive: List[int] = field(default_factory=list)
    public_to_not_archive: List[int] = field(default_factory=list)


async def copy_history(target: nextcord.abc.Messageable, history):
    async for message in history:
        embed = nextcord.Embed(description=message.content)
        embed.set_author(name=str(message.author) + " at " + str(message.created_at),
                         icon_url=message.author.display_avatar.url)
        attachment_list = []
        for i in message.attachments:
            attachment_list.append(await i.to_file())
        for i in message.reactions:
            user_list = []
            async for user in i.users():
                user_list.append(str(user.name))
            reactors = ", ".join(user_list)
            if not embed.footer.text or len(embed.footer.text) == 0:
                embed.set_footer(text=f"{i.emoji} - {reactors}, ")
            else:
                embed.set_footer(text=embed.footer.text + f" {i.emoji} - {reactors}, ")
        try:
            await target.send(embed=embed, files=attachment_list)
        except InvalidArgument:
            embed.set_footer(text=embed.footer.text + "\nError: Attachment file was too large.")
            await target.send(embed=embed)


class Archive(commands.Cog):
    bot: commands.Bot
    helper: utility.Helper
    ThreadArchivalStorage: str
    threads_by_channel: Dict[int, ThreadList]

    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper
        self.ThreadArchivalStorage = os.path.join(self.helper.StorageLocation, "thread_archival.json")
        self.threads_by_channel = {}
        if not os.path.exists(self.ThreadArchivalStorage):
            with open(self.ThreadArchivalStorage, 'w') as f:
                json.dump(self.threads_by_channel, f)
        else:
            with open(self.ThreadArchivalStorage, 'r') as f:
                json_data = json.load(f)
            for channel in json_data:
                self.threads_by_channel[channel] = ThreadList.from_dict(json_data[channel])

    def update_storage(self):
        json_data = {}
        for channel in self.threads_by_channel:
            json_data[channel] = self.threads_by_channel[channel].to_dict()
        with open(self.ThreadArchivalStorage, 'w') as f:
            json.dump(json_data, f)

    @commands.command()
    async def IncludeInArchive(self, ctx: commands.Context):
        """Marks a thread as to be included in the archive. Use in the thread you want to include.
        By default, private threads are not archived, and public threads are. Use IncludeInArchive to include a
        private thread in the archive, or to undo ExcludeFromArchive for a public thread."""
        thread = ctx.channel
        if thread.type == nextcord.ChannelType.private_thread:
            await utility.start_processing(ctx)
            if thread.parent.id not in self.threads_by_channel:
                self.threads_by_channel[thread.parent.id] = ThreadList()
            if thread.id not in self.threads_by_channel[thread.parent.id].private_to_archive:
                self.threads_by_channel[thread.parent.id].private_to_archive.append(thread.id)
            else:
                await utility.dm_user(ctx.author, "This thread is already included in the archive.")
            await utility.finish_processing(ctx)
            await self.helper.log(f"{ctx.author.display_name} has run the IncludeInArchive Command")
            self.update_storage()
        elif thread.type == nextcord.ChannelType.public_thread:
            await utility.start_processing(ctx)
            if thread.parent.id not in self.threads_by_channel:
                self.threads_by_channel[thread.parent.id] = ThreadList()
            if thread.id in self.threads_by_channel[thread.parent.id].public_to_not_archive:
                self.threads_by_channel[thread.parent.id].public_to_not_archive.remove(thread.id)
            else:
                await utility.dm_user(ctx.author, "This thread is already included in the archive.")
            await utility.finish_processing(ctx)
            await self.helper.log(f"{ctx.author.display_name} has run the IncludeInArchive Command")
            self.update_storage()
        else:
            await utility.deny_command(ctx, "This command can only be used in a thread.")

    @commands.command()
    async def ExcludeFromArchive(self, ctx: commands.Context):
        """Marks a thread as not to be included in the archive. Use in the thread you want to exclude.
        By default, private threads are not archived, and public threads are. Use ExcludeFromArchive to exclude a
        public thread from the archive, or to undo IncludeInArchive for a private thread."""
        thread = ctx.channel
        if thread.type == nextcord.ChannelType.private_thread:
            await utility.start_processing(ctx)
            if thread.parent.id not in self.threads_by_channel:
                self.threads_by_channel[thread.parent.id] = ThreadList()
            if thread.id in self.threads_by_channel[thread.parent.id].private_to_archive:
                self.threads_by_channel[thread.parent.id].private_to_archive.remove(thread.id)
            else:
                await utility.dm_user(ctx.author, "This thread is already not included in the archive.")
            await utility.finish_processing(ctx)
            await self.helper.log(f"{ctx.author.display_name} has run the ExcludeFromArchive Command")
            self.update_storage()
        elif thread.type == nextcord.ChannelType.public_thread:
            await utility.start_processing(ctx)
            if thread.parent.id not in self.threads_by_channel:
                self.threads_by_channel[thread.parent.id] = ThreadList()
            if thread.id not in self.threads_by_channel[thread.parent.id].public_to_not_archive:
                self.threads_by_channel[thread.parent.id].public_to_not_archive.append(thread.id)
            else:
                await utility.dm_user(ctx.author, "This thread is already not included in the archive.")
            await utility.finish_processing(ctx)
            await self.helper.log(f"{ctx.author.display_name} has run the ExcludeFromArchive Command")
            self.update_storage()
        else:
            await utility.deny_command(ctx, "This command can only be used in a thread.")

    @commands.command()
    async def OffServerArchive(self, ctx: commands.Context, archive_server_id: int, archive_channel_id: int):
        """Copies the channel the message was sent in to the provided server and channel, message by message.
        Attachments may not be preserved if they are too large. Also creates a discussion thread at the end."""
        # Credit to Ivy for this code, mostly their code

        archive_server = self.helper.bot.get_guild(archive_server_id)
        if archive_server is None:
            await utility.dm_user(ctx.author, f"Was unable to find server with ID {archive_server_id}")
            return
        archive_channel = get(archive_server.channels, id=archive_channel_id)
        if archive_channel is None:
            await utility.dm_user(ctx.author, f"Was unable to find channel with ID {archive_server_id}")
            return
        channel_to_archive = ctx.message.channel

        access = self.helper.authorize_mod_command(ctx.author)
        # Ivy Access
        if access or ctx.author.id == ivy_id:
            # React on Approval
            await utility.start_processing(ctx)
            channel_history = channel_to_archive.history(limit=None, oldest_first=True)

            await copy_history(archive_channel, channel_history)

            for thread in channel_to_archive.threads:
                if thread.is_private() and (thread.parent.id not in self.threads_by_channel or
                                            thread.id not in self.threads_by_channel[
                                                channel_to_archive.id].private_to_archive):
                    continue
                elif (not thread.is_private()) and thread.parent.id in self.threads_by_channel and \
                        thread.id in self.threads_by_channel[channel_to_archive.id].public_to_not_archive:
                    continue
                try:
                    archive_thread = await archive_channel.create_thread(name=thread.name,
                                                                         type=nextcord.ChannelType.public_thread)
                    thread_history = thread.history(limit=None, oldest_first=True)
                    await copy_history(archive_thread, thread_history)
                except HTTPException:
                    await archive_channel.send(f"Failed to create thread '{thread.name}'")
                    continue

            await archive_channel.create_thread(name="Chat about the game", type=nextcord.ChannelType.public_thread)

            await utility.finish_processing(ctx)
            self.threads_by_channel.pop(channel_to_archive.id, None)
            self.update_storage()

            await self.helper.log(f"{ctx.author.display_name} has run the OffServerArchive Command")
            await utility.dm_user(ctx.author, f"Your Archive for {ctx.message.channel.name} is done.")
        else:
            await utility.deny_command(ctx, "You do not have permission to use this command")


def setup(bot: commands.Bot):
    bot.add_cog(Archive(bot, utility.Helper(bot)))

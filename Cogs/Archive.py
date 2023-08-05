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


async def convert_message(message):
    message_content = message.content
    embed = nextcord.Embed(description=message_content)
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
    return attachment_list, embed


class Archive(commands.Cog):
    bot: commands.Bot
    helper: utility.Helper
    ThreadArchivalStorage: str
    threads: Dict[int, ThreadList]

    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper
        self.ThreadArchivalStorage = os.path.join(self.helper.StorageLocation, "thread_archival.json")
        self.threads = {}
        if not os.path.exists(self.ThreadArchivalStorage):
            with open(self.ThreadArchivalStorage, 'w') as f:
                json.dump(self.threads, f)
        else:
            with open(self.ThreadArchivalStorage, 'r') as f:
                json_data = json.load(f)
            for channel in json_data:
                self.threads[channel] = ThreadList.from_dict(json_data[channel])

    def update_storage(self):
        json_data = {}
        for channel in self.threads:
            json_data[channel] = self.threads[channel].to_dict()
        with open(self.ThreadArchivalStorage, 'w') as f:
            json.dump(json_data, f)

    @commands.command()
    async def IncludeInArchive(self, ctx: commands.Context):
        """"""

    @commands.command()
    async def DoNotArchive(self, ctx: commands.Context):
        pass

    @commands.command()
    async def OffServerArchive(self, ctx: commands.Context, archive_server_id: int, archive_channel_id: int):
        """Copies the channel the message was sent in to the provided server and channel, message by message.
        Attachments may not be preserved if they are too large. Also creates a discussion thread at the end."""
        # Credit to Ivy for this code, mostly their code

        archive_server = self.helper.bot.get_guild(archive_server_id)
        archive_channel = get(archive_server.channels, id=archive_channel_id)

        channel_to_archive = ctx.message.channel

        access = self.helper.authorize_mod_command(ctx.author)
        # Ivy Access
        if access or ctx.author.id == ivy_id:
            # React on Approval
            await utility.start_processing(ctx)
            channel_history = channel_to_archive.history(limit=None, oldest_first=True)

            async for message in channel_history:
                attachment_list, embed = await convert_message(message)
                try:
                    await archive_channel.send(embed=embed, files=attachment_list)
                except InvalidArgument:
                    embed.set_footer(text=embed.footer.text + "\nError: Attachment file was too large.")
                    await archive_channel.send(embed=embed)

            for thread in channel_to_archive.threads:
                if thread.is_private() and thread.id not in self.threads[channel_to_archive.id].private_to_archive:
                    continue
                elif not thread.is_private() and thread.id in self.threads[channel_to_archive.id].public_to_not_archive:
                    continue
                try:
                    archive_thread = await archive_channel.create_thread(name=thread.name, type=nextcord.ChannelType.public_thread)
                    thread_history = thread.history(limit=None, oldest_first=True)
                    async for message in thread_history:
                        attachment_list, embed = await convert_message(message)
                        try:
                            await archive_thread.send(embed=embed, files=attachment_list)
                        except InvalidArgument:
                            embed.set_footer(text=embed.footer.text + "\nError: Attachment file was too large.")
                            await archive_thread.send(embed=embed)
                except HTTPException:
                    await archive_channel.send(f"Failed to create thread '{thread.name}'")
                    continue

            await archive_channel.create_thread(name="Chat about the game", type=nextcord.ChannelType.public_thread)

            await self.helper.finish_processing(ctx)
            self.threads.pop(archive_channel_id)
            self.update_storage()

            await self.helper.log(f"{ctx.author.display_name} has run the OffServerArchive Command")
            await utility.dm_user(ctx.author, f"Your Archive for {ctx.message.channel.name} is done.")
        else:
            await utility.deny_command(ctx)
            await utility.dm_user(ctx.author, "You do not have permission to use this command")

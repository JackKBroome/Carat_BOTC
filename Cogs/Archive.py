import json
import os.path
from dataclasses import dataclass, field
from typing import List, Dict

import nextcord
from dataclasses_json import dataclass_json
from nextcord import InvalidArgument, HTTPException
from nextcord.ext import tasks, commands
from nextcord.utils import get

import utility

ivy_id = 183474450237358081

@dataclass_json
@dataclass
class ThreadList:
    private_to_archive: List[int] = field(default_factory=list)
    public_to_not_archive: List[int] = field(default_factory=list)

class Game(commands.Cog):
    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper

async def copy_history(target: nextcord.abc.Messageable, history) -> int:
    errors = 0
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
            embed.set_footer(text=f"{embed.footer.text}\nError: Attachment file was too large.")
            await target.send(embed=embed)
        except HTTPException as e:
            if e.status == 413:
                embed.set_footer(text=f"{embed.footer.text}\nError: Attachment file was too large.")
                await target.send(embed=embed)
            else:
                await target.send(f"Error: this message caused an unknown issue: {e.status} - {e.text}")
                errors += 1
    return errors


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
                json.dump(self.threads_by_channel, f, indent=2)
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
            json.dump(json_data, f, indent=2)

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
    async def ClaimRole(self, ctx: commands.Context):
        await utility.start_processing(ctx)
        Unique_role_name = str(ctx.author.id)
        archive_server = self.helper.bot.get_guild(1203126128693354516)
        Unique_role = nextcord.utils.get(archive_server.roles, name=Unique_role_name)
        if Unique_role is None:
            Unique_role = await archive_server.create_role(name=Unique_role_name)
        await ctx.author.add_roles(Unique_role)
        await utility.finish_processing(ctx)

    @commands.command()
    async def ArchiveGame(self, ctx, game_number):
        """Moves the game channel to the archive and creates a new empty channel for the next game.
        Also makes the kibitz channel hidden from the public. Use after post-game discussion has concluded.
        Do not remove the game number from the channel name until after archiving.
        You will still be able to do so afterward."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            

            townsfolk_role = self.helper.Guild.default_role
            st_role = self.helper.get_st_role(game_number)
            game_channel = self.helper.get_game_channel(game_number)
            if game_channel is None:
                await utility.deny_command(ctx, "No game for that number found")
                return
            game_position = game_channel.position
            game_channel_name = game_channel.name
            archive_category = self.helper.ArchiveCategory
            if len(archive_category.channels) == 50:
                await utility.deny_command(ctx, "Archive category is full")
                await game_channel.send(f"{self.helper.ModRole.mention} The archive category is full, so this channel "
                                        f"cannot be archived")
                return
            if game_number[0] != "r":
                new_channel = await game_channel.clone(reason="New Game")
                await new_channel.edit(position=game_position, name=f"text-game-{game_number}", topic="")
            # remove manage threads permission so future STs for the game number can't see private threads
            st_permissions = game_channel.overwrites[st_role]
            st_permissions.update(manage_threads=None)
            await game_channel.set_permissions(st_role, overwrite=st_permissions)
            for st in st_role.members:
                if st in game_channel.overwrites:
                    member_permissions = game_channel.overwrites[st]
                    member_permissions.update(manage_threads=True)
                    await game_channel.set_permissions(st, overwrite=member_permissions)
                else:
                    await game_channel.set_permissions(st, manage_threads=True)
            await game_channel.edit(category=archive_category, name=str(game_channel_name) + " Archived on " + str(
                strftime("%a, %d %b %Y %H %M %S ", gmtime())), topic="")

            kibitz_channel = self.helper.get_kibitz_channel(game_number)
            await kibitz_channel.set_permissions(townsfolk_role, view_channel=False)

            channel_to_archive = ctx.message.channel
            archive_server_id = 1203126128693354516
            archive_server = self.helper.bot.get_guild(archive_server_id)
            if archive_server is None:
                await utility.dm_user(ctx.author, f"Was unable to find server with ID {archive_server_id}")
                return
            archive_channel_id = 0
            archive_channel = get(archive_server.channels, id=archive_channel_id)
            if archive_channel is None:
                archive_channel = await archive_server.create_text_channel(name="Temp Channel")
                Channel_name = str(channel_to_archive.name) + "-" + str(member.display_name)
                await archive_channel.edit(name=Channel_name)

            access = self.helper.authorize_mod_command(ctx.author)
            member = ctx.author
            # Ivy Access
            if 1 == 1:
                # React on Approval
                await utility.start_processing(ctx)
                Unique_role_name = str(member.id)
                Unique_role = nextcord.utils.get(archive_server.roles, name=Unique_role_name)
                if Unique_role is None:
                    Unique_role = await archive_server.create_role(name=Unique_role_name)

                channel_history = channel_to_archive.history(limit=None, oldest_first=True)
                errors = await copy_history(archive_channel, channel_history)
                for thread in channel_to_archive.threads:
                    if thread.is_private() and (thread.parent.id not in self.threads_by_channel or
                                                thread.id not in self.threads_by_channel[
                                                    channel_to_archive.id].private_to_archive):
                        try:
                            archive_thread = await archive_channel.create_thread(
                                name=str(thread.name),
                                auto_archive_duration=4320,  # 3 days
                                type=nextcord.ChannelType.private_thread,
                                invitable=True,
                                reason="Private Thread"
                                )
                            thread_history = thread.history(limit=None, oldest_first=True)
                            errors += await copy_history(archive_thread, thread_history)
                            continue
                        except HTTPException:
                            await archive_channel.send(f"Failed to create thread '{thread.name}'")
                            continue
                    elif (not thread.is_private()) and thread.parent.id in self.threads_by_channel and \
                            thread.id in self.threads_by_channel[channel_to_archive.id].public_to_not_archive:
                        continue
                    try:
                        archive_thread = await archive_channel.create_thread(name=thread.name,
                                                                            type=nextcord.ChannelType.public_thread)
                        thread_history = thread.history(limit=None, oldest_first=True)
                        errors += await copy_history(archive_thread, thread_history)
                    except HTTPException:
                        await archive_channel.send(f"Failed to create thread '{thread.name}'")
                        continue
                await archive_channel.create_thread(name="Chat about the game", type=nextcord.ChannelType.public_thread)
                await archive_channel.set_permissions(Unique_role, manage_threads=True)
                await utility.finish_processing(ctx)
                self.threads_by_channel.pop(channel_to_archive.id, None)
                self.update_storage()
                #await self.helper.log(f"{ctx.author.display_name} has run the OffServerArchive Command")

            # React for completion
            await utility.finish_processing(ctx)

        else:
            await utility.deny_command(ctx, "You are not the current ST for game " + game_number)

        await self.helper.log(f"{ctx.author.mention} has run the ArchiveGame Command for Game {game_number}")

    @commands.command()
    async def OffServerArchive(self, ctx: commands.Context, archive_server_id: int, member: nextcord.Member, archive_channel_id: int =0):
        """Copies the channel the message was sent in to the provided server and channel, message by message.
        Attachments may not be preserved if they are too large. Also creates a discussion thread at the end.
        Public threads are also copied, private threads are not, except where someone specifically excluded or
        included them."""
        
        channel_to_archive = ctx.message.channel

        archive_server = self.helper.bot.get_guild(archive_server_id)
        if archive_server is None:
            await utility.dm_user(ctx.author, f"Was unable to find server with ID {archive_server_id}")
            return

        archive_channel = get(archive_server.channels, id=archive_channel_id)
        if archive_channel is None:
            archive_channel = await archive_server.create_text_channel(name="Temp Channel")
            Channel_name = str(channel_to_archive.name) + "-" + str(member.display_name)
            await archive_channel.edit(name=Channel_name)
                
        access = self.helper.authorize_mod_command(ctx.author)
        # Ivy Access
        if access or ctx.author.id == ivy_id:
            # React on Approval
            await utility.start_processing(ctx)

            Unique_role_name = str(member.id)
            Unique_role = nextcord.utils.get(archive_server.roles, name=Unique_role_name)
            if Unique_role is None:
                Unique_role = await archive_server.create_role(name=Unique_role_name)
            
            channel_history = channel_to_archive.history(limit=None, oldest_first=True)

            errors = await copy_history(archive_channel, channel_history)

            for thread in channel_to_archive.threads:
                if thread.is_private() and (thread.parent.id not in self.threads_by_channel or
                                            thread.id not in self.threads_by_channel[
                                                channel_to_archive.id].private_to_archive):
                    try:
                        archive_thread = await archive_channel.create_thread(
                            name=str(thread.name),
                            auto_archive_duration=4320,  # 3 days
                            type=nextcord.ChannelType.private_thread,
                            invitable=True,
                            reason="Private Thread"
                            )
                        thread_history = thread.history(limit=None, oldest_first=True)
                        errors += await copy_history(archive_thread, thread_history)
                        continue
                    except HTTPException:
                        await archive_channel.send(f"Failed to create thread '{thread.name}'")
                        continue

                elif (not thread.is_private()) and thread.parent.id in self.threads_by_channel and \
                        thread.id in self.threads_by_channel[channel_to_archive.id].public_to_not_archive:
                    continue

                try:
                    archive_thread = await archive_channel.create_thread(name=thread.name,
                                                                         type=nextcord.ChannelType.public_thread)
                    thread_history = thread.history(limit=None, oldest_first=True)
                    errors += await copy_history(archive_thread, thread_history)
                except HTTPException:
                    await archive_channel.send(f"Failed to create thread '{thread.name}'")
                    continue

            await archive_channel.create_thread(name="Chat about the game", type=nextcord.ChannelType.public_thread)

            await archive_channel.set_permissions(Unique_role, manage_threads=True)

            await utility.finish_processing(ctx)
            self.threads_by_channel.pop(channel_to_archive.id, None)
            self.update_storage()

            await self.helper.log(f"{ctx.author.display_name} has run the OffServerArchive Command")
            message = f"Your Archive for {ctx.message.channel.name} is done."
            if errors > 0:
                message += f" {errors} messages caused unknown errors and were not archived."
            await utility.dm_user(ctx.author, message)
        else:
            await utility.deny_command(ctx, "You do not have permission to use this command")

    @tasks.loop(hours=24)
    async def adjust_thread_archive_time():

        guild = bot.get_guild(569683781800296501)
        EXCLUDED_CHANNELS = [1218704547585724537, 1218706422297137272, 777660207424733204, 1173738081036283924]
        ACTIVE_THREAD_CATEGORIES = [569683781846433930]

        for current_thread_ID in ACTIVE_THREAD_CATEGORIES:
            category = nextcord.utils.get(guild.categories, id=current_thread_ID)

            for channel in category.channels:
                if channel.id in EXCLUDED_CHANNELS:
                    continue
            
                threads = await channel.threads()
                for thread in threads:
                    try:
                        await thread.edit(auto_archive_duration=10080)  # 10080 minutes = 7 days
                        await thread.edit(auto_archive_duration=4320)  # 4,320 minutes = 3 days
                    except Exception as e:
                        print(f"Failed to update thread: {thread.name} in channel: {channel.name}. Error: {e}")

def setup(bot: commands.Bot):
    bot.add_cog(Archive(bot, utility.Helper(bot)))

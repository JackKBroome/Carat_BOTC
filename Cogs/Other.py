from time import strftime, gmtime

import nextcord
from nextcord.ext import commands
from nextcord.utils import get

import utility

ivy_id = 183474450237358081


class Other(commands.Cog):

    def __init__(self, bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper

    @commands.command()
    async def ShowSignUps(self, ctx: commands.Context, game_number: str):
        st_role = self.helper.get_st_role(game_number)
        st_names = [st.display_name for st in st_role.members]
        player_role = self.helper.get_game_role(game_number)
        player_names = [player.display_name for player in player_role.members]
        kibitz_role = self.helper.get_kibitz_role(game_number)
        kibitz_names = [kibitzer.display_name for kibitzer in kibitz_role.members]

        output_string = f"Game {game_number} Players\n" \
                        f"Storyteller:\n"
        output_string += "\n".join(st_names)

        output_string += "\nPlayers:\n"
        output_string += "\n".join(player_names)

        output_string += "\nKibitz members:\n"
        output_string += "\n".join(kibitz_names)

        dm_success = await utility.dm_user(ctx.author, output_string)
        if not dm_success:
            await ctx.send(content=output_string, reference=ctx.message)
        await self.helper.log(f"{ctx.author.mention} has run the ShowSignUps Command")

    @commands.command()
    async def OffServerArchive(self, ctx, archive_server_id: int, archive_channel_id: int):
        # Credit to Ivy for this code, mostly their code

        archive_server = self.helper.bot.get_guild(archive_server_id)
        archive_channel = get(archive_server.channels, id=archive_channel_id)

        channel_to_archive = ctx.message.channel

        access = self.helper.authorize_mod_command(ctx.author)
        # Ivy Access
        if access or ctx.author.id == ivy_id:
            # React on Approval
            await utility.start_processing(ctx)

            async for current_message in channel_to_archive.history(limit=None, oldest_first=True):
                message_content = current_message.content
                embed = nextcord.Embed(description=message_content)
                embed.set_author(name=str(current_message.author) + " at " + str(current_message.created_at),
                                 icon_url=current_message.author.display_avatar.url)
                attachment_list = []
                for i in current_message.attachments:
                    attachment_list.append(await i.to_file())
                for i in current_message.reactions:
                    user_list = []
                    async for user in i.users():
                        user_list.append(str(user.name))
                    reactors = ", ".join(user_list)
                    if len(embed.footer.text) != 0:
                        embed.set_footer(text=embed.footer.text + f" {i.emoji} - {reactors}, ")
                    else:
                        embed.set_footer(text=f"{i.emoji} - {reactors}, ")
                try:
                    await archive_channel.send(embed=embed, files=attachment_list)
                except:
                    try:
                        embed.set_footer(text=embed.footer.text + "/nError Attachment file was too large.")
                    except:
                        embed.set_footer(text="Error Attachment file was too large.")
                    await archive_channel.send(embed=embed)

            await self.helper.finish_processing(ctx)

            await self.helper.log(f"{ctx.author.display_name} has run the OffServerArchive Command")
            await utility.dm_user(ctx.author, f"Your Archive for {ctx.message.channel.name} is done.")
        else:
            await utility.deny_command(ctx, "OffServerArchive")
            await utility.dm_user(ctx.author, "You do not have permission to use this command")

    @commands.command()
    async def CreateThreads(self, ctx, game_number):
        if await self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)

            for player in self.helper.get_game_role(game_number).members:
                thread = await self.helper.get_game_channel(game_number).create_thread(
                    name=f"ST Thread {player.display_name}",
                    auto_archive_duration=4320,  # 3 days
                    type=nextcord.ChannelType.private_thread,
                    reason=f"Preparing text game {game_number}"
                )

                await thread.add_user(player)
                for st in self.helper.get_st_role(game_number).members:
                    await thread.add_user(st)

            await self.helper.finish_processing(ctx)

            print("-= The CreateThreads command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
        else:
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))
            await utility.deny_command(ctx, "CreateThreads")

        await self.helper.log(f"{ctx.author.mention} has run the CreateThreads Command on Game {game_number}")

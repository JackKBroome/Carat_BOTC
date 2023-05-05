from time import strftime, gmtime

import nextcord
from nextcord.ext import commands

import utility
from Cogs.TextQueue import TextQueue

MaxGameNumber = 15
PotentialGames = [str(n) for n in range(1, MaxGameNumber)] + ["x" + str(n) for n in range(1, MaxGameNumber)]


class Grimoire(commands.Cog):
    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper

    @commands.command()
    async def ClaimGrimoire(self, ctx: commands.Context, game_number: str):

        st_role = self.helper.get_st_role(game_number)

        # stX Access
        if len(st_role.members) == 0 or self.helper.authorize_mod_command(ctx.author):
            # React on Approval
            await utility.start_processing(ctx)

            await ctx.author.add_roles(st_role)
            await utility.dm_user(ctx.author, "You are now the current ST for game " + game_number)
            queue: TextQueue | None = self.bot.get_cog('Queue')
            if queue:
                channel_type = "Experimental" if game_number[0] == 'x' else "Regular"
                users_in_queue = [entry["ST"] for entry in queue.queues[channel_type]["Entries"]]
                if ctx.author.id not in users_in_queue:
                    game_channel = self.helper.get_game_channel(game_number)
                    await game_channel.send(f"{ctx.author.mention} Warning - you are taking a channel without having "
                                            f"been in the appropriate text ST queue. If that's how it's supposed to "
                                            f"be, carry on - otherwise you can drop the grimoire with `>DropGrimoire` "
                                            f"and join the queue with `>JoinTextQueue` (see `>HelpMe` for details)")
                await queue.user_leave_queue(ctx.author)
            await self.helper.finish_processing(ctx)
            print("-= The ClaimGrimoire command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
        else:
            await utility.dm_user(ctx.author,
                                  "This channel already has " + str(len(st_role.members)) + " STs. These users are:\n" +
                                  "\n".join([ST.display_name for ST in st_role.members])
                                  )
            await utility.deny_command(ctx, "ClaimGrimoire")

        await self.helper.log(f"{ctx.author.mention} has run the ClaimGrimoire Command  for game {game_number}")

    @commands.command()
    async def GiveGrimoire(self, ctx, game_number, member: nextcord.Member):
        # Check for access

        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            st_role = self.helper.get_st_role(game_number)
            await member.add_roles(st_role)
            await ctx.author.remove_roles(st_role)
            await utility.dm_user(ctx.author,
                                  "You have assigned the current ST role for game " + str(game_number) +
                                  " to " + member.display_name)
            await self.helper.finish_processing(ctx)
            print("-= The GiveGrimoire command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + f" on {member.name}=-"))
        else:
            await utility.deny_command(ctx, "GiveGrimoire")

        await self.helper.log(
            f"{ctx.author.mention} has run the GiveGrimoire Command on {member.display_name} for game {game_number}")

    @commands.command()
    async def DropGrimoire(self, ctx: commands.Context, game_number):
        # Check for access

        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            st_role = self.helper.get_st_role(game_number)
            await ctx.author.remove_roles(st_role)
            dm_content = "You have removed the current ST role from yourself for game " + str(game_number)
            dm_success = await utility.dm_user(ctx.author, dm_content)
            if not dm_success:
                await ctx.send(content=dm_content, reference=ctx.message)
            queue = self.bot.get_cog('Queue')
            if queue and not st_role.members:
                await queue.announce_free_channel(game_number, 0)
            await self.helper.finish_processing(ctx)
            print("-= The DropGrimoire command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
        else:
            await utility.deny_command(ctx, "DropGrimoire")
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))

        await self.helper.log(f"{ctx.author.mention} has run the DropGrimoire Command for game {game_number}")

    @commands.command()
    async def ShareGrimoire(self, ctx: commands.Context, game_number, member: nextcord.Member):
        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)

            await member.add_roles(self.helper.get_st_role(game_number))

            dm_content = "You have assigned the current ST for game " + str(game_number) + " to " + \
                         str(member.display_name)
            dm_success = await utility.dm_user(ctx.author, dm_content)
            if not dm_success:
                await ctx.send(content=dm_content, reference=ctx.message)
            await self.helper.finish_processing(ctx)
            print("-= The ShareGrimoire command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + f" on {member.name}=-"))
        else:
            await utility.deny_command(ctx, "ShareGrimoire")
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))

        await self.helper.log(
            f"{ctx.author.mention} has run the ShareGrimoire Command on {member.display_name} for game {game_number}")

    @commands.command()
    async def FindGrimoire(self, ctx: commands.Context):

        # find existing games by getting all channel names in the text games category
        # and checking which of 1 to [MaxGameNumber] and x1 to x[MaxGameNumber] appear in them
        channel_names_string = " ".join([channel.name for channel in self.helper.TextGamesCategory.channels])
        games = [x for x in PotentialGames if x in channel_names_string]
        message = ""
        for j in games:
            try:
                current_sts = self.helper.get_st_role(j).members
                if not current_sts:
                    message += "There is currently no assigned ST for game " + str(j) + "\n"
                else:
                    message += f"Game {j}'s STs are: " + ", ".join([st.display_name for st in current_sts]) + "\n"
            except:
                print(f"game {j} not found")
        dm_success = await utility.dm_user(ctx.author, message)
        if not dm_success:
            await ctx.send(message)
        await self.helper.log(f"{ctx.author.mention} has run the FindGrimoire Command")

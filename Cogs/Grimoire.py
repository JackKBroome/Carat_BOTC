import logging
from typing import Optional

import nextcord
from nextcord.ext import commands

import utility
from Cogs.TextQueue import TextQueue
from Cogs.Townsquare import Townsquare, Player



class Grimoire(commands.Cog):
    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper

    @commands.command()
    async def ClaimGrimoire(self, ctx: commands.Context, game_number: str):
        """Grants you the ST role of the given game.
        Also removes you from the relevant queue. Fails if there is already an ST for that game."""
        st_role = self.helper.get_st_role(game_number)

        if len(st_role.members) == 0 or self.helper.authorize_mod_command(ctx.author):
            # React on Approval
            await utility.start_processing(ctx)

            await ctx.author.add_roles(st_role)
            await utility.dm_user(ctx.author, "You are now the current ST for game " + game_number)
            queue: Optional[TextQueue] = self.bot.get_cog('TextQueue')
            if queue:
                channel_type = "Experimental" if game_number[0] == 'x' else "Regular"
                users_in_queue = [entry.st for entry in queue.queues[channel_type].entries]
                if ctx.author.id not in users_in_queue:
                    game_channel = self.helper.get_game_channel(game_number)
                    await game_channel.send(f"{ctx.author.mention} Warning - you are taking a channel without having "
                                            f"been in the appropriate text ST queue. If that's how it's supposed to "
                                            f"be, carry on - otherwise you can drop the grimoire with `>DropGrimoire` "
                                            f"and join the queue with `>JoinTextQueue` (see `>HelpMe` for details)")
                await queue.user_leave_queue(ctx.author)
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx,
                                       "This channel already has {0} STs. These users are:\n{1}".format(
                                           str(len(st_role.members)),
                                           "\n".join([ST.display_name for ST in st_role.members]))
                                       )

        await self.helper.log(f"{ctx.author.mention} has run the ClaimGrimoire Command  for game {game_number}")

    @commands.command()
    async def GiveGrimoire(self, ctx, game_number, member: nextcord.Member):
        """Removes the ST role for the game from you and gives it to the given user.
        You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            st_role = self.helper.get_st_role(game_number)
            await member.add_roles(st_role)
            await ctx.author.remove_roles(st_role)
            await utility.dm_user(ctx.author,
                                  "You have assigned the current ST role for game " + str(game_number) +
                                  " to " + member.display_name)
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You are not the current ST for game " + game_number)

        await self.helper.log(
            f"{ctx.author.mention} has run the GiveGrimoire Command on {member.display_name} for game {game_number}")

    @commands.command()
    async def DropGrimoire(self, ctx: commands.Context, game_number):
        """Removes the ST role for the game from you.
        Also announces the free channel if there is no other ST."""

        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            st_role = self.helper.get_st_role(game_number)
            await ctx.author.remove_roles(st_role)
            dm_content = "You have removed the current ST role from yourself for game " + str(game_number)
            dm_success = await utility.dm_user(ctx.author, dm_content)
            if not dm_success:
                await ctx.send(content=dm_content, reference=ctx.message)
            queue: Optional[TextQueue] = self.bot.get_cog('TextQueue')
            if queue and not st_role.members:
                await queue.announce_free_channel(game_number, 0)
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You are not the current ST for game " + game_number)

        await self.helper.log(f"{ctx.author.mention} has run the DropGrimoire Command for game {game_number}")

    @commands.command()
    async def ShareGrimoire(self, ctx: commands.Context, game_number: str, member: nextcord.Member):
        """Gives the ST role for the game to the given user without removing it from you.
        Use this if you want to co-ST a game. You can provide a user by ID, mention/ping, or nickname, though giving
        the nickname may find the wrong user."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)

            await member.add_roles(self.helper.get_st_role(game_number))
            townsquare: Optional[Townsquare] = self.bot.get_cog('Townsquare')
            if townsquare and game_number in townsquare.town_squares:
                townsquare.town_squares[game_number].sts.append(Player(member.id, member.display_name))
            dm_content = f"You have assigned the ST role for game {game_number} to {member.display_name}"
            dm_success = await utility.dm_user(ctx.author, dm_content)
            if not dm_success:
                await ctx.send(content=dm_content, reference=ctx.message)
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You are not the current ST for game " + game_number)

        await self.helper.log(
            f"{ctx.author.mention} has run the ShareGrimoire Command on {member.display_name} for game {game_number}")

    @commands.command()
    async def FindGrimoire(self, ctx: commands.Context):
        """Sends you a DM listing all games and whether they currently have an ST.
        If they have an ST, it will list them."""
        # find existing games by getting all channel names in the text games category
        # and checking which of 1 to [MaxGameNumber] and x1 to x[MaxGameNumber] appear in them
        await utility.start_processing(ctx)
        channel_names_string = " ".join([channel.name for channel in self.helper.TextGamesCategory.channels])
        games = [x for x in utility.PotentialGames if x in channel_names_string]
        message = ""
        for j in games:
            st_role = self.helper.get_st_role(j)
            if not st_role:
                logging.warning(f"ST role for game {j} not found")
            elif not st_role.members:
                message += "There is currently no assigned ST for game " + str(j) + "\n"
            else:
                message += f"Game {j}'s STs are: " + ", ".join([st.display_name for st in st_role.members]) + "\n"
        dm_success = await utility.dm_user(ctx.author, message)
        if not dm_success:
            await ctx.send(message)
        await utility.finish_processing(ctx)


def setup(bot: commands.Bot):
    bot.add_cog(Grimoire(bot, utility.Helper(bot)))

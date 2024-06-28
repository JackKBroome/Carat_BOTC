from time import strftime, gmtime
from typing import Optional

from nextcord.ext import commands

import utility
from Cogs.Townsquare import Townsquare


class Game(commands.Cog):
    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper

    @commands.command()
    async def OpenKibitz(self, ctx, game_number):
        """Makes the kibitz channel to the game visible to the public.
        Players will still need to remove their game role to see it. Use after the game has concluded.
        Will also send a message reminding players to give feedback for the ST and provide a link to do so.
        In most cases, EndGame may be the more appropriate command."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)

            # Change permission of Kibitz to allow Townsfolk to view
            townsfolk_role = self.helper.Guild.default_role
            kibitz_channel = self.helper.get_kibitz_channel(game_number)
            await kibitz_channel.set_permissions(townsfolk_role, view_channel=True)
            game_role = self.helper.get_game_role(game_number)
            await ctx.channel.send(
                f"{game_role.mention} Kibitz is now being opened - remove your game role to access it. " +
                f"Remember to give your ST(s) any feedback you may have!\n" +
                f"Feedback form: https://forms.gle/3PsSPs4TznRkMhY8A")

            # React for completion
            await utility.finish_processing(ctx)
        else:
            # React on Disapproval
            await utility.deny_command(ctx, "You are not the current ST for game " + str(game_number))

        await self.helper.log(f"{ctx.author.mention} has run the OpenKibitz Command on Game {game_number}")

    @commands.command()
    async def CloseKibitz(self, ctx, game_number):
        """Makes the kibitz channel to the game hidden from the public.
        This is typically already the case when you claim a grimoire, but might not be in some cases. Make sure none of
         your players have the kibitz role, as they could still see the channel in that case."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)

            # Change permission of Kibitz to allow Townsfolk to view
            townsfolk_role = self.helper.Guild.default_role

            kibitz_channel = self.helper.get_kibitz_channel(game_number)
            await kibitz_channel.set_permissions(townsfolk_role, view_channel=False)

            # React for completion
            await utility.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "You are not the current ST for game " + game_number)

        await self.helper.log(f"{ctx.author.mention} has run the CloseKibitz Command on Game {game_number}")

    @commands.command()
    async def EndGame(self, ctx: commands.Context, game_number):
        """Opens Kibitz to the public and cleans up after the game.
        This includes removing the game role from players and the kibitz role from kibitzers, sending a message
        reminding players to give feedback for the ST with a link to do so,
        and resetting the town square if there is one."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)

            # Gather member list & role information
            kibitz_role = self.helper.get_kibitz_role(game_number)
            game_role = self.helper.get_game_role(game_number)

            await ctx.channel.send(
                f"{game_role.mention} Kibitz is now being opened. "
                f"Remember to give your ST(s) any feedback you may have!\n" +
                f"Feedback form: https://forms.gle/3PsSPs4TznRkMhY8A"
            )
            members = game_role.members
            members += kibitz_role.members

            # Remove roles from non-bot players
            for member in members:
                if not member.bot:
                    await member.remove_roles(kibitz_role)
                    await member.remove_roles(game_role)

            townsquare: Optional[Townsquare] = self.bot.get_cog("Townsquare")
            if townsquare and game_number in townsquare.town_squares:
                townsquare.town_squares.pop(game_number)
                townsquare.update_storage()

            # Change permission of Kibitz to allow Townsfolk to view
            townsfolk_role = self.helper.Guild.default_role
            kibitz_channel = self.helper.get_kibitz_channel(game_number)
            await kibitz_channel.set_permissions(townsfolk_role, view_channel=True)

            # React for completion
            await utility.finish_processing(ctx)

        else:
            # React on Disapproval
            await utility.deny_command(ctx, "You are not the current ST for game " + game_number)

        await self.helper.log(f"{ctx.author.mention} has run the EndGame Command on Game {game_number}")

    #@commands.command()
    #async def ArchiveGame(self, ctx, game_number):
    #    """Moves the game channel to the archive and creates a new empty channel for the next game.
    #    Also makes the kibitz channel hidden from the public. Use after post-game discussion has concluded.
    #    Do not remove the game number from the channel name until after archiving.
    #    You will still be able to do so afterward."""
    #    if self.helper.authorize_st_command(ctx.author, game_number):
    #        # React on Approval
    #        await utility.start_processing(ctx)]
    #
    #        townsfolk_role = self.helper.Guild.default_role
    #        st_role = self.helper.get_st_role(game_number)
    #        game_channel = self.helper.get_game_channel(game_number)
    #        if game_channel is None:
    #            await utility.deny_command(ctx, "No game for that number found")
    #            return
    #        game_position = game_channel.position
    #        game_channel_name = game_channel.name
    #        archive_category = self.helper.ArchiveCategory
    #        if len(archive_category.channels) == 50:
    #            await utility.deny_command(ctx, "Archive category is full")
    #            await game_channel.send(f"{self.helper.ModRole.mention} The archive category is full, so this channel "
    #                                    f"cannot be archived")
    #            return
    #        if game_number[0] != "r":
    #            new_channel = await game_channel.clone(reason="New Game")
    #            await new_channel.edit(position=game_position, name=f"text-game-{game_number}", topic="")
    #        # remove manage threads permission so future STs for the game number can't see private threads
    #        st_permissions = game_channel.overwrites[st_role]
    #        st_permissions.update(manage_threads=None)
    #        await game_channel.set_permissions(st_role, overwrite=st_permissions)
    #        for st in st_role.members:
    #            if st in game_channel.overwrites:
    #                member_permissions = game_channel.overwrites[st]
    #                member_permissions.update(manage_threads=True)
    #                await game_channel.set_permissions(st, overwrite=member_permissions)
    #            else:
    #                await game_channel.set_permissions(st, manage_threads=True)
    #        await game_channel.edit(category=archive_category, name=str(game_channel_name) + " Archived on " + str(
    #            strftime("%a, %d %b %Y %H %M %S ", gmtime())), topic="")
    #
    #        kibitz_channel = self.helper.get_kibitz_channel(game_number)
    #        await kibitz_channel.set_permissions(townsfolk_role, view_channel=False)
    #
    #       # React for completion
    #        await utility.finish_processing(ctx)

    #    else:
    #        await utility.deny_command(ctx, "You are not the current ST for game " + game_number)

    #    await self.helper.log(f"{ctx.author.mention} has run the ArchiveGame Command for Game {game_number}")


def setup(bot):
    bot.add_cog(Game(bot, utility.Helper(bot)))

from time import strftime, gmtime

import nextcord
from nextcord.ext import commands

import utility


class Users(commands.Cog):
    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper

    @commands.command()
    async def AddPlayer(self, ctx, game_number, players: commands.Greedy[nextcord.Member]):
        if not len(players):
            await utility.dm_user(ctx.author, "Usage: >AddPlayer [game number] [at least one user]")
            return

        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            player_names = []
            for player in players:
                await player.add_roles(self.helper.get_game_role(game_number))
                player_names.append(player.display_name)
            await utility.dm_user(ctx.author,
                                  "You have assigned the game role for game " + str(game_number) +
                                  " to " + ", ".join(player_names))
            await self.helper.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "AddPlayer")
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))

        await self.helper.log(
            f"{ctx.author.mention} has run the AddPlayer Command on {', '.join(players)} for game {game_number}")

    @commands.command()
    async def RemovePlayer(self, ctx, game_number, players: commands.Greedy[nextcord.Member]):
        if not len(players):
            await utility.dm_user(ctx.author, "Usage: >RemovePlayer [game number] [at least one user]")
            return

        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            game_role = self.helper.get_game_role(game_number)
            player_names = []
            for player in players:
                await player.remove_roles(game_role)
                player_names.append(player.display_name)
            await utility.dm_user(ctx.author,
                                  "You have removed the game role for game " + str(game_number) +
                                  " from " + ", ".join(player_names))
            await self.helper.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "RemovePLayer")
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))

        await self.helper.log(
            f"{ctx.author.mention} has run the RemovePlayer Command on {', '.join(players)} for game {game_number}")

    @commands.command()
    async def AddKibitz(self, ctx, game_number, kibitzers: commands.Greedy[nextcord.Member]):
        if not len(kibitzers):
            await utility.dm_user(ctx.author, "Usage: >AddKibitz [game number] [at least one user]")
            return

        kibitz_role = self.helper.get_kibitz_role(game_number)

        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            member_names = []
            for watcher in kibitzers:
                await watcher.add_roles(kibitz_role)
                member_names.append(watcher.display_name)
            await utility.dm_user(ctx.author,
                                  "You have assigned the kibitz role for game " + str(game_number) +
                                  " to " + ", ".join(member_names)
                                  )
            await self.helper.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "AddKibitz")
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))

        await self.helper.log(
            f"{ctx.author.mention} has run the AddKibitz Command on {', '.join(kibitzers)} for game {game_number}")

    @commands.command()
    async def RemoveKibitz(self, ctx, game_number, kibitzers: commands.Greedy[nextcord.Member]):
        if not len(kibitzers):
            await utility.dm_user(ctx.author, "Usage: >RemoveKibitz [game number] [at least one user]")
            return
        game_number = game_number
        kibitz_role = self.helper.get_kibitz_role(game_number)

        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            watcher_names = []
            for watcher in kibitzers:
                await watcher.remove_roles(kibitz_role)
                watcher_names.append(watcher.display_name)
            await utility.dm_user(ctx.author,
                                  "You have removed the kibitz role for game " + str(game_number) +
                                  " to " + ", ".join(watcher_names))
            await self.helper.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "RemoveKibitz")
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))
        await self.helper.log(
            f"{ctx.author.mention} has run the RemoveKibitz Command on {', '.join(kibitzers)} for game {game_number}")

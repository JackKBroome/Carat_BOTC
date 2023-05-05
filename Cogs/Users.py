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

        player_names = [p.display_name for p in players]
        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            for player in players:
                await player.add_roles(self.helper.get_game_role(game_number))
            await utility.dm_user(ctx.author,
                                  "You have assigned the game role for game " + str(game_number) +
                                  " to " + ", ".join(player_names))
            await self.helper.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "AddPlayer")
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))

        await self.helper.log(
            f"{ctx.author.mention} has run the AddPlayer Command on {', '.join(player_names)} for game {game_number}")

    @commands.command()
    async def RemovePlayer(self, ctx, game_number, players: commands.Greedy[nextcord.Member]):
        if not len(players):
            await utility.dm_user(ctx.author, "Usage: >RemovePlayer [game number] [at least one user]")
            return

        player_names = [p.display_name for p in players]
        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            game_role = self.helper.get_game_role(game_number)
            for player in players:
                await player.remove_roles(game_role)
            await utility.dm_user(ctx.author,
                                  "You have removed the game role for game " + str(game_number) +
                                  " from " + ", ".join(player_names))
            await self.helper.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "RemovePLayer")
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))

        await self.helper.log(
            f"{ctx.author.mention} has run the RemovePlayer Command on {', '.join(player_names)} for game {game_number}")

    @commands.command()
    async def AddKibitz(self, ctx, game_number, kibitzers: commands.Greedy[nextcord.Member]):
        if not len(kibitzers):
            await utility.dm_user(ctx.author, "Usage: >AddKibitz [game number] [at least one user]")
            return

        kibitz_role = self.helper.get_kibitz_role(game_number)
        kibitzer_names = [k.display_name for k in kibitzers]

        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            for watcher in kibitzers:
                await watcher.add_roles(kibitz_role)
            await utility.dm_user(ctx.author,
                                  "You have assigned the kibitz role for game " + str(game_number) +
                                  " to " + ", ".join(kibitzer_names)
                                  )
            await self.helper.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "AddKibitz")
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))

        await self.helper.log(
            f"{ctx.author.mention} has run the AddKibitz Command on {', '.join(kibitzer_names)} for game {game_number}")

    @commands.command()
    async def RemoveKibitz(self, ctx, game_number, kibitzers: commands.Greedy[nextcord.Member]):
        if not len(kibitzers):
            await utility.dm_user(ctx.author, "Usage: >RemoveKibitz [game number] [at least one user]")
            return
        game_number = game_number
        kibitz_role = self.helper.get_kibitz_role(game_number)
        kibitzer_names = [k.display_name for k in kibitzers]
        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            for watcher in kibitzers:
                await watcher.remove_roles(kibitz_role)
            await utility.dm_user(ctx.author,
                                  "You have removed the kibitz role for game " + str(game_number) +
                                  " to " + ", ".join(kibitzer_names))
            await self.helper.finish_processing(ctx)
        else:
            await utility.deny_command(ctx, "RemoveKibitz")
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))
        await self.helper.log(
            f"{ctx.author.mention} has run the RemoveKibitz Command on {', '.join(kibitzer_names)} for game {game_number}")

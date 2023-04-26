from nextcord.ext import commands


class Users(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def AddPlayer(self, ctx, GameNumber, players: commands.Greedy[nextcord.Member]):
        if not len(players):
            try:
                await ctx.author.send("Usage: >AddPlayer [game number] [at least one user]")
            except:
                print(f"Could not DM {ctx.author}")
            return
        x = GameNumber

        LogChannel, Server = await helper.get_server()

        STRole = get(Server.roles, name="st" + str(x))
        GameRole = get(Server.roles, name="game" + str(x))
        PlayerNames = []
        Access = await helper.authorize_st_command(STRole, Server, ctx.author)
        if Access:
            # React on Approval
            await utility.start_processing(ctx)
            for player in players:
                await player.add_roles(GameRole)
                PlayerNames.append(player.display_name)
            try:
                await ctx.author.send(
                    "You have assigned the game role for game " + str(x) + " to " + ", ".join(PlayerNames))
            except:
                print(f"Could not DM {ctx.author}")
            await self.helper.finish_processing(ctx)
        else:
            print("-= The AddPlayer command was stopped against " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
            await ctx.message.add_reaction(DeniedEmoji)
            try:
                await ctx.author.send("You are not the current ST for game " + str(x))
            except:
                print(f"Could not DM {ctx.author}")

        await self.helper.log(
            f"{ctx.author.mention} has run the AddPlayer Command on {', '.join(PlayerNames)} for game {x}")

    @commands.command()
    async def RemovePlayer(self, ctx, GameNumber, players: commands.Greedy[nextcord.Member]):
        if not len(players):
            try:
                await ctx.author.send("Usage: >RemovePlayer [game number] [at least one user]")
            except:
                print(f"Could not DM {ctx.author}")
            return
        x = GameNumber

        LogChannel, Server = await helper.get_server()
        GameRole = get(ctx.guild.roles, name="game" + str(x))

        STRole = get(Server.roles, name="st" + str(x))
        PlayerNames = []
        Access = await helper.authorize_st_command(STRole, Server, ctx.author)
        if Access:
            # React on Approval
            await utility.start_processing(ctx)
            for player in players:
                await player.remove_roles(GameRole)
                PlayerNames.append(player.display_name)
            try:
                await ctx.author.send(
                    "You have removed the game role for game " + str(x) + " from " + ", ".join(PlayerNames)
                )
            except:
                print(f"Could not DM {ctx.author}")
            await self.helper.finish_processing(ctx)
        else:
            print("-= The RemovePlayer command was stopped against " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
            await ctx.message.add_reaction(DeniedEmoji)
            try:
                await ctx.author.send("You are not the current ST for game " + str(x))
            except:
                print(f"Could not DM {ctx.author}")

        await self.helper.log(
            f"{ctx.author.mention} has run the RemovePlayer Command on {', '.join(PlayerNames)} for game {x}")

    @commands.command()
    async def AddKibitz(self, ctx, GameNumber, watchers: commands.Greedy[nextcord.Member]):
        if not len(watchers):
            try:
                await ctx.author.send("Usage: >AddKibitz [game number] [at least one user]")
            except:
                print(f"Could not DM {ctx.author}")
            return
        x = GameNumber

        LogChannel, Server = await helper.get_server()

        STRole = get(Server.roles, name="st" + str(x))
        KibitzRole = get(Server.roles, name="kibitz" + str(x))

        MemberNames = []
        Access = await helper.authorize_st_command(STRole, Server, ctx.author)
        if Access:
            # React on Approval
            await utility.start_processing(ctx)
            for watcher in watchers:
                await watcher.add_roles(KibitzRole)
                MemberNames.append(watcher.display_name)
            try:
                await ctx.author.send(
                    "You have assigned the kibitz role for game " + str(x) + " to " + ", ".join(MemberNames)
                )
            except:
                print(f"Could not DM {ctx.author}")
            await self.helper.finish_processing(ctx)
        else:
            print("-= The AddKibitz command was stopped against " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
            await ctx.message.add_reaction(DeniedEmoji)
            try:
                await ctx.author.send("You are not the current ST for game " + str(x))
            except:
                print(f"Could not DM {ctx.author}")

        await self.helper.log(
            f"{ctx.author.mention} has run the AddKibitz Command on {', '.join(MemberNames)} for game {x}")

    @commands.command()
    async def RemoveKibitz(self, ctx, GameNumber, watchers: commands.Greedy[nextcord.Member]):
        if not len(watchers):
            try:
                await ctx.author.send("Usage: >RemoveKibitz [game number] [at least one user]")
            except:
                print(f"Could not DM {ctx.author}")
            return
        x = GameNumber

        LogChannel, Server = await helper.get_server()

        STRole = get(Server.roles, name="st" + str(x))
        KibitzRole = get(Server.roles, name="kibitz" + str(x))

        Access = await helper.authorize_st_command(STRole, Server, ctx.author)
        WatcherNames = []
        if Access:
            # React on Approval
            await utility.start_processing(ctx)
            for watcher in watchers:
                await watcher.remove_roles(KibitzRole)
                WatcherNames.append(watcher.display_name)
            try:
                await ctx.author.send(
                    "You have removed the kibitz role for game " + str(x) + " to " + ", ".join(WatcherNames))
            except:
                print(f"Could not DM {ctx.author}")
            await self.helper.finish_processing(ctx)
        else:
            print("-= The RemoveKibitz command was stopped against " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
            await ctx.message.add_reaction(DeniedEmoji)
            try:
                await ctx.author.send("You are not the current ST for game " + str(x))
            except:
                print(f"Could not DM {ctx.author}")

        await self.helper.log(
            f"{ctx.author.mention} has run the RemoveKibitz Command on {', '.join(WatcherNames)} for game {x}")
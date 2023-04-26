from nextcord.ext import commands


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def OpenKibitz(self, ctx, GameNumber):
        # x is Legacy from early days, changed to help >help command easier to read, could be updated
        x = GameNumber

        LogChannel, Server = await helper.get_server()

        STRole = get(Server.roles, name="st" + str(x))
        GameRole = get(Server.roles, name="game" + str(x))
        Access = await helper.authorize_st_command(STRole, Server, ctx.author)
        if Access:
            # React on Approval
            await utility.start_processing(ctx)

            # Change permission of Kibitz to allow Townsfolk to view
            TownsfolkRole = Server.default_role
            X = str(x)
            if X[0] == "x":
                KibitzChannelName = "experimental-kibitz-" + str(X[1])
            else:
                KibitzChannelName = "kibitz-game-" + str(x)

            KibitzChannel = get(Server.channels, name=KibitzChannelName)
            await KibitzChannel.set_permissions(TownsfolkRole, view_channel=True)
            await ctx.channel.send(
                f"{GameRole.mention} Kibitz is now being opened - remove your game? role to access it. " +
                f"Remember to give your ST(s) any feedback you may have!\n" +
                f"Feedback form: https://forms.gle/HqNfMv1pte8vo5j59")

            # React for completion
            await self.helper.finish_processing(ctx)
            print("-= The Open Kibitz command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
        else:
            # React on Disapproval
            await ctx.message.add_reaction(DeniedEmoji)
            try:
                await ctx.author.send("You are not the current ST for game " + str(x))
            except:
                print(f"Could not DM {ctx.author}")
            print("-= The Open Kibitz command was stopped against " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

        await self.helper.log(f"{ctx.author.mention} has run the OpenKibitz Command on Game {x}")

    @commands.command()
    async def CloseKibitz(self, ctx, GameNumber):
        # x is Legacy from early days, changed to help >help command easier to read, could be updated
        x = GameNumber

        LogChannel, Server = await helper.get_server()

        # Check permission
        STRoleSTR = "st" + str(x)
        ST = get(Server.roles, name=STRoleSTR)
        Access = await helper.authorize_st_command(ST, Server, ctx.author)
        if Access:
            # React on Approval
            await utility.start_processing(ctx)

            # Change permission of Kibitz to allow Townsfolk to view
            TownsfolkRole = Server.default_role
            X = str(x)
            if X[0] == "x":
                KibitzChannelName = "experimental-kibitz-" + str(X[1])
            else:
                KibitzChannelName = "kibitz-game-" + str(x)

            KibitzChannel = get(Server.channels, name=KibitzChannelName)
            await KibitzChannel.set_permissions(TownsfolkRole, view_channel=False)

            # React for completion
            await self.helper.finish_processing(ctx)
            print("-= The Close Kibitz command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
        else:
            # React on Disapproval
            await ctx.message.add_reaction(DeniedEmoji)
            try:
                await ctx.author.send("You are not the current ST for game " + str(x))
            except:
                print(f"Could not DM {ctx.author}")
            print("-= The Close Kibitz command was stopped against " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

        await self.helper.log(f"{ctx.author.mention} has run the CloseKibitz Command on Game {x}")

    @commands.command()
    async def EndGame(ctx: commands.Context, GameNumber):
        # x is Legacy from early days, changed to help >help command easier to read, could be updated
        x = GameNumber

        LogChannel, Server = await helper.get_server()

        # Check Access
        STRoleSTR = "st" + str(x)
        ST = get(Server.roles, name=STRoleSTR)
        Access = await helper.authorize_st_command(ST, Server, ctx.author)
        if Access:
            # React on Approval
            await utility.start_processing(ctx)

            # Gather member list & role information
            Kibitz = "kibitz" + str(x)
            KibitzRole = get(Server.roles, name=Kibitz)
            Game = "game" + str(x)
            GameRole = get(Server.roles, name=Game)

            await ctx.channel.send(
                f"{GameRole.mention} Kibitz is now being opened: Remember to give your ST(s) any feedback you may have!\n" +
                f"Feedback form: https://forms.gle/HqNfMv1pte8vo5j59")
            members = GameRole.members
            members += KibitzRole.members

            # Remove Kibitz from non-bot players
            for member in members:
                if str(member.bot) == "False":
                    await member.remove_roles(KibitzRole)
                    await member.remove_roles(GameRole)

            # Change permission of Kibitz to allow Townsfolk to view
            TownsfolkRole = Server.default_role
            X = str(x)
            if X[0] == "x":
                KibitzChannelName = "experimental-kibitz-" + str(X[1:])
            else:
                KibitzChannelName = "kibitz-game-" + str(x)

            KibitzChannel = get(Server.channels, name=KibitzChannelName)
            await KibitzChannel.set_permissions(TownsfolkRole, view_channel=True)

            # React for completion
            await self.helper.finish_processing(ctx)
            print("-= The EndGame command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

        else:
            # React on Disapproval
            await ctx.message.add_reaction(DeniedEmoji)
            try:
                await ctx.author.send("You are not the current ST for game " + str(x))
            except:
                print(f"Could not DM {ctx.author}")
            print("-= The EndGame command was stopped against " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

        await self.helper.log(f"{ctx.author.mention} has run the EndGame Command on Game {x}")

    @commands.command()
    async def ArchiveGame(self, ctx, GameNumber):
        # x is Legacy from early days, changed to help >help command easier to read, could be updated
        x = GameNumber

        LogChannel, Server = await helper.get_server()

        # Check for permissions
        STRoleSTR = "st" + str(x)
        ST = get(Server.roles, name=STRoleSTR)
        Access = await helper.authorize_st_command(ST, Server, ctx.author)
        if Access:
            # React on Approval
            await utility.start_processing(ctx)

            TownsfolkRole = Server.default_role

            # Find Channel
            X = str(x)
            if X[0] == "x":
                GameNumber = "x" + str(X[1])
                KibitzChannelName = "experimental-kibitz-" + str(X[1])
            else:
                GameNumber = str(X[0])
                KibitzChannelName = "kibitz-game-" + str(x)

            Category = get(Server.channels, id=TextGamesCategoryID)
            for channel in Category.channels:
                if GameNumber in str(channel) and f"x{GameNumber}" not in str(channel):
                    GameChannel = channel
                    GameChannelName = str(channel)

            KibitzChannel = get(Server.channels, name=KibitzChannelName)
            Game_position = GameChannel.position

            # Create New Channel
            await GameChannel.clone(reason="New Game")

            ARCHIVEDGAMES = get(Server.channels, id=ArchiveCategoryID)
            if len(ARCHIVEDGAMES.channels) == 50:
                await ARCHIVEDGAMES.channels[49].delete()
            await GameChannel.edit(category=ARCHIVEDGAMES, name=str(GameChannelName) + " Archived on " + str(
                strftime("%a, %d %b %Y %H %M %S ", gmtime())), topic="")

            NewGameChannel = get(Server.channels, name=GameChannelName)
            await NewGameChannel.edit(position=Game_position)
            await NewGameChannel.edit(name=f"text-game-{GameNumber}")

            await KibitzChannel.set_permissions(TownsfolkRole, view_channel=False)

            # React for completion
            await self.helper.finish_processing(ctx)
            print("-= The ArchiveGame command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

        else:
            # React on Disapproval
            await ctx.message.add_reaction(DeniedEmoji)
            try:
                await ctx.author.send("You are not the current ST for game " + str(x))
            except:
                print(f"Could not DM {ctx.author}")
            print("-= The ArchiveGame command was stopped against " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

        await self.helper.log(f"{ctx.author.mention} has run the ArchiveGame Command for Game {x}")
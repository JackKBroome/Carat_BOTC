# Import a Bunch of stuff, might have redundant areas
import discord
import os
from discord.ext import commands, tasks
from discord.utils import get
from discord_components import DiscordComponents, ComponentsBot, Button, Select, SelectOption
from time import gmtime, strftime
import asyncio

intents = discord.Intents.default()
intents.presences = True
intents.members = True

BotCUGuildId = 569683781800296501
TextGamesCategoryID = 569683781846433930
DoomsayerRoleID = 569684377496190996
WorkingEmoji = '\U0001F504'
CompletedEmoji = '\U0001F955'
DeniedEmoji = '\U000026D4'

bot = ComponentsBot(command_prefix=">", intents=intents, activity=discord.Game(name=">HelpMe or >help"))


# Output in terminal when bot turns on
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


async def get_server():
    Server = bot.get_guild(BotCUGuildId)
    LogChannel = discord.utils.get(Server.channels, id=958296180251561984)
    return LogChannel, Server


async def authorize_st_command(STRole, Server, author):
    Access = 0
    Doomsayer = Server.get_role(DoomsayerRoleID)
    # Doomsayer Access
    if Doomsayer in author.roles:
        Access = 1
    # stX Access
    if STRole in author.roles:
        Access = 1
    # Jack B Access
    if str(author.id) == "107209184147185664":
        Access = 1
    return Access


@bot.command()
async def OpenKibitz(ctx, GameNumber):
    # x is Legacy from early days, changed to help >help command easier to read, could be updated
    x = GameNumber

    LogChannel, Server = await get_server()

    # Check permissions, granted the check is backwards but works
    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        # Change permission of Kibitz to allow Townsfolk to view
        TownsfolkRole = Server.default_role
        X = str(x)
        if X[0] == "x":
            KibitzChannelName = "experimental-kibitz-" + str(X[1])
        else:
            KibitzChannelName = "kibitz-game-" + str(x)

        KibitzChannel = discord.utils.get(Server.channels, name=KibitzChannelName)
        await KibitzChannel.set_permissions(TownsfolkRole, view_channel=True)

        # React for completion
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
        print("-= The Open Kibitz command was used successfully by " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    else:
        # React on Disapproval
        emoji = DeniedEmoji
        await ctx.message.add_reaction(emoji)
        print("-= The Open Kibitz command was stopped against " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    await LogChannel.send(f"{ctx.author.mention} has run the OpenKibitz Command on Game {x}")


@bot.command()
async def CloseKibitz(ctx, GameNumber):
    # x is Legacy from early days, changed to help >help command easier to read, could be updated
    x = GameNumber

    LogChannel, Server = await get_server()

    # Check permission
    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        # Change permission of Kibitz to allow Townsfolk to view
        TownsfolkRole = Server.default_role
        X = str(x)
        if X[0] == "x":
            KibitzChannelName = "experimental-kibitz-" + str(X[1])
        else:
            KibitzChannelName = "kibitz-game-" + str(x)

        KibitzChannel = discord.utils.get(Server.channels, name=KibitzChannelName)
        await KibitzChannel.set_permissions(TownsfolkRole, view_channel=False)

        # React for completion
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
        print("-= The Close Kibitz command was used successfully by " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    else:
        # React on Disapproval
        emoji = DeniedEmoji
        await ctx.message.add_reaction(emoji)
        print("-= The Close Kibitz command was stopped against " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    await LogChannel.send(f"{ctx.author.mention} has run the CloseKibitz Command on Game {x}")


@bot.command()
async def EndGame(ctx, GameNumber):
    # x is Legacy from early days, changed to help >help command easier to read, could be updated
    x = GameNumber

    LogChannel, Server = await get_server()

    # Check Access
    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        # Gather member list & role information
        Kibitz = "kibitz" + str(x)
        KibitzRole = discord.utils.get(Server.roles, name=Kibitz)
        Game = "game" + str(x)
        GameRole = discord.utils.get(Server.roles, name=Game)
        guild = bot.get_guild(780303800425906206)
        members = GameRole.members
        members = members + KibitzRole.members

        # Remove Kibitz from non-bot players
        for i in range(len(members)):
            member = members[i]
            if str(member.bot) == "False":
                await member.remove_roles(KibitzRole)
                await member.remove_roles(GameRole)

        # Change permission of Kibitz to allow Townsfolk to view
        TownsfolkRole = Server.default_role
        X = str(x)
        if X[0] == "x":
            KibitzChannelName = "experimental-kibitz-" + str(X[1])
        else:
            KibitzChannelName = "kibitz-game-" + str(x)

        KibitzChannel = discord.utils.get(Server.channels, name=KibitzChannelName)
        await KibitzChannel.set_permissions(TownsfolkRole, view_channel=True)

        # React for completion
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
        print("-= The EndGame command was used successfully by " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    else:
        # React on Disapproval
        emoji = DeniedEmoji
        await ctx.message.add_reaction(emoji)
        print("-= The EndGame command was stopped against " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    await LogChannel.send(f"{ctx.author.mention} has run the EndGame Command on Game {x}")


@bot.command()
async def ArchiveGame(ctx, GameNumber):
    # x is Legacy from early days, changed to help >help command easier to read, could be updated
    x = GameNumber

    LogChannel, Server = await get_server()

    # Check for permissions
    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        # Gather member list & role information
        TownsfolkRole = Server.default_role
        Kibitz = "kibitz" + str(x)
        KibitzRole = discord.utils.get(Server.roles, name=Kibitz)
        Game = "game" + str(x)
        GameRole = discord.utils.get(Server.roles, name=Game)
        guild = bot.get_guild(780303800425906206)

        # Command
        # Archived Games
        # Find Channel
        X = str(x)
        if X[0] == "x":
            GameNumber = "x" + str(X[1])
            KibitzChannelName = "experimental-kibitz-" + str(X[1])
        else:
            GameNumber = str(X[0])
            KibitzChannelName = "kibitz-game-" + str(x)

        Category = discord.utils.get(Server.channels, id=TextGamesCategoryID)
        for i in range(len(Category.channels)):
            if GameNumber in str(Category.channels[i]) and f"x{GameNumber}" not in str(Category.channels[i]):
                GameChannelName = str(Category.channels[i])

        GameChannel = discord.utils.get(Server.channels, name=GameChannelName)
        KibitzChannel = discord.utils.get(Server.channels, name=KibitzChannelName)
        Game_position = GameChannel.position

        # Create New Channel
        await GameChannel.clone(reason="New Game")

        ARCHIVEDGAMES = discord.utils.get(Server.channels, id=956566935657676870)
        if len(ARCHIVEDGAMES.channels) == 50:
            await ARCHIVEDGAMES.channels[49].delete()
        await GameChannel.edit(category=ARCHIVEDGAMES, name=str(GameChannelName) + " Archived on " + str(
            strftime("%a, %d %b %Y %H %M %S ", gmtime())), topic="")

        NewGameChannel = discord.utils.get(Server.channels, name=GameChannelName)
        await NewGameChannel.edit(position=Game_position)
        await NewGameChannel.edit(name=f"text-game-{GameNumber}")

        await KibitzChannel.set_permissions(TownsfolkRole, view_channel=False)

        # React for completion
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
        print("-= The New Game command was used successfully by " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    else:
        # React on Disapproval
        emoji = DeniedEmoji
        await ctx.message.add_reaction(emoji)
        print("-= The New Game command was stopped against " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    await LogChannel.send(f"{ctx.author.mention} has run the ArchiveGame Command for Game {x}")


@bot.command()
async def Signup(ctx, GameNumber, SignupLimit: int, Script: str):
    # x/y is Legacy from early days, changed to help >help command easier to read, could be updated
    x = GameNumber
    y = SignupLimit

    LogChannel, Server = await get_server()

    # Check for access
    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)
        # Gather member list & role information
        TownsfolkRole = Server.default_role
        Kibitz = "kibitz" + str(x)
        KibitzRole = discord.utils.get(Server.roles, name=Kibitz)
        Game = "game" + str(x)
        GameRole = discord.utils.get(Server.roles, name=Game)
        guild = bot.get_guild(780303800425906206)

        # Find Game & player
        X = str(x)
        if X[0] == "x":
            GameNumber = "x" + str(X[1])
            KibitzChannelName = "experimental-kibitz-" + str(X[1])
        else:
            GameNumber = str(X[0])
            KibitzChannelName = "kibitz-game-" + str(x)

        Category = discord.utils.get(Server.channels, id=TextGamesCategoryID)
        for i in range(len(Category.channels)):
            if GameNumber in str(Category.channels[i]) and f"x{GameNumber}" not in str(Category.channels[i]):
                GameChannelName = str(Category.channels[i])

        GameChannel = discord.utils.get(Server.channels, name=GameChannelName)
        KibitzChannel = discord.utils.get(Server.channels, name=KibitzChannelName)
        if ctx.author.nick == None:
            STname = ctx.author.name
        else:
            STname = ctx.author.nick

        # Post Signup Page
        embed = discord.Embed(title=str(Script), description="Ran by " + str(
            STname) + "\nPress \U0001F7E9 to sign up for the game\nPress \U0001F7E5 to remove yourself from the game "
                      "\nPress \U0001F504 if the list needs updating (if a command is used to assign roles)",
                              color=0xff0000)
        for i in range(y):
            if (len(GameRole.members)) >= (i + 1):
                if GameRole.members[i].nick == None:
                    name = GameRole.members[i].name
                else:
                    name = GameRole.members[i].nick
                embed.add_field(name=str(i + 1) + ". " + str(name), value="has Signed Up", inline=False)
            else:
                embed.add_field(name=str(i + 1) + ". ", value=" Awaiting Player", inline=False)
        embed.set_footer(text=X)
        await GameChannel.send(
            embed=embed,
            components=[
                [
                    Button(label="Sign Up", custom_id="Sign_Up_Command", style=3),
                    Button(label="Leave Game", custom_id="Leave_Game_Command", style=4),
                    Button(label="Refresh List", custom_id="Refresh_Command", style=2)
                ]
            ]
        )

        # React for completion
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
        print("-= The SignUp command was used successfully by " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    else:
        emoji = DeniedEmoji
        await ctx.message.add_reaction(emoji)
        print("-= The SignUp command was stopped against " + str(ctx.author.name) + " at " + str(
            strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

    await LogChannel.send(f"{ctx.author.mention} has run the Signups Command  for game {x}")


@bot.event
async def on_button_click(interaction):
    # Signup Button
    # Find which game the sign-up page relates to
    Message = await interaction.send(content=f"{interaction.custom_id} has been selected!", ephemeral=True)
    guild = bot.get_guild(BotCUGuildId)
    SignupMessage = interaction.message
    NumberofFields = SignupMessage.embeds[0].to_dict()

    LogChannel, Server = await get_server()

    x = NumberofFields["footer"]
    x = str(x["text"])

    Game = "game" + str(x)
    GameRole = discord.utils.get(guild.roles, name=Game)
    Kibitz = "kibitz" + str(x)
    KibitzRole = discord.utils.get(guild.roles, name=Kibitz)
    st = "st" + str(x)
    STRole = discord.utils.get(guild.roles, name=st)
    STPlayers = STRole.members

    y = len(NumberofFields["fields"])
    z = len(GameRole.members)

    # Find the connected Game
    X = str(x)
    if X[0] == "x":
        GameChannelName = "experimental-game-" + str(X[1])
    else:
        GameChannelName = "text-only-game-" + str(X)

    # Sign up command
    if str(interaction.custom_id) == "Sign_Up_Command":
        if GameRole in interaction.user.roles:
            await interaction.user.send("You are already signed up")
        elif interaction.user.bot == True:
            a = 1
        elif z >= y:
            await interaction.user.send("The game is currently full, please contact the Storyteller")
        else:
            await interaction.user.add_roles(GameRole)
            await interaction.user.remove_roles(KibitzRole)
            for i in range(len(STPlayers)):
                await STPlayers[i].send(
                    f"{interaction.user.display_name} ({ctx.author.name}) has signed up for Game {X}")
            await LogChannel.send(f"{interaction.user.display_name} ({ctx.author.name}) has signed up for Game {X}")

    # Leave Game command
    if str(interaction.custom_id) == "Leave_Game_Command":
        if GameRole not in interaction.user.roles:
            await interaction.user.send("You haven't signed up")
        elif interaction.user.bot == True:
            a = 1
        else:
            await interaction.user.remove_roles(GameRole)
            for i in range(len(STPlayers)):
                await STPlayers[i].send(
                    f"{interaction.user.display_name} ({ctx.author.name}) has removed themself from Game {X}")
            await LogChannel.send(
                f"{interaction.user.display_name} ({ctx.author.name}) has removed themself from Game {X}")

    # Update Message
    y = len(NumberofFields["fields"])
    RanBy = str(NumberofFields["description"])
    Script = str(NumberofFields["title"])
    embed = discord.Embed(title=Script, description=RanBy, color=0xff0000)
    SortedPlayerList = GameRole.members
    for i in range(y):
        if (len(SortedPlayerList)) >= (i + 1):
            name = SortedPlayerList[i].display_name
            embed.add_field(name=str(i + 1) + ". " + str(name), value=f"{SortedPlayerList[i].mention} has signed up",
                            inline=False)
        else:
            embed.add_field(name=str(i + 1) + ". ", value=" Awaiting Player", inline=False)
    embed.set_footer(text=X)
    await SignupMessage.edit(embed=embed)


@bot.command()
async def ClaimGrimoire(ctx, GameNumber):
    # x is Legacy from early days, changed to help >help command easier to read, could be updated
    x = GameNumber

    LogChannel, Server = await get_server()

    # Check access (Given to everyone so could remove this section entirely, certainly the logic here is not optimal going back & forth
    Access = 1
    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    CurrentST = ST.members
    Doomsayer = Server.get_role(DoomsayerRoleID)

    if Doomsayer in ctx.author.roles:
        Access = 1
    # stX Access
    if len(ST.members) != 0:
        Access = 0
    # Doomsayer Access
    if Doomsayer in ctx.author.roles:
        Access = 1
    # Jack B Access
    if str(ctx.author.id) == "107209184147185664":
        Access = 1
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        await ctx.author.add_roles(ST)
        try:
            await ctx.message.author.send("You are now the current ST for game " + str(x))
        except:
            print("Error")
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
    else:
        try:
            await ctx.message.author.send("This channel already has " + str(len(CurrentST)) + " STs. These users are: ")
        except:
            print("Error")
        for i in range(len(CurrentST)):
            await ctx.message.author.send(str(CurrentST[i].display_name))

    await LogChannel.send(f"{ctx.author.mention} has run the ClaimGrimoire Command  for game {x}")


@bot.command()
async def GiveGrimoire(ctx, GameNumber, member: discord.Member):
    # x is Legacy from early days, changed to help >help command easier to read, could be updated
    x = GameNumber

    LogChannel, Server = await get_server()

    # Check for access
    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        await member.add_roles(ST)
        await ctx.message.author.remove_roles(ST)
        MemberName = member.display_name
        try:
            await ctx.message.author.send(
                "You have assigned the current ST role for game " + str(x) + " to " + str(MemberName))
        except:
            print("Error")
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
    else:
        try:
            await ctx.message.author.send("You are not the current ST for game " + str(x))
        except:
            print("Error")

    await LogChannel.send(
        f"{ctx.author.mention} has run the GiveGrimoire Command on {member.display_name} for game {x}")


@bot.command()
async def DropGrimoire(ctx, GameNumber):
    # x is Legacy from early days, changed to help >help command easier to read, could be updated
    x = GameNumber

    LogChannel, Server = await get_server()

    # Check for access
    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        await ctx.message.author.remove_roles(ST)
        try:
            await ctx.message.author.send("You have removed the current ST role from yourself for game " + str(x))
        except:
            print("Error")
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
    else:
        try:
            await ctx.message.author.send("You are not the current ST for game " + str(x))
        except:
            print("Error")

    await LogChannel.send(f"{ctx.author.mention} has run the DropGrimoire Command for game {x}")


@bot.command()
async def ShareGrimoire(ctx, GameNumber, member: discord.Member):
    # x is Legacy from early days, changed to help >help command easier to read, could be updated
    x = GameNumber

    LogChannel, Server = await get_server()

    # Check for access
    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        await member.add_roles(ST)
        MemberName = member.display_name
        try:
            await ctx.message.author.send(
                "You have assigned the current ST for game " + str(x) + " to " + str(MemberName))
        except:
            print("Error")
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
    else:
        try:
            await ctx.message.author.send("You are not the current ST for game " + str(x))
        except:
            print("Error")

    await LogChannel.send(
        f"{ctx.author.mention} has run the ShareGrimoire Command on {member.display_name} for game {x}")


@bot.command()
async def FindGrimoire(ctx):
    LogChannel, Server = await get_server()

    # Entire logic of this could be changed to numerate from 1 up until an error then x1 up until error, didn't think about that
    GameList = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8"]
    for j in GameList:
        STRoleSTR = "st" + str(j)
        ST = discord.utils.get(Server.roles, name=STRoleSTR)
        CurrentST = ST.members
        if CurrentST == []:
            try:
                # Would be better to concatenate a single message to stop the rate limit, also to send all elements of "CurrentST"
                await ctx.message.author.send("There is currently no assigned ST for game " + str(j))
            except:
                print("Error")
        else:
            try:
                await ctx.message.author.send("Game " + str(j) + "'s ST is: " + str(CurrentST[0]))
            except:
                print("Error")
    await LogChannel.send(f"{ctx.author.mention} has run the FindGrimoire Command")


@bot.command()
async def ShowSignUps(ctx, GameNumber):
    LogChannel, Server = await get_server()

    x = GameNumber

    GameRoleSTR = "game" + str(x)
    GameRole = discord.utils.get(Server.roles, name=GameRoleSTR)
    GamePlayers = GameRole.members
    KibitzSTR = "kibitz" + str(x)
    KibitzRole = discord.utils.get(Server.roles, name=KibitzSTR)
    Kibitzers = KibitzRole.members
    STSTR = "st" + str(x)
    STRole = discord.utils.get(Server.roles, name=STSTR)
    ST = STRole.members

    OutputString = f"Game {x} Players\nStoryteller:\n"

    for i in range(len(ST)):
        OutputString = OutputString + ST[i].display_name + "\n"

    OutputString = OutputString + "\nPlayers:\n"

    for i in range(len(GamePlayers)):
        OutputString = OutputString + GamePlayers[i].display_name + "\n"

    OutputString = OutputString + "\nKibitz members:\n"

    for i in range(len(Kibitzers)):
        OutputString = OutputString + Kibitzers[i].display_name + "\n"

    try:
        await ctx.author.send(OutputString)
    except:
        print("Error")
    await LogChannel.send(f"{ctx.author.mention} has run the ShowSignUps Command")


@bot.command()
async def AddPlayer(ctx, GameNumber, member: discord.Member):
    x = GameNumber

    LogChannel, Server = await get_server()

    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    GameRoleSTR = "game" + str(x)
    GameRole = discord.utils.get(Server.roles, name=GameRoleSTR)
    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        await member.add_roles(GameRole)
        MemberName = member.display_name
        try:
            await ctx.message.author.send(
                "You have assigned the game role for game " + str(x) + " to " + str(MemberName))
        except:
            print("Error")
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
    else:
        try:
            await ctx.message.author.send("You are not the current ST for game " + str(x))
        except:
            print("Error")

    await LogChannel.send(f"{ctx.author.mention} has run the AddPlayer Command on {member.display_name} for game {x}")


@bot.command()
async def RemovePlayer(ctx, GameNumber, member: discord.Member):
    x = GameNumber

    LogChannel, Server = await get_server()

    GameRoleSTR = "game" + str(x)
    GameRole = discord.utils.get(ctx.guild.roles, name=GameRoleSTR)

    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        await member.remove_roles(GameRole)
        MemberName = member.display_name
        try:
            await ctx.message.author.send(
                "You have removed the game role for game " + str(x) + " to " + str(MemberName))
        except:
            print("Error")
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
    else:
        try:
            await ctx.message.author.send("You are not the current ST for game " + str(x))
        except:
            print("Error")

    await LogChannel.send(
        f"{ctx.author.mention} has run the RemovePlayer Command on {member.display_name} for game {x}")


@bot.command()
async def AddKibitz(ctx, GameNumber, member: discord.Member):
    x = GameNumber

    LogChannel, Server = await get_server()

    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    GameRoleSTR = "kibitz" + str(x)
    GameRole = discord.utils.get(Server.roles, name=GameRoleSTR)

    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)

        await member.add_roles(GameRole)
        MemberName = member.display_name
        try:
            await ctx.message.author.send(
                "You have assigned the kibitz role for game " + str(x) + " to " + str(MemberName))
        except:
            print("Error")
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
    else:
        try:
            await ctx.message.author.send("You are not the current ST for game " + str(x))
        except:
            print("Error")

    await LogChannel.send(f"{ctx.author.mention} has run the AddKibitz Command on {member.display_name} for game {x}")


@bot.command()
async def RemoveKibitz(ctx, GameNumber, member: discord.Member):
    x = GameNumber

    LogChannel, Server = await get_server()

    STRoleSTR = "st" + str(x)
    ST = discord.utils.get(Server.roles, name=STRoleSTR)
    GameRoleSTR = "kibitz" + str(x)
    GameRole = discord.utils.get(Server.roles, name=GameRoleSTR)

    Access = await authorize_st_command(ST, Server, ctx.author)
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)
        await member.remove_roles(GameRole)
        MemberName = member.display_name
        try:
            await ctx.message.author.send(
                "You have removed the kibitz role for game " + str(x) + " to " + str(MemberName))
        except:
            print("Error")
        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)
    else:
        try:
            await ctx.message.author.send("You are not the current ST for game " + str(x))
        except:
            print("Error")

    await LogChannel.send(
        f"{ctx.author.mention} has run the RemoveKibitz Command on {member.display_name} for game {x}")


@bot.command()
async def OffServerArchive(ctx, ServerID, ArchiveChannelID):
    # Credit to Ivy for this code, mostly their code

    Server = bot.get_guild(int(ServerID))
    ArchiveChannel = discord.utils.get(Server.channels, id=int(ArchiveChannelID))

    archivedchannel = ctx.message.channel

    LogChannel, UnofficialID = await get_server()

    Access = 0

    Doomsayer = UnofficialID.get_role(DoomsayerRoleID)
    # Doomsayer Access
    if Doomsayer in ctx.author.roles:
        Access = 1
    # Jack B & Ivy Access
    if str(ctx.author.id) == "107209184147185664" or str(ctx.author.id) == "183474450237358081":
        Access = 1
    if Access == 1:
        # React on Approval
        emoji = WorkingEmoji
        await ctx.message.add_reaction(emoji)
        async for currentmessage in archivedchannel.history(limit=None, oldest_first=True):
            messagecontent = currentmessage.content
            embed = discord.Embed(description=messagecontent)
            embed.set_author(name=str(currentmessage.author) + " at " + str(currentmessage.created_at),
                             icon_url=currentmessage.author.avatar_url)
            attachmentlist = []
            for i in currentmessage.attachments:
                attachmentlist.append(await i.to_file())
            for i in currentmessage.reactions:
                userlist = []
                async for user in i.users():
                    userlist.append(str(user.name))
                reactors = ", ".join(userlist)
                if len(embed.footer) != 0:
                    embed.set_footer(text=embed.footer.text + f" {i.emoji} - {reactors}, ")
                else:
                    embed.set_footer(text=f"{i.emoji} - {reactors}, ")
            try:
                await ArchiveChannel.send(embed=embed, files=attachmentlist)
            except:
                try:
                    embed.set_footer(text=embed.footer.text + "/nError Attachment file was too large.")
                except:
                    embed.set_footer(text="Error Attachment file was too large.")
                await ArchiveChannel.send(embed=embed)

        await ctx.message.remove_reaction(emoji, bot.user)
        emoji = CompletedEmoji
        await ctx.message.add_reaction(emoji)

        await LogChannel.send(f"{ctx.author.display_name} has run the OffSiteArchive Command")
        await ctx.message.author.send(f"Your Archive for {ctx.message.channel.name} is done.")


@bot.command()
async def HelpMe(ctx):
    # Add ShowSignUps here
    embed = discord.Embed(title="Unofficial Text Game Bot",
                          description="A List of commands for both Storytellers & Moderators", color=0xe100ff)
    embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")

    embed.add_field(name=">OpenKibitz [game number] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the brackets with your game number, for example #text-only-game-1 would be ">OpenKibitz 1" & #experimental-game-2 would be ">Openkibitz x2". This command will change the viewing permission of the associated kibitz channel to be viewed by all players',
                    inline=False)
    embed.add_field(name=">CloseKibitz [game number] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the brackets with your game number, for example #text-only-game-1 would be ">CloseKibitz 1" & #experimental-game-2 would be ">Closekibitz x2". This command will change the viewing permission of the associated kibitz channel to be viewed by only players with the KibitzX role',
                    inline=False)
    embed.add_field(name=">ArchiveGame [game number] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the brackets with your game number, for example #text-only-game-1 would be ">ArchiveGame 1" & #experimental-game-2 would be ">ArchiveGame x2". This command is to signal the start of a new game, it will archive the previous game channel & create a new & cleared channel to run a new game in. It will also change the viewing permission of the associated kibitz to only be viewed by "Kibitz?" role.',
                    inline=False)
    embed.add_field(name=">EndGame [game number] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the brackets with your game number, for example #text-only-game-1 would be ">NewGame 1" & #experimental-game-2 would be "!NewGame x2". This command is to signal the end of a text game. This command will remove "GameX" & "KibitzX" role from each player who had it, along with changing the viewing permissions of the Kibitz channel to allow the All Discord Users role to view it.',
                    inline=False)
    embed.add_field(name=">Signup [game number] [Player Count] [Script Name] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the first brackets with your game number, the second with the number of players allowed in the game & finally the name of the script (Please note: If the script name is multiple words eg. Trouble Brewing, it will require speech marks around the script name eg "Trouble Brewing"), for example #text-only-game-1 would be ">Signup 1 10 BMR" & #experimental-game-2 would be >!Signup x2 9 Catfishing". This command is used to automate the signup board, it will post an embedded message in the correct channel that players can react to sign up to & react to remove themselves from the game. This updates in almost real time & requires no intervention from the storyteller. When a player is signed up their name will appear in the signup list & they will be assigned the "game?" role automatically.',
                    inline=False)

    embed.add_field(name=">FindGrimoire", value="Sends the user a DM showing which games currently do not have an ST.",
                    inline=False)
    embed.add_field(name=">ClaimGrimoire [game number]",
                    value='This will assign you the "st?" role for the denoted game number, providing there is not currently a player with the "st?" role.',
                    inline=False)
    embed.add_field(name=">GiveGrimoire [game number] [@Player]",
                    value='This will remove the "st?" role from you for the denoted game number & assign the "st?" role to the tagged player.',
                    inline=False)
    embed.add_field(name=">DropGrimoire [game number]",
                    value='This will remove the "st?" role from you for the denoted game number', inline=False)
    embed.add_field(name=">ShareGrimoire [game number] [@Player]",
                    value='This will assign the "st?" role to the tagged player for the denoted game number, this will allow multiple people to co-ST a game.',
                    inline=False)

    embed.add_field(name=">AddPlayer [game number] [@Player]",
                    value='To run this command it requires that you have the "st?" role. It will give the "game?" role to the tagged player for the denoted game number.',
                    inline=False)
    embed.add_field(name=">RemovePlayer [game number] [@Player]",
                    value='To run this command it requires that you have the "st?" role. It will remove the "game?" role from the tagged player for the denoted game number.',
                    inline=False)
    embed.add_field(name=">AddKibitz [game number] [@Player]",
                    value='To run this command it requires that you have the "st?" role. It will give the "kibitz?" role to the tagged player for the denoted game number.',
                    inline=False)
    embed.add_field(name=">RemoveKibitz [game number] [@Player]",
                    value='To run this command it requires that you have the "st?" role. It will remove the "kibitz?" role from the tagged player for the denoted game number.',
                    inline=False)

    embed.add_field(name=">HelpMe",
                    value="Sends a direct message of this to the player who typed the command",
                    inline=False)
    embed.set_footer(
        text="Note: If you believe that there is an error with the bot, please let Jack or a moderator know in order to resolve it. Thank You!")
    await ctx.message.author.send(embed=embed)


bot.run(token)

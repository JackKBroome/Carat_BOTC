import nextcord
from nextcord.ext import commands


class Signup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(SignupView())  # so it knows to listen for buttons on pre-existing signup forms


    async def update_signup_sheet(SignupMessage):
        guild = bot.get_guild(BotCUGuildId)
        NumberofFields = SignupMessage.embeds[0].to_dict()

        x = NumberofFields["footer"]
        x = str(x["text"])
        Game = "game" + x
        GameRole = get(guild.roles, name=Game)
        # Update Message
        y = len(NumberofFields["fields"])
        RanBy = str(NumberofFields["description"])
        Script = str(NumberofFields["title"])
        embed = nextcord.Embed(title=Script, description=RanBy, color=0xff0000)
        SortedPlayerList = GameRole.members
        for i in range(y):
            if (len(SortedPlayerList)) >= (i + 1):
                name = SortedPlayerList[i].display_name
                embed.add_field(name=str(i + 1) + ". " + str(name),
                                value=f"{SortedPlayerList[i].mention} has signed up",
                                inline=False)
            else:
                embed.add_field(name=str(i + 1) + ". ", value=" Awaiting Player", inline=False)
        embed.set_footer(text=x)
        await SignupMessage.edit(embed=embed)

    @commands.command()
    async def Signup(self, ctx, GameNumber, SignupLimit: int, Script: str):
        # x/y is Legacy from early days, changed to help >help command easier to read, could be updated
        x = GameNumber
        y = SignupLimit

        LogChannel, Server = await helper.get_server()

        # Check for access
        STRoleSTR = "st" + str(x)
        ST = get(Server.roles, name=STRoleSTR)
        Access = await helper.authorize_st_command(ST, Server, ctx.author)
        if Access:
            # React on Approval
            await utility.start_processing(ctx)
            # Gather member list & role information
            Game = "game" + str(x)
            GameRole = get(Server.roles, name=Game)

            # Find Game & player
            X = str(x)
            if X[0] == "x":
                GameNumber = "x" + str(X[1])
            else:
                GameNumber = str(X[0])

            Category = get(Server.channels, id=TextGamesCategoryID)
            for channel in Category.channels:
                if GameNumber in str(channel) and f"x{GameNumber}" not in str(channel):
                    GameChannelName = str(channel)

            GameChannel = get(Server.channels, name=GameChannelName)
            STname = ctx.author.display_name

            # Post Signup Page
            embed = nextcord.Embed(title=str(Script), description="Ran by " + str(
                STname) + "\nPress \U0001F7E9 to sign up for the game\nPress \U0001F7E5 to remove yourself from the game "
                          "\nPress \U0001F504 if the list needs updating (if a command is used to assign roles)",
                                   color=0xff0000)
            for i in range(y):
                if (len(GameRole.members)) >= (i + 1):
                    name = GameRole.members[i].display_name
                    embed.add_field(name=str(i + 1) + ". " + str(name), value="has Signed Up", inline=False)
                else:
                    embed.add_field(name=str(i + 1) + ". ", value=" Awaiting Player", inline=False)
            embed.set_footer(text=X)
            await GameChannel.send(
                embed=embed,
                view=SignupView()
            )

            # React for completion
            await self.helper.finish_processing(ctx)
            print("-= The SignUp command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

        else:
            await ctx.message.add_reaction(DeniedEmoji)
            try:
                await ctx.author.send("You are not the current ST for game " + str(x))
            except:
                print(f"Could not DM {ctx.author}")
            print("-= The SignUp command was stopped against " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))

        await self.helper.log(f"{ctx.author.mention} has run the Signups Command  for game {x}")


class SignupView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # for persistence

    @nextcord.ui.button(label="Sign Up", custom_id="Sign_Up_Command", style=nextcord.ButtonStyle.green)
    async def signup_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Find which game the sign-up page relates to
        await interaction.response.send_message(content=f"{button.custom_id} has been selected!",
                                                ephemeral=True)
        guild = bot.get_guild(BotCUGuildId)
        SignupMessage = interaction.message
        NumberofFields = SignupMessage.embeds[0].to_dict()

        LogChannel, Server = await helper.get_server()

        x = NumberofFields["footer"]
        x = str(x["text"])

        Game = "game" + str(x)
        GameRole = get(guild.roles, name=Game)
        Kibitz = "kibitz" + str(x)
        KibitzRole = get(guild.roles, name=Kibitz)
        st = "st" + str(x)
        STRole = get(guild.roles, name=st)
        STPlayers = STRole.members

        y = len(NumberofFields["fields"])
        z = len(GameRole.members)

        # Sign up command
        if GameRole in interaction.user.roles:
            await interaction.user.send("You are already signed up")
        elif STRole in interaction.user.roles:
            await interaction.user.send("You are the Storyteller for this game and so cannot sign up for it")
        elif interaction.user.bot:
            pass
        elif z >= y:
            await interaction.user.send("The game is currently full, please contact the Storyteller")
        else:
            await interaction.user.add_roles(GameRole)
            await interaction.user.remove_roles(KibitzRole)
            await update_signup_sheet(interaction.message)
            for st in STPlayers:
                await st.send(
                    f"{interaction.user.display_name} ({interaction.user.name}) has signed up for Game {x}")
            await self.helper.log(
                f"{interaction.user.display_name} ({interaction.user.name}) has signed up for Game {x}")

    @nextcord.ui.button(label="Leave Game", custom_id="Leave_Game_Command", style=nextcord.ButtonStyle.red)
    async def leave_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Find which game the sign-up page relates to
        await interaction.response.send_message(content=f"{button.custom_id} has been selected!",
                                                ephemeral=True)
        guild = bot.get_guild(BotCUGuildId)
        SignupMessage = interaction.message
        NumberofFields = SignupMessage.embeds[0].to_dict()

        LogChannel, Server = await helper.get_server()

        x = NumberofFields["footer"]
        x = str(x["text"])

        Game = "game" + str(x)
        GameRole = get(guild.roles, name=Game)
        st = "st" + str(x)
        STRole = get(guild.roles, name=st)
        STPlayers = STRole.members

        # Find the connected Game
        if GameRole not in interaction.user.roles:
            await interaction.user.send("You haven't signed up")
        elif interaction.user.bot:
            pass
        else:
            await interaction.user.remove_roles(GameRole)
            await update_signup_sheet(interaction.message)
            for st in STPlayers:
                await st.send(
                    f"{interaction.user.display_name} ({interaction.user.name}) has removed themself from Game {x}")
            await self.helper.log(
                f"{interaction.user.display_name} ({interaction.user.name}) has removed themself from Game {x}")

    @nextcord.ui.button(label="Refresh List", custom_id="Refresh_Command", style=nextcord.ButtonStyle.gray)
    async def refresh_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(content=f"{button.custom_id} has been selected!",
                                                ephemeral=True)
        await update_signup_sheet(interaction.message)
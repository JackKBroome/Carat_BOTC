import nextcord
from nextcord.ext import commands

import utility


class Signup(commands.Cog):
    def __init__(self, bot: commands.Bot, helper: utility.Helper):
        self.bot = bot
        self.bot.add_view(SignupView(helper))  # so it knows to listen for buttons on pre-existing signup forms
        self.helper = helper

    @commands.command()
    async def ShowSignUps(self, ctx: commands.Context, game_number: str):
        """Sends a DM listing the STs, players, and kibitz members of the game."""
        await utility.start_processing(ctx)
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
        await self.helper.finish_processing(ctx)

    @commands.command()
    async def Signup(self, ctx: commands.Context, game_number: str, signup_limit: int, script: str):
        """Posts a message listing the signed up players in the appropriate game channel, with buttons that players can use to sign up or leave the game.
        If players are added or removed in other ways, may need to be updated explicitly with the appropriate button to
         reflect those changes. Note that if a parameter contains spaces, you have to surround it with quotes."""
        if self.helper.authorize_st_command(ctx.author, game_number):
            # React on Approval
            await utility.start_processing(ctx)
            st_names = [st.display_name for st in self.helper.get_st_role(game_number).members]
            # Post Signup Page
            player_list = self.helper.get_game_role(game_number).members
            embed = nextcord.Embed(title=str(script),
                                   description="Ran by " + " ".join(st_names) +
                                               "\nPress \U0001F7E9 to sign up for the game"
                                               "\nPress \U0001F7E5 to remove yourself from the game"
                                               "\nPress \U0001F504 if the list needs updating (if a command is used to assign roles)",
                                   color=0xff0000)
            for i in range(signup_limit):
                if i < len(player_list):
                    name = player_list[i].display_name
                    embed.add_field(name=str(i + 1) + ". " + str(name),
                                    value=f"{player_list[i].mention} has signed up",
                                    inline=False)
                else:
                    embed.add_field(name=str(i + 1) + ". ", value=" Awaiting Player", inline=False)
            embed.set_footer(text=game_number)
            await self.helper.get_game_channel(game_number).send(embed=embed, view=SignupView(self.helper))

            # React for completion
            await self.helper.finish_processing(ctx)

        else:
            await utility.deny_command(ctx)
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))

        await self.helper.log(f"{ctx.author.mention} has run the Signups Command  for game {game_number}")


class SignupView(nextcord.ui.View):
    def __init__(self, helper: utility.Helper):
        super().__init__(timeout=None)  # for persistence
        self.helper = helper

    @nextcord.ui.button(label="Sign Up", custom_id="Sign_Up_Command", style=nextcord.ButtonStyle.green)
    async def signup_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Find which game the sign-up page relates to
        await interaction.response.send_message(content=f"{button.custom_id} has been selected!",
                                                ephemeral=True)
        signup_message = interaction.message
        number_of_fields = signup_message.embeds[0].to_dict()

        game_number = str(number_of_fields["footer"]["text"])
        game_role = self.helper.get_game_role(game_number)
        st_role = self.helper.get_st_role(game_number)
        kibitz_role = self.helper.get_kibitz_role(game_number)

        signup_limit = len(number_of_fields["fields"])

        z = len(game_role.members)

        # Sign up command
        if game_role in interaction.user.roles:
            await utility.dm_user(interaction.user, "You are already signed up")
        elif st_role in interaction.user.roles:
            await utility.dm_user(interaction.user,
                                  "You are the Storyteller for this game and so cannot sign up for it")
        elif interaction.user.bot:
            pass
        elif z >= signup_limit:
            await utility.dm_user(interaction.user, "The game is currently full, please contact the Storyteller")
        else:
            await interaction.user.add_roles(game_role)
            await interaction.user.remove_roles(kibitz_role)
            await self.update_signup_sheet(interaction.message)
            for st in st_role.members:
                await utility.dm_user(st,
                                      f"{interaction.user.display_name} ({interaction.user.name}) has signed up for Game {game_number}")
            await self.helper.log(
                f"{interaction.user.display_name} ({interaction.user.name}) has signed up for Game {game_number}")

    @nextcord.ui.button(label="Leave Game", custom_id="Leave_Game_Command", style=nextcord.ButtonStyle.red)
    async def leave_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Find which game the sign-up page relates to
        await interaction.response.send_message(content=f"{button.custom_id} has been selected!",
                                                ephemeral=True)
        signup_message = interaction.message
        number_of_fields = signup_message.embeds[0].to_dict()
        game_number = str(number_of_fields["footer"]["text"])

        game_role = self.helper.get_game_role(game_number)
        st_role = self.helper.get_st_role(game_number)

        # Find the connected Game
        if game_role not in interaction.user.roles:
            await utility.dm_user(interaction.user, "You haven't signed up")
        elif interaction.user.bot:
            pass
        else:
            await interaction.user.remove_roles(game_role)
            await self.update_signup_sheet(interaction.message)
            for st in st_role.members:
                await utility.dm_user(st,
                                      f"{interaction.user.display_name} ({interaction.user.name}) has removed themself from Game {game_number}")
            await self.helper.log(
                f"{interaction.user.display_name} ({interaction.user.name}) has removed themself from Game {game_number}")

    @nextcord.ui.button(label="Refresh List", custom_id="Refresh_Command", style=nextcord.ButtonStyle.gray)
    async def refresh_callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(content=f"{button.custom_id} has been selected!",
                                                ephemeral=True)
        await self.update_signup_sheet(interaction.message)

    async def update_signup_sheet(self, signup_message: nextcord.Message):
        number_of_fields = signup_message.embeds[0].to_dict()

        game_number = str(number_of_fields["footer"]["text"])
        # Update Message
        signup_limit = len(number_of_fields["fields"])
        ran_by = str(number_of_fields["description"])
        script = str(number_of_fields["title"])
        embed = nextcord.Embed(title=script, description=ran_by, color=0xff0000)
        player_list = self.helper.get_game_role(game_number).members
        for i in range(signup_limit):
            if i < len(player_list):
                name = player_list[i].display_name
                embed.add_field(name=str(i + 1) + ". " + str(name),
                                value=f"{player_list[i].mention} has signed up",
                                inline=False)
            else:
                embed.add_field(name=str(i + 1) + ". ", value=" Awaiting Player", inline=False)
        embed.set_footer(text=game_number)
        await signup_message.edit(embed=embed)

import typing
from time import strftime, gmtime

import nextcord
from nextcord import InvalidArgument
from nextcord.ext import commands
from nextcord.utils import get

import utility

ivy_id = 183474450237358081


class Other(commands.Cog):

    def __init__(self, bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper

    @commands.command()
    async def ShowSignUps(self, ctx: commands.Context, game_number: str):
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
        await self.helper.log(f"{ctx.author.mention} has run the ShowSignUps Command")

    @commands.command()
    async def OffServerArchive(self, ctx, archive_server_id: int, archive_channel_id: int):
        # Credit to Ivy for this code, mostly their code

        archive_server = self.helper.bot.get_guild(archive_server_id)
        archive_channel = get(archive_server.channels, id=archive_channel_id)

        channel_to_archive = ctx.message.channel

        access = self.helper.authorize_mod_command(ctx.author)
        # Ivy Access
        if access or ctx.author.id == ivy_id:
            # React on Approval
            await utility.start_processing(ctx)

            async for current_message in channel_to_archive.history(limit=None, oldest_first=True):
                message_content = current_message.content
                embed = nextcord.Embed(description=message_content)
                embed.set_author(name=str(current_message.author) + " at " + str(current_message.created_at),
                                 icon_url=current_message.author.display_avatar.url)
                attachment_list = []
                for i in current_message.attachments:
                    attachment_list.append(await i.to_file())
                for i in current_message.reactions:
                    user_list = []
                    async for user in i.users():
                        user_list.append(str(user.name))
                    reactors = ", ".join(user_list)
                    if not embed.footer.text or len(embed.footer.text) == 0:
                        embed.set_footer(text=f"{i.emoji} - {reactors}, ")
                    else:
                        embed.set_footer(text=embed.footer.text + f" {i.emoji} - {reactors}, ")
                try:
                    await archive_channel.send(embed=embed, files=attachment_list)
                except InvalidArgument:
                    embed.set_footer(text=embed.footer.text + "\nError: Attachment file was too large.")
                    await archive_channel.send(embed=embed)
            await archive_channel.create_thread(name="Chat about the game", type=nextcord.ChannelType.public_thread)
            await self.helper.finish_processing(ctx)

            await self.helper.log(f"{ctx.author.display_name} has run the OffServerArchive Command")
            await utility.dm_user(ctx.author, f"Your Archive for {ctx.message.channel.name} is done.")
        else:
            await utility.deny_command(ctx, "OffServerArchive")
            await utility.dm_user(ctx.author, "You do not have permission to use this command")

    @commands.command()
    async def CreateThreads(self, ctx, game_number):
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)

            for player in self.helper.get_game_role(game_number).members:
                thread = await self.helper.get_game_channel(game_number).create_thread(
                    name=f"ST Thread {player.display_name}",
                    auto_archive_duration=4320,  # 3 days
                    type=nextcord.ChannelType.private_thread,
                    reason=f"Preparing text game {game_number}"
                )
                thread.invitable = False

                await thread.add_user(player)
                for st in self.helper.get_st_role(game_number).members:
                    await thread.add_user(st)

            await self.helper.finish_processing(ctx)

            print("-= The CreateThreads command was used successfully by " + str(ctx.author.name) + " at " + str(
                strftime("%a, %d %b %Y %H:%M:%S ", gmtime()) + "=-"))
        else:
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))
            await utility.deny_command(ctx, "CreateThreads")

        await self.helper.log(f"{ctx.author.mention} has run the CreateThreads Command on Game {game_number}")

    # Future task: shorten this, add information for the >help command for each command. Nextcord has built-ins for these things, I'm pretty sure
    @commands.command()
    async def HelpMe(self, ctx: commands.Context, command_type: typing.Optional[str] = "no-mod"):
        await utility.start_processing(ctx)
        anyone_embed = nextcord.Embed(title="Unofficial Text Game Bot",
                                      description="Commands that can be executed by anyone", color=0xe100ff)
        anyone_embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")

        anyone_embed.add_field(name=">FindGrimoire",
                               value="Sends the user a DM listing all games and whether they currently have an ST.",
                               inline=False)
        anyone_embed.add_field(name=">ShowSignups [game_number]",
                               value="Sends the user a DM listing the STs, players, and kibitz members of the game\n"
                                     "Usage examples: >ShowSignups 1, >ShowSignups x3",
                               inline=False)
        anyone_embed.add_field(name=">ClaimGrimoire [game number]",
                               value='Grants you the ST role of the given game, unless it is already occupied\n' +
                                     'Usage examples: `>ClaimGrimoire 1`, `>ClaimGrimoire x3`',
                               inline=False)
        anyone_embed.add_field(name=">JoinTextQueue [channel type] [script name] [availability] [notes (optional)]",
                               value="Adds you to the queue for the given channel type (regular/experimental), "
                                     "listing the provided information, unless you are already in either of the "
                                     "queues. Do not join a queue if you are currently storytelling. Note that if a "
                                     "parameter contains spaces, you have to surround it with quotes.\n" +
                                     'Usage examples: `>JoinTextQueue regular "Trouble Brewing" "anytime after june"`, '
                                     '`>JoinTextQueue Exp "Oops All Amnesiacs" "in July, between the 13th and 30th" '
                                     '"Let me know beforehand if you\'re interested"`',
                               inline=False)
        anyone_embed.add_field(name=">LeaveTextQueue",
                               value="Removes you from the queue you are in currently - careful, you won't be able to "
                                     "regain your spot.",
                               inline=False)
        anyone_embed.add_field(name=">MoveDown [number]",
                               value="Moves you down that number of spaces in your queue - use if you can't run the "
                                     "game yet but don't want to be pinged every time a channel becomes free. Careful "
                                     "- you cannot move yourself back up, though you can ask a mod to fix things if "
                                     "you make a mistake",
                               inline=False)
        anyone_embed.add_field(name=">HelpMe",
                               value="Sends this message. Can be filtered by appending one of `all, anyone, st, mod, "
                                     "no-mod`. Default is `no-mod`\n"
                                     "Usage example: `>HelpMe all`",
                               inline=False)
        anyone_embed.set_footer(text="1/4")

        st_embed = nextcord.Embed(title="Unofficial Text Game Bot",
                                  description="Commands that can be executed by the ST of the relevant game - mods "
                                              "can ignore this restriction",
                                  color=0xe100ff)
        st_embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")
        st_embed.add_field(name=">OpenKibitz [game number]",
                           value='Makes the kibitz channel to the game visible to the public. Players will still need '
                                 'to remove their game role to see it. Use after the game has concluded. Will also '
                                 'send a message reminding players to give feedback for the ST and provide a link to '
                                 'do so.\n' +
                                 'Usage examples: `>OpenKibitz 1` `>OpenKibitz x3`',
                           inline=False)
        st_embed.add_field(name=">CloseKibitz [game number]",
                           value='Makes the kibitz channel to the game hidden from the public. This is typically '
                                 'already the case when you claim a grimoire, but might not be in some cases. Make '
                                 'sure none of your players have the kibitz role, as they could still see the channel '
                                 'in that case.\n' +
                                 'Usage examples: `>CloseKibitz 1`, `>CloseKibitz x3`',
                           inline=False)
        st_embed.add_field(name=">ArchiveGame [game number]",
                           value='Moves the game channel to the archive and creates a new empty channel for the next '
                                 'game. Also makes the kibitz channel hidden from the public. Use after post-game '
                                 'discussion has concluded. Do not remove the game number from the channel name until '
                                 'after archiving - you will still be able to do so afterwards.\n' +
                                 'Usage examples: `>ArchiveGame 1`, `>ArchiveGame x3`',
                           inline=False)
        st_embed.add_field(name=">EndGame [game number]",
                           value='Removes the game role from your players and the kibitz role from your kibitzers, '
                                 'makes the kibitz channel visible to the public, and sends a message reminding '
                                 'players to give feedback for the ST and providing a link to do so.\n' +
                                 'Usage examples: `>EndGame 1`, `>EndGame x3`',
                           inline=False)
        st_embed.add_field(name=">Signup [game number] [max player count] [script name]",
                           value='Posts a message listing the signed up players in the appropriate game channel, '
                                 'with buttons that players can use to sign up or leave the game. If players are '
                                 'added or removed in other ways, may need to be updated explicitly with the '
                                 'appropriate button to reflect those changes. Note that if a parameter contains '
                                 'spaces, you have to surround it with quotes.\n' +
                                 'Usage examples: `>Signup 1 12 Catfishing`, `>Signup x3 6 "My new homebrew Teensy"`',
                           inline=False)
        st_embed.add_field(name=">CreateThreads [game number]",
                           value='Creates a private thread in the game\'s channel for each player, named "ST Thread ['
                                 'player name]", and adds the player and all STs to it.\n' +
                                 'Usage examples: `>CreateThreads 1`, `>CreateThreads x3`',
                           inline=False)
        st_embed.add_field(name=">GiveGrimoire [game number] [User]",
                           value='Removes the ST role for the game from you and gives it to the given user. You can '
                                 'provide a user by ID, mention/ping, or nickname, though giving the nickname may '
                                 'find the wrong user.\n' +
                                 'Usage examples: `>GiveGrimoire 1 @Ben`, `>GiveGrimoire x3 107209184147185664`',
                           inline=False)
        st_embed.add_field(name=">DropGrimoire [game number]",
                           value='Removes the ST role for the game from you\n' +
                                 'Usage examples: `>DropGrimoire 1`, `>DropGrimoire x3`',
                           inline=False)
        st_embed.add_field(name=">ShareGrimoire [game number] [User]",
                           value='Gives the ST role for the game to the given user without removing it from you. Use '
                                 'if you want to co-ST a game.You can provide a user by ID, mention/ping, '
                                 'or nickname, though giving the nickname may find the wrong user.\n' +
                                 'Usage examples: `>ShareGrimoire 1 @Ben`, `>ShareGrimoire x3 108309184147185664`',
                           inline=False)
        st_embed.add_field(name=">AddPlayer [game number] [at least one user]",
                           value='Gives the appropriate game role to the given users. You can provide a user by ID, '
                                 'mention/ping, or nickname, though giving the nickname may find the wrong user.\n' +
                                 'Usage examples: `>AddPlayer 1 793448603309441095`, `>AddPlayer x3 @Alex @Ben @Celia`',
                           inline=False)
        st_embed.add_field(name=">RemovePlayer [game number] [at least one user]",
                           value='Removes the appropriate game role from the given users. You can provide a user by '
                                 'ID, mention/ping, or nickname, though giving the nickname may find the wrong '
                                 'user.\n' +
                                 'Usage examples: `>RemovePlayer 1 793448603309441095`, `>RemovePlayer x3 @Alex @Ben @Celia`',
                           inline=False)
        st_embed.add_field(name=">AddKibitz [game number] [at least one user] (Requires ST Role or Mod)",
                           value='Gives the appropriate game role to the given users. You can provide a user by ID, '
                                 'mention/ping, or nickname, though giving the nickname may find the wrong user.\n' +
                                 'Usage examples: `>AddKibitz 1 793448603309441095`, `>AddKibitz x3 @Alex @Ben @Celia`',
                           inline=False)
        st_embed.add_field(name=">RemoveKibitz [game number] [at least one user] (Requires ST Role or Mod)",
                           value='Removes the appropriate game role from the given users. You can provide a user by '
                                 'ID, mention/ping, or nickname, though giving the nickname may find the wrong '
                                 'user.\n' +
                                 'Usage examples: `>RemoveKibitz 1 793448603309441095`, `>RemoveKibitz x3 @Alex @Ben @Celia`',
                           inline=False)
        st_embed.set_footer(text="2/4")

        ts_embed = nextcord.Embed(title="Unofficial Text Game Bot",
                                  description="Commands related to the town square", color=0xe100ff)
        ts_embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")
        ts_embed.add_field(name=">SetupTownSquare [game_number] [players]",
                           value="Creates the town square for the given game, with the given players. Ping them in order of seating.\n"
                                 "Usage example: `>SetupTownSquare x1 @Alex @Ben @Celia @Derek @Eli @Fiona @Gabe @Hannah`",
                           inline=False)

        ts_embed.add_field(name=">UpdateTownSquare [game_number] [players]",
                           value="Updates the town square for the given game, with the given players. Ping them in order of seating."
                                 "The difference to rerunning SetupTownSquare is that the latter will lose information like aliases, "
                                 "spent deadvotes, and nominations. UpdateTownSquare will not.\n"
                                 "Usage example: `>UpdateTownSquare x1 @Alex @Ben @Celia @Derek @Eli @Fiona @Gideon @Hannah`",
                           inline=False)
        ts_embed.add_field(name=">CreateNomThread [game_number] [name]",
                           value='Creates a thread for nominations to be run in. The name of the thread is optional, with `Nominations` as default.\n'
                                 'Usage example: `>CreateNomThread x1`, `>CreateNomThread "D2 Nominations"`',
                           inline=False)

        ts_embed.add_field(name=">Nominate [game_number] [nominee] [nominator]",
                           value="Create a nomination for the given nominee. If you are a ST, provide the nominator. "
                                 "If you are a player, leave the nominator out or give yourself. In either case, you don't need to ping, a name should work.\n"
                                 "Usage examples: `>Nominate x1 Alex Ben`, >Nominate 3 Alex`",
                           inline=False)
        ts_embed.add_field(name=">AddAccusation [game_number] [accusation] [nominee_identifier]",
                           value='Add an accusation to the nomination of the given nominee. You don\'t need to ping, a name should work. You must be the nominator or a storyteller for this.\n'
                                 'Usage examples: `>AddAccusation x1 Alex "In a doubleclaim"`, >AddAccusation 3 Alex "I think they would be a great Undertaker test"`',
                           inline=False)
        ts_embed.add_field(name=">AddDefense [game_number] [defense] [nominee_identifier]",
                           value='Add a defense to your nomination or that of the given nominee. You must be a storyteller for the latter.\n'
                                 'Usage examples: `>AddDefense x1 "I\'m good I promise"`, >AddDefense 3 "This is fine"`',
                           inline=False)
        ts_embed.add_field(name=">SetDeadline [game_number] [nominee_identifier] [hours]",
                           value='Set the deadline for the nomination of a given nominee to the given number of hours from now. You must be a storyteller for this.\n'
                                 'Usage examples: `>SetDeadline x1 Alex 1`, `>SetDeadline 3 Alex 24`',
                           inline=False)
        ts_embed.add_field(name=">SetDefaultDeadline [game_number] [hours]",
                           value='Set the default nomination duration for the game to the given number of hours. You must be a storyteller for this.\n'
                                 'Usage examples: `>SetDefaultDeadline x1 36`, `>SetDefaultDeadline 3 24`',
                           inline=False)
        ts_embed.add_field(name=">Vote [game_number] [nominee_identifier] [vote]",
                           value='Set your vote for the given nominee. You don\'t need to ping, a name should work. '
                                 'Your vote can be anything (but should be something the ST can unambiguously interpret as yes or no when they count it).'
                                 'You can change your vote until it is counted by the storyteller.\n'
                                 'Usage examples: `>Vote x1 Alex yes`, `>Vote 3 Alex "no unless nobody is on the block"`',
                           inline=False)
        ts_embed.add_field(name=">PrivateVote [game_number] [nominee_identifier] [vote]",
                           value='Same as >Vote, but your vote will be hidden from other players. They will still see '
                                 'whether you voted yes or no after your vote is counted. A private vote will always override any public vote, even later ones. '
                                 'If you want your public vote to be counted instead, you can change your private vote accordingly or use >RemovePrivateVote.\n'
                                 'Usage examples: `>PrivateVote x1 Alex yes`, `>PrivateVote 3 Alex "drop my hand if there aren\'t enough votes yet"`',
                           inline=False)
        ts_embed.add_field(name=">RemovePrivateVote [game_number] [nominee_identifier]",
                           value='Removes your private vote for the given nominee, so that your public vote is counted instead.\n'
                                 'Usage examples: `>RemovePrivateVote x1 Alex`, `>RemovePrivateVote 3 Alex`',
                           inline=False)
        ts_embed.add_field(name=">CountVotes [game_number] [nominee_identifier]",
                           value='Begins counting the votes for the given nominee. You must be a storyteller for this.\n'
                                 'Usage examples: `>CountVotes x1 Alex`, `>CountVotes 3 Alex`',
                           inline=False)
        ts_embed.add_field(name=">CloseNomination [game_number] [nominee_identifier]",
                           value='Marks the nomination for the given nominee as closed. You must be a storyteller for this.\n',
                           inline=False)
        ts_embed.add_field(name=">SetAlias [game_number] [alias]",
                           value='Set your preferred alias for the given game. This will be used anytime '
                                 'the bot refers to you. By default set to your username. Can be used by players and storytellers.\n'
                                 'Usage examples: `>SetAlias x1 "Alex"`, `>SetAlias 3 "Alex"`',
                           inline=False)
        ts_embed.add_field(name=">ToggleOrganGrinder [game_number]",
                           value='Activates or deactivates Organ Grinder for the display of nominations in the game. You must be a storyteller for this.\n'
                                 'Usage examples: `>ToggleOrganGrinder x1`, `>ToggleOrganGrinder 3`',
                           inline=False)
        ts_embed.add_field(name=">TogglePlayerNoms [game_number]",
                           value='Activates or deactivates the ability of players to nominate directly. You must be a storyteller for this.\n'
                                 'Usage examples: `>TogglePlayerNoms x1`, `>TogglePlayerNoms 3`',
                           inline=False)
        ts_embed.add_field(name=">ToggleMarkedDead [game_number] [player_identifier]",
                           value="Marks the given player as dead or alive for display on nominations. You must be a storyteller for this.\n"
                                 "Usage examples: `>ToggleMarkedDead x1 Alex`, `>ToggleMarkedDead 3 Alex`",
                           inline=False)
        ts_embed.add_field(name=">ToggleCanVote [game_number] [player_identifier]",
                           value="Allows or disallows the given player to vote. You must be a storyteller for this.\n"
                                 "Usage examples: `>ToggleCanVote x1 Alex`, `>ToggleCanVote 3 Alex`",
                           inline=False)
        ts_embed.set_footer(text="3/4")

        mod_embed = nextcord.Embed(title="Unofficial Text Game Bot",
                                   description="Commands that can only be executed by moderators", color=0xe100ff)
        mod_embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")
        mod_embed.add_field(name=">InitQueue [channel type] ",
                            value="Initializes an ST queue in the channel or thread the command was used in, for the "
                                  "provided channel type (regular/experimental). Can be reused to create a new "
                                  "queue/queue message, but all previous entries of that queue will be lost in the "
                                  "process.",
                            inline=False)
        mod_embed.add_field(name=">RemoveFromQueue [user]",
                            value="Removes the given user from either queue. You can provide a user by ID, "
                                  "mention/ping, or nickname, though giving the nickname may find the wrong user.",
                            inline=False)
        mod_embed.add_field(name=">MoveToSpot [user] [spot]",
                            value="Moves the queue entry of the given user to the given spot in the queue, 1 being "
                                  "the top. You can provide a user by ID, mention/ping, or nickname, though giving "
                                  "the nickname may find the wrong user.",
                            inline=False)
        mod_embed.add_field(name=">OffServerArchive [Server ID] [Channel ID]",
                            value="Copies the channel the message was sent in to the provided server and channel, "
                                  "message by message.",
                            inline=False)
        mod_embed.set_footer(
            text="3/4")
        try:
            command_type = command_type.lower()
            if command_type == "all":
                await ctx.author.send(embed=anyone_embed)
                await ctx.author.send(embed=st_embed)
                await ctx.author.send(embed=ts_embed)
                await ctx.author.send(embed=mod_embed)
            elif command_type == "anyone":
                await ctx.author.send(embed=anyone_embed)
            elif command_type == "st":
                await ctx.author.send(embed=st_embed)
            elif command_type == "townsquare":
                await ctx.author.send(embed=ts_embed)
            elif command_type == "mod":
                await ctx.author.send(embed=mod_embed)
            elif command_type == "no-mod":
                await ctx.author.send(embed=anyone_embed)
                await ctx.author.send(embed=st_embed)
                await ctx.author.send(embed=ts_embed)
            else:
                await ctx.author.send(
                    'Use `all`, `anyone`, `st`, `townsquare`, `mod` or `no-mod` to filter the help message. '
                    'Default is `no-mod`.')
            await ctx.author.send("Note: If you believe that there is an error with the bot, please let Jack or a "
                                  "moderator know in order to resolve it. Thank you!")
        except nextcord.Forbidden:
            await ctx.send("Please enable DMs to receive the help message")
        await self.helper.finish_processing(ctx)

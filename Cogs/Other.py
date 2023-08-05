import asyncio
import datetime
import typing

import nextcord
from nextcord import InvalidArgument
from nextcord.ext import commands
from nextcord.utils import get, utcnow, format_dt

import utility
from Cogs.Townsquare import Townsquare


class Other(commands.Cog):

    def __init__(self, bot, helper: utility.Helper):
        self.bot = bot
        self.helper = helper

    @commands.command(usage="<game_number> [event] [times]...")
    async def SetReminders(self, ctx, *args):
        """At the given times, sends reminders to the players how long they have until the event occurs.
        The event argument is optional and defaults to "Whispers close". Times must be given in hours from the
        current time. You can give any number of times. The event is assumed to occur at the latest given time."""
        if len(args) < 2:
            await utility.deny_command(ctx)
            await utility.dm_user(ctx.author, "At least game number and one reminder time are required")
            return
        game_number = args[0]
        game_channel = self.helper.get_game_channel(game_number)
        if not game_channel:
            await utility.deny_command(ctx)
            await utility.dm_user(ctx.author, "The first argument must be a valid game number")
            return
        game_role = self.helper.get_game_role(game_number)
        event = "Whispers close"
        try:
            times = [float(time) for time in args[1:]]
        except ValueError:
            event = args[1]
            try:
                times = [float(time) for time in args[2:]]
            except ValueError as e:
                await utility.deny_command(ctx)
                await utility.dm_user(ctx.author, e.args[0])  # looks like: "could not convert string to float: 'bla'"
                return
            if len(times) == 0:
                await utility.deny_command(ctx)
                await utility.dm_user(ctx.author, "At least one reminder time is required")
                return
        if not self.helper.authorize_st_command(ctx.author, game_number):
            await utility.deny_command(ctx)
            await utility.dm_user(ctx.author, "You must be an ST to use this command")
            return
        await utility.start_processing(ctx)
        times.sort()
        end_of_countdown = utcnow() + datetime.timedelta(hours=times[-1])
        deltas = [times[0]] + [second - first for first, second in zip(times, times[1:])]
        await self.helper.finish_processing(ctx)
        await self.helper.log(f"{ctx.author.mention} has run the SetReminders command for game {game_number}")

        for wait_time in deltas[:-1]:
            await asyncio.sleep(wait_time * 3600)  # hours to seconds
            await game_channel.send(content=game_role.mention + " " + event + " " + format_dt(end_of_countdown, "R"))
        await asyncio.sleep(deltas[-1] * 3600)
        await game_channel.send(content=game_role.mention + " " + event)

    @commands.command()
    async def CreateThreads(self, ctx, game_number):
        """Creates a private thread in the game\'s channel for each player.
        The player and all STs are automatically added to each thread. The threads are named "ST Thread [player name]".
        """
        if self.helper.authorize_st_command(ctx.author, game_number):
            await utility.start_processing(ctx)
            townsquare_cog: typing.Optional[Townsquare] = self.bot.get_cog("Townsquare")
            if townsquare_cog and game_number in townsquare_cog.town_squares:
                townsquare = townsquare_cog.town_squares[game_number]
            else:
                townsquare = None
            for player in self.helper.get_game_role(game_number).members:
                if townsquare:
                    name = next((p.alias for p in townsquare.players if p.id == player.id), None)
                if not name:
                    name = player.display_name
                thread = await self.helper.get_game_channel(game_number).create_thread(
                    name=f"ST Thread {name}",
                    auto_archive_duration=4320,  # 3 days
                    type=nextcord.ChannelType.private_thread,
                    reason=f"Preparing text game {game_number}"
                )
                thread.invitable = False

                await thread.add_user(player)
                for st in self.helper.get_st_role(game_number).members:
                    await thread.add_user(st)

            await self.helper.finish_processing(ctx)
        else:
            await utility.dm_user(ctx.author, "You are not the current ST for game " + str(game_number))
            await utility.deny_command(ctx)

        await self.helper.log(f"{ctx.author.mention} has run the CreateThreads Command on Game {game_number}")

    @commands.command()
    async def HelpMe(self, ctx: commands.Context, command_type: typing.Optional[str] = "no-mod"):
        """Sends a message listing and explaining available commands.
        Can be filtered by appending one of `all, anyone, st, mod, no-mod`. Default is `no-mod`"""
        await utility.start_processing(ctx)
        anyone_embed = nextcord.Embed(title="Unofficial Text Game Bot",
                                      description="Commands that can be executed by anyone", color=0xe100ff)
        anyone_embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")

        anyone_embed.add_field(name=">FindGrimoire",
                               value="Sends you a DM listing all games and whether they currently have an ST. If they "
                                     "have an ST, it will list them.",
                               inline=False)
        anyone_embed.add_field(name=">ShowSignups [game_number]",
                               value="Sends you a DM listing the STs, players, and kibitz members of the game\n"
                                     "Usage examples: `>ShowSignups 1`, `>ShowSignups x3`",
                               inline=False)
        anyone_embed.add_field(name=">ClaimGrimoire [game number]",
                               value='Grants you the ST role of the given game, unless it is already occupied. '
                                     'Also removes you from the relevant queue.\n' +
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
        anyone_embed.add_field(name=">EditEntry [script name] [availability] [notes (optional)]",
                               value="Edits your queue entry. You cannot change the channel type. "
                                     "You have to give availability and script even if they have not changed."
                                     'Usage examples: `>EditEntry "Trouble Brewing" "after June 20"`')
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
                                 'do so. In most cases, EndGame may be the more appropriate command.\n' +
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
                                 'after archiving - you will still be able to do so afterward.\n' +
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
        st_embed.add_field(name=">SetReminders [game number] [event] [times]",
                           value='At the given times, sends reminders to the players how long they have until the event'
                                 ' occurs. The event argument is optional and defaults to "Whispers close". '
                                 'Times must be given in hours from the current time. You can give any number of times.'
                                 'The event is assumed to occur at the latest given time.\n'
                                 'Usage examples: `>SetReminders 1 "Votes on Alice close" 24`, '
                                 '`>SetReminders x3 18 24 30 33 36`',
                           inline=False)
        st_embed.add_field(name=">GiveGrimoire [game number] [User]",
                           value='Removes the ST role for the game from you and gives it to the given user. You can '
                                 'provide a user by ID, mention/ping, or nickname, though giving the nickname may '
                                 'find the wrong user.\n' +
                                 'Usage examples: `>GiveGrimoire 1 @Ben`, `>GiveGrimoire x3 107209184147185664`',
                           inline=False)
        st_embed.add_field(name=">DropGrimoire [game number]",
                           value='Removes the ST role for the game from you and announces the free channel if there is '
                                 'no other ST\n' +
                                 'Usage examples: `>DropGrimoire 1`, `>DropGrimoire x3`',
                           inline=False)
        st_embed.add_field(name=">ShareGrimoire [game number] [User]",
                           value='Gives the ST role for the game to the given user without removing it from you. Use '
                                 'if you want to co-ST a game. You can provide a user by ID, mention/ping, '
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
                           value='Gives the appropriate kibitz role to the given users. You can provide a user by ID, '
                                 'mention/ping, or nickname, though giving the nickname may find the wrong user.\n' +
                                 'Usage examples: `>AddKibitz 1 793448603309441095`, `>AddKibitz x3 @Alex @Ben @Celia`',
                           inline=False)
        st_embed.add_field(name=">RemoveKibitz [game number] [at least one user] (Requires ST Role or Mod)",
                           value='Removes the appropriate kibitz role from the given users. You can provide a user by '
                                 'ID, mention/ping, or nickname, though giving the nickname may find the wrong '
                                 'user.\n' +
                                 'Usage examples: `>RemoveKibitz 1 793448603309441095`, `>RemoveKibitz x3 @Alex @Ben @Celia`',
                           inline=False)
        st_embed.set_footer(text="2/4")

        ts_embed = nextcord.Embed(title="Unofficial Text Game Bot",
                                  description="Commands related to the town square", color=0xe100ff)
        ts_embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")
        ts_embed.add_field(name=">SetupTownSquare [game_number] [players]",
                           value="Creates the town square for the given game, with the given players. "
                                 "Ping them in order of seating.\n"
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
                                 'Usage examples: `>AddAccusation x1 "In a doubleclaim" Alex`, >AddAccusation 3 "I think they would be a great Undertaker test"`',
                           inline=False)
        ts_embed.add_field(name=">AddDefense [game_number] [defense] [nominee_identifier]",
                           value='Add a defense to your nomination or that of the given nominee. You must be a storyteller for the latter.\n'
                                 'Usage examples: `>AddDefense x1 "I\'m good I promise"`, >AddDefense 3 "This is fine"`',
                           inline=False)
        ts_embed.add_field(name=">SetVoteThreshold [game_number] [threshold]",
                           value='Set the vote threshold to put a player on the block to the given number. You must be a storyteller for this.\n'
                                 'Usage examples: `>SetVoteThreshold x1 4`, `>SetVoteThreshold 3 5`',
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
                                 'the bot refers to you. The default is your username. Can be used by players and storytellers.\n'
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
                            value="Moves the queue entry of the given user to the given spot in their queue, 1 being "
                                  "the top. You can provide a user by ID, mention/ping, or nickname, though giving "
                                  "the nickname may find the wrong user.",
                            inline=False)
        mod_embed.add_field(name=">OffServerArchive [Server ID] [Channel ID]",
                            value="Copies the channel the message was sent in to the provided server and channel, "
                                  "message by message. Attachments may not be preserved if they are too large. "
                                  "Also creates a discussion thread at the end.",
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
                                  "moderator know, or open an issue at https://github.com/JackKBroome/Carat_BOTC/issues"
                                  "\nThank you!")
        except nextcord.Forbidden:
            await ctx.send("Please enable DMs to receive the help message")
        await self.helper.finish_processing(ctx)

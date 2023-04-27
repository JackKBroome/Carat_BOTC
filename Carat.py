import os

import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands

from Cogs.Game import Game
from Cogs.Grimoire import Grimoire
from Cogs.Other import Other
from Cogs.Queue import Queue
from Cogs.Signup import Signup
from Cogs.Users import Users
from utility import Helper

load_dotenv()
token = os.environ['TOKEN']

intents = nextcord.Intents.all()
allowedMentions = nextcord.AllowedMentions.all()
allowedMentions.everyone = False

bot = commands.Bot(command_prefix=">",
                   case_insensitive=True,
                   intents=intents,
                   allowed_mentions=allowedMentions,
                   activity=nextcord.Game(">HelpMe or >help"))


# Output in terminal when bot turns on
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('Loading cogs')
    helper = Helper(bot)
    bot.add_cog(Game(bot, helper))
    bot.add_cog(Grimoire(bot, helper))
    bot.add_cog(Other(bot, helper))
    bot.add_cog(Queue(bot, helper))
    bot.add_cog(Signup(bot, helper))
    bot.add_cog(Users(bot, helper))
    print('Ready')
    print('------')


@bot.command()
async def HelpMe(ctx: commands.Context):
    # Add ShowSignUps here
    anyone_embed = nextcord.Embed(title="Unofficial Text Game Bot",
                                  description="Commands that can be executed by anyone", color=0xe100ff)
    anyone_embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")

    anyone_embed.add_field(name=">FindGrimoire",
                           value="Sends the user a DM listing all games and whether they currently have an ST.",
                           inline=False)
    anyone_embed.add_field(name=">ClaimGrimoire [game number]",
                           value='Grants you the ST role of the given game, unless it is already occupied\n' +
                                 'Usage examples: >ClaimGrimoire 1; >ClaimGrimoire x3',
                           inline=False)
    anyone_embed.add_field(name=">Enqueue [channel type] [script name] [availability] [notes (optional)]",
                           value="Adds you to the queue for the given channel type (regular/experimental), listing the provided information, unless you are already in either of the queues. Do not join a queue if you are currently storytelling. Note that if a parameter contains spaces, you have to surround it with quotes.\n" +
                                 'Usage examples: >Enqueue regular "Trouble Brewing" "anytime after june"; >Enqueue Exp "Oops All Amnesiacs" "between 07-13 and 07-30" "Let me know beforehand if you\'re interested"',
                           inline=False)
    anyone_embed.add_field(name=">Dequeue",
                           value="Removes you from the queue you are in currently",
                           inline=False)
    anyone_embed.add_field(name=">MoveDown [number]",
                           value="Moves you down that number of spaces in your queue - use if you can't run the game yet but don't want to be pinged every time a channel becomes free. Careful - you cannot move yourself back up, though you can ask a mod to fix things if you make a mistake",
                           inline=False)
    anyone_embed.add_field(name=">HelpMe",
                           value="Sends this message",
                           inline=False)
    anyone_embed.set_footer(text="1/3")

    st_embed = nextcord.Embed(title="Unofficial Text Game Bot",
                              description="Commands that can be executed by the ST of the relevant game - mods can ignore this restriction",
                              color=0xe100ff)
    st_embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")
    st_embed.add_field(name=">OpenKibitz [game number]",
                       value='Makes the kibitz channel to the game visible to the public. Players will still need to remove their game role to see it. Use after the game has concluded. Will also send a message reminding players to give feedback for the ST and provide a link to do so.\n' +
                             'Usage examples: >OpenKibitz 1; >OpenKibitz x3',
                       inline=False)
    st_embed.add_field(name=">CloseKibitz [game number]",
                       value='Makes the kibitz channel to the game hidden from the public. This is typically already the case when you claim a grimoire, but might not be in some cases. Make sure none of your players have the kibitz role, as they could still see the channel in that case.\n' +
                             'Usage examples: >CloseKibitz 1; >CloseKibitz x3',
                       inline=False)
    st_embed.add_field(name=">ArchiveGame [game number]",
                       value='Moves the game channel to the archive and creates a new empty channel for the next game. Also makes the kibitz channel hidden from the public. Use after post-game discussion has concluded. Do not remove the game number from the channel name until after archiving - you will still be able to do so afterwards.\n' +
                             'Usage examples: >ArchiveGame 1; >ArchiveGame x3',
                       inline=False)
    st_embed.add_field(name=">EndGame [game number]",
                       value='Removes the game role from your players and the kibitz role from your kibitzers, makes the kibitz channel visible to the public, and sends a message reminding players to give feedback for the ST and providing a link to do so.\n' +
                             'Usage examples: >EndGame 1; >EndGame x3',
                       inline=False)
    st_embed.add_field(name=">Signup [game number] [max player count] [script name]",
                       value='Posts a message listing the signed up players in the appropriate game channel, with buttons that players can use to sign up or leave the game. If players are added or removed in other ways, may need to be updated explicitly with the appropriate button to reflect those changes. Note that if a parameter contains spaces, you have to surround it with quotes.\n' +
                             'Usage examples: >Signup 1 12 Catfishing; >Signup x3 6 "My new homebrew Teensy"',
                       inline=False)
    st_embed.add_field(name=">CreateThreads [game number]",
                       value='Creates a private thread in the game\'s channel for each player, named "ST Thread [player name]", and adds the player and all STs to it.\n' +
                             'Usage examples: >CreateThreads 1; >CreateThreads x3',
                       inline=False)
    st_embed.add_field(name=">GiveGrimoire [game number] [User]",
                       value='Removes the ST role for the game from you and gives it to the given user. You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user.\n' +
                             'Usage examples: >GiveGrimoire 1 @Daddy Ben; >GiveGrimoire x3 107209184147185664',
                       inline=False)
    st_embed.add_field(name=">DropGrimoire [game number]",
                       value='Removes the ST role for the game from you\n' +
                             'Usage examples: >DropGrimoire 1; >DropGrimoire x3',
                       inline=False)
    st_embed.add_field(name=">ShareGrimoire [game number] [User]",
                       value='Gives the ST role for the game to the given user without removing it from you. Use if you want to co-ST a game.You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user.\n' +
                             'Usage examples: >ShareGrimoire 1 @Daddy Ben; >ShareGrimoire x3 108309184147185664',
                       inline=False)
    st_embed.add_field(name=">AddPlayer [game number] [at least one user]",
                       value='Gives the appropriate game role to the given users. You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user.\n' +
                             'Usage examples: >AddPlayer 1 793448603309441095; >AddPlayer x3 @eevee @Pam @Velvet',
                       inline=False)
    st_embed.add_field(name=">RemovePlayer [game number] [at least one user]",
                       value='Removes the appropriate game role from the given users. You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user.\n' +
                             'Usage examples: >RemovePlayer 1 793448603309441095; >RemovePlayer x3 @eevee @Pam @Velvet',
                       inline=False)
    st_embed.add_field(name=">AddKibitz [game number] [at least one user] (Requires ST Role or Mod)",
                       value='Gives the appropriate game role to the given users. You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user.\n' +
                             'Usage examples: >AddKibitz 1 793448603309441095; >AddKibitz x3 @eevee @Pam @Velvet',
                       inline=False)
    st_embed.add_field(name=">RemoveKibitz [game number] [at least one user] (Requires ST Role or Mod)",
                       value='Removes the appropriate game role from the given users. You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user.\n' +
                             'Usage examples: >RemoveKibitz 1 793448603309441095; >RemoveKibitz x3 @eevee @Pam @Velvet',
                       inline=False)
    st_embed.set_footer(text="2/3")

    mod_embed = nextcord.Embed(title="Unofficial Text Game Bot",
                               description="Commands that can only be executed by moderators", color=0xe100ff)
    mod_embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")
    mod_embed.add_field(name=">InitQueue [channel type] ",
                        value="Initializes an ST queue in the channel or thread the command was used in, for the provided channel type (regular/experimental). Can be reused to create a new queue/queue message, but all previous entries of that queue will be lost in the process.",
                        inline=False)
    mod_embed.add_field(name=">KickFromQueue [user]",
                        value="Removes the given user from either queue. You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user.",
                        inline=False)
    mod_embed.add_field(name=">MoveToSpot [user] [spot]",
                        value="Moves the queue entry of the given user to the given spot in the queue, 1 being the top. You can provide a user by ID, mention/ping, or nickname, though giving the nickname may find the wrong user.",
                        inline=False)
    mod_embed.add_field(name=">OffServerArchive [Server ID] [Channel ID]",
                        value="Copies the channel the message was sent in to the provided server and channel, message by message.",
                        inline=False)
    mod_embed.set_footer(
        text="3/3 - Note: If you believe that there is an error with the bot, please let Jack or a moderator know in order to resolve it. Thank You!")
    try:
        await ctx.author.send(embeds=[anyone_embed, st_embed, mod_embed])
    except:
        await ctx.send("Please enable DMs to receive the help message")


bot.run(token)

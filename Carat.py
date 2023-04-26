import os

import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands

from utility import Helper
from Cogs.Game import Game
from Cogs.Grimoire import Grimoire
from Cogs.Other import Other
from Cogs.Signup import Signup
from Cogs.Users import Users

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
helper = Helper(bot)


# Output in terminal when bot turns on
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('Loading cogs')
    bot.add_cog(Game(bot, helper))
    bot.add_cog(Grimoire(bot, helper))
    bot.add_cog(Other(bot, helper))
    # bot.add_cog(Queue(bot, helper))
    bot.add_cog(Signup(bot, helper))
    bot.add_cog(Users(bot, helper))
    print('Ready')
    print('------')


@bot.command()
async def HelpMe(ctx):
    # Add ShowSignUps here
    embed = nextcord.Embed(title="Unofficial Text Game Bot",
                           description="A List of commands for both Storytellers & Moderators", color=0xe100ff)
    embed.set_thumbnail(url="https://wiki.bloodontheclocktower.com/images/6/67/Thief_Icon.png")

    embed.add_field(name=">OpenKibitz [game number] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the brackets with your game number, for example #text-only-game-1 would be ">OpenKibitz 1" & #experimental-game-2 would be ">OpenKibitz x2". This command will change the viewing permission of the associated kibitz channel to be viewed by all players. It will also send a message reminding players to give feedback for the ST and provide a link to do so.',
                    inline=False)
    embed.add_field(name=">CloseKibitz [game number] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the brackets with your game number, for example #text-only-game-1 would be ">CloseKibitz 1" & #experimental-game-2 would be ">CloseKibitz x2". This command will change the viewing permission of the associated kibitz channel to be viewed by only players with the KibitzX role',
                    inline=False)
    embed.add_field(name=">ArchiveGame [game number] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the brackets with your game number, for example #text-only-game-1 would be ">ArchiveGame 1" & #experimental-game-2 would be ">ArchiveGame x2". This command is to signal the start of a new game, it will archive the previous game channel & create a new & cleared channel to run a new game in. It will also change the viewing permission of the associated kibitz to only be viewed by "Kibitz?" role.',
                    inline=False)
    embed.add_field(name=">EndGame [game number] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the brackets with your game number, for example #text-only-game-1 would be ">NewGame 1" & #experimental-game-2 would be ">NewGame x2". This command is to signal the end of a text game. This command will remove "GameX" & "KibitzX" role from each player who had it, along with changing the viewing permissions of the Kibitz channel to allow the All Discord Users role to view it. It will also send a message reminding players to give feedback for the ST and provide a link to do so.',
                    inline=False)
    embed.add_field(name=">Signup [game number] [Player Count] [Script Name] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the first brackets with your game number, the second with the number of players allowed in the game & finally the name of the script (Please note: If the script name is multiple words eg. Trouble Brewing, it will require speech marks around the script name eg "Trouble Brewing"), for example #text-only-game-1 would be ">Signup 1 10 BMR" & #experimental-game-2 would be >Signup x2 9 Catfishing". This command is used to automate the signup board, it will post an embedded message in the correct channel that players can react to sign up to & react to remove themselves from the game. This updates in almost real time & requires no intervention from the storyteller. When a player is signed up their name will appear in the signup list & they will be assigned the "game?" role automatically.',
                    inline=False)
    embed.add_field(name=">CreateThreads [game number] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. To run this command you should replace the brackets with your game number, for example #text-only-game-1 would be ">CreateThreads 1" & #experimental-game-2 would be ">CreateThreads x2". This command is to assist in preparing a text game. This command will create a private thread in the game\'s channel for each player, named "ST Thread [player name]", and add the player and all STs to it.',
                    inline=False)
    embed.add_field(name=">FindGrimoire",
                    value="Sends the user a DM showing which games currently do not have an ST.",
                    inline=False)
    embed.add_field(name=">ClaimGrimoire [game number]",
                    value='This will assign you the "st?" role for the denoted game number, providing there is not currently a player with the "st?" role.',
                    inline=False)
    embed.add_field(name=">GiveGrimoire [game number] [@Player] (Requires ST Role or Mod)",
                    value='This will remove the "st?" role from you for the denoted game number & assign the "st?" role to the tagged player.',
                    inline=False)
    embed.add_field(name=">DropGrimoire [game number] (Requires ST Role or Mod)",
                    value='This will remove the "st?" role from you for the denoted game number',
                    inline=False)
    embed.add_field(name=">ShareGrimoire [game number] [@Player] (Requires ST Role or Mod)",
                    value='This will assign the "st?" role to the tagged player for the denoted game number, this will allow multiple people to co-ST a game.',
                    inline=False)
    embed.add_field(name=">AddPlayer [game number] [at least one user] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. It will give the "game?" role to the given users for the denoted game number. You can give users by pinging them or providing their ID. Name can also work, but is error prone - avoid it',
                    inline=False)
    embed.add_field(name=">RemovePlayer [game number] [at least one user] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. It will remove the "game?" role from the given users for the denoted game number. You can give users by pinging them or providing their ID. Name can also work, but is error prone - avoid it',
                    inline=False)
    embed.add_field(name=">AddKibitz [game number] [at least one user] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. It will give the "kibitz?" role to the given users for the denoted game number. You can give users by pinging them or providing their ID. Name can also work, but is error prone - avoid it',
                    inline=False)
    embed.add_field(name=">RemoveKibitz [game number] [at least one user] (Requires ST Role or Mod)",
                    value='To run this command it requires that you have the "st?" role. It will remove the "kibitz?" role from the given users for the denoted game number. You can give users by pinging them or providing their ID. Name can also work, but is error prone - avoid it',
                    inline=False)
    embed.add_field(name=">OffServerArchive [Server ID] [Channel ID] (Requires Mod)",
                    value="A Mod-only command that archives the channel the message was sent in to the provided server and channel.")
    embed.add_field(name=">HelpMe",
                    value="Sends a direct message of this to the player who typed the command",
                    inline=False)
    embed.set_footer(
        text="Note: If you believe that there is an error with the bot, please let Jack or a moderator know in order to resolve it. Thank You!")
    await ctx.author.send(embed=embed)


bot.run(token)

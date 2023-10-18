import io
import logging
import os
import sys
import traceback
from typing import Optional, List

import nextcord
import requests
from dotenv import load_dotenv
from nextcord.ext import commands
from nextcord.ext.commands import DefaultHelpCommand, CommandError

import utility

LogFile = "Carat.log"

LogLevelMapping = {'DEBUG': logging.DEBUG,
                   'INFO': logging.INFO,
                   'WARNING': logging.WARNING,
                   'ERROR': logging.ERROR,
                   'CRITICAL': logging.CRITICAL}

logging.basicConfig(filename=LogFile, filemode="w",
                    format="%(asctime)s - %(levelname)s: %(message)s",
                    level=logging.INFO)

try:
    load_dotenv()
    token = os.environ['TOKEN']
except Exception as e:
    message = "Encountered an issue loading environment variables. Ensure .env file exists and is properly formatted " \
              "with all necessary variables.\nException: " + str(e)
    print(message)
    logging.critical(message)
    sys.exit()

intents = nextcord.Intents.all()
allowedMentions = nextcord.AllowedMentions.all()
allowedMentions.everyone = False
help_command = DefaultHelpCommand(verify_checks=False, dm_help=None, dm_help_threshold=600)

bot = commands.Bot(command_prefix=">",
                   case_insensitive=True,
                   intents=intents,
                   allowed_mentions=allowedMentions,
                   activity=nextcord.Game(">HelpMe or >help"),
                   help_command=help_command,
                   owner_id=utility.OwnerID)


# load cogs and print ready message
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('Loading cogs')
    cog_paths = ["Cogs." + os.path.splitext(file)[0] for file in os.listdir("Cogs") if file.endswith(".py")]
    load_extensions(cog_paths)
    print('Ready')
    print('------')
    logging.info("Carat online")


def load_extensions(paths: List[str]):
    for extension in paths:
        try:
            bot.load_extension(extension)
        except commands.ExtensionFailed as e:
            logging.exception(f"Failed to load {extension}: {e}")


@bot.event
async def on_command_error(ctx: commands.Context, error: CommandError):
    if isinstance(error, commands.CommandNotFound):
        # filter out emoji like >.> by checking if first character after > is a letter
        if ctx.message.content[1].isalnum() and not ctx.message.content[1].isdigit():
            await utility.dm_user(ctx.author, "Command not found. Use >help for a list of commands, "
                                              "or >HelpMe for a list of commands with explanations.")
    elif isinstance(error, commands.UserInputError):
        await utility.dm_user(ctx.author, f"There was an issue with your input. Usage: "
                                          f"`>{ctx.command.name} {ctx.command.signature}`.")
        logging.warning(f"Command {ctx.command.name} was used with incorrect input: {ctx.message.content}")
    else:
        traceback_buffer = io.StringIO()
        traceback.print_exception(type(error), error, error.__traceback__, file=traceback_buffer)
        traceback_text = traceback_buffer.getvalue()
        logging.exception(f"Ignoring exception in command {ctx.command}:\n{traceback_text}")


def get_level(line: str):
    line_without_time = line.split(" - ")[1]
    line_without_message = line_without_time.split(": ")[0]
    return LogLevelMapping[line_without_message.strip().upper()]


@bot.command()
async def SendLogs(ctx: commands.Context, limit: int, level: Optional[str] = "ERROR"):
    """Sends a number of the most recent log events as a DM. The number is given by limit. Events are filtered by
    logging level. Restricted to developers."""
    if level.upper() not in LogLevelMapping:
        await utility.deny_command(ctx, "Not a valid logging level")
        return
    if ctx.author.id == utility.OwnerID or \
            (ctx.author.id in utility.DeveloperIDs and level.upper() in ["WARNING", "ERROR", "CRITICAL"]):
        log_level = LogLevelMapping[level.upper()]
        await utility.start_processing(ctx)
        with open(LogFile, "r") as logs:
            lines = logs.readlines()
        items = []
        for line in lines:
            try:
                level = get_level(line)
                if level >= log_level:
                    items.append(line)
            except (KeyError, IndexError):
                # exception traces occupy several lines, and for all but the first get_level should fail
                if level >= log_level:
                    items[-1] += "\n" + line
        if limit < len(items):
            items = items[-limit:]
        bytes_data = io.BytesIO("\n".join(items).encode("utf-8"))
        await ctx.author.send("Logs", file=nextcord.File(bytes_data, f"Carat_{log_level}_{limit}.log"))
        await utility.finish_processing(ctx)
    else:
        await utility.deny_command(ctx, "You lack permission for this command")
        logging.warning(f"{ctx.author.display_name} (id: {ctx.author.id}) attempted to access Carat's logs")


@bot.command()
@commands.is_owner()
async def ReloadCogs(ctx: commands.Context):
    """Loads newest version of cogs from GitHub repository. Restricted to repository owner"""

    await utility.start_processing(ctx)
    cog_paths = ["Cogs." + os.path.splitext(file)[0] for file in os.listdir("Cogs") if file.endswith(".py")]
    for cog in cog_paths:
        if cog[5:] in bot.cogs:
            bot.unload_extension(cog)
        logging.info(", ".join(bot.cogs.keys()))
    await utility.dm_user(ctx.author, "Unloaded cogs: " + ", ".join([c[5:] for c in cog_paths]))
    response = requests.get("https://api.github.com/repos/JackKBroome/Carat_BOTC/contents/Cogs",
                            headers={"Accept": "application/vnd.github+json",
                                     "X-GitHub-Api-Version": "2022-11-28"})
    if response.status_code != 200:
        await utility.deny_command(ctx, "Could not connect to GitHub")
        load_extensions(cog_paths)
        await utility.dm_user(ctx.author, "reloaded original cogs")
        return
    for file in response.json():
        if file["name"].endswith(".py"):
            response = requests.get(file["download_url"])
            if response.status_code != 200:
                await utility.deny_command(ctx, "Could not connect to GitHub")
                load_extensions(cog_paths)
                await utility.dm_user(ctx.author, "reloaded original cogs")
                return
            with open(os.path.join("Cogs", file["name"]), "w", encoding="utf-8") as f:
                f.write(response.text)
    new_cog_paths = ["Cogs." + os.path.splitext(file)[0] for file in os.listdir("Cogs") if file.endswith(".py")]
    load_extensions(new_cog_paths)
    await utility.dm_user(ctx.author, "Loaded new cogs: " + ", ".join([c[5:] for c in new_cog_paths]))
    await utility.finish_processing(ctx)


@bot.command()
async def Restart(ctx: commands.Context):
    if ctx.author.id == utility.OwnerID or ctx.author.id in utility.DeveloperIDs:
        logging.warning("Trying to restart Carat...")
        # bot.close() finishes execution of bot.run(), so Carat terminates and is restarted by the loop in AutoRestart
        await bot.close()
    else:
        await utility.deny_command(ctx, "You lack permission for this command")
        logging.warning(f"{ctx.author.display_name} (id: {ctx.author.id}) attempted to restart Carat")


bot.run(token)

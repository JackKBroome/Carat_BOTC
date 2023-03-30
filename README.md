# Carat Discord Bot
Carat Bot for BOTC Unofficial discord server written in nextcord, the python wrapper for the Discord API

## Deployment instructions
1. Install the necessary packages (nextcord, python-dotenv). The packages os, time and asyncio should already be installed.
2. Create a file called `.env`, if it doesn't exist. To do this, you can copy `.env-dist` or create it manually. `.env-dist` contains the appropriate values to run Carat for the BotC Unofficial discord, aside from the token, which you must add yourself. Make sure to never commit or otherwise upload any file containing the bot token. `.env` (unlike `.env-dist`) is included in the `.gitignore`, so it is safe from this. If you want to run Carat somewhere that is not the BotC Unofficial discord, set the environment variables to the appropriate values.
3. Run the bot!
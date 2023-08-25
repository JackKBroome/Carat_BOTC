
# Carat Discord Bot

Carat is a discord bot written in Nextcord (A python wrapper for the Discord API), designed to help facilitate text games of Blood on the Clocktower.

Use `>help` or `>HelpMe` for mor information.




## Authors
- [@Qaysed](https://github.com/Qaysed) - Major contributions throughout all of Carat
- [@Broome](https://github.com/JackKBroome) - Initial Developer
- [@Kanave](https://github.com/lilymnky-F) - OffServerArchive contributed



## Used By

This project is used by the following discord servers:

- [@Blood on the Clocktower Unofficial](http://discord.gg/botc)
- [@Blood on the Clocktower Unofficial Archive](https://discord.gg/epj5h3yK)


## Game Role Management

- To see who is running a game use:
`>FindGrimoire` 

- To become the ST of an empty game use:
`>ClaimGrimoire [Game Number]` 

- You can invite a Co-ST with:
`>ShareGrimoire [Game Number] [@member]` 

- You can give the ST role of a game to another player by:
`>GiveGrimoire [Game Number] [@member]` 

- You can remove yourself as the ST role of a game by:
`>DropGrimoire [Game Number]` 

- You add & remove players to your kibitz with:
`>AddKibitz [Game Number] [@member]`  
`>RemoveKibitz [Game Number] [@member]` 

- You can change the viewing permissions of kibitz for every player using:
`>OpenKibitz [Game Number]`  
`>CloseKibitz [Game Number]` 
## Text Queue
- To setup the Queue (Done by Server Moderators) use:
`>InitQueue [x/r]` 

![Automatic Queue](https://github.com/JackKBroome/Carat_BOTC/blob/main/ReadMe%20Images/Queue.PNG?raw=true)


 - To Join or leave the Queue use:
`>JoinTextQueue [x/r] [Script] [Availability] [Notes]`  
`>LeaveTextQueue [x/r]` 

- You can edit your entries & delay your turn using:     
`>EditEntry [Script] [Availability] [Notes]`  
`>MoveDown [Number of Spots to move down]` 

- To moderate the queue, mods can move players to certain positions or remove them from the queue entirely:  
`>RemoveFromQueue [@member]`  
`>MoveToSpot [@member] [Queue Position Number]` 

- When the next game starts Carat will notify the top of the queue as seen below:

![Grimoire Ping](https://github.com/JackKBroome/Carat_BOTC/blob/main/ReadMe%20Images/VoterPing.PNG?raw=true)
## Game Sign-ups & Setup

- STs can automate signups throuh Carat using:
`>Signup [Game Number] [Player Limit] [Script Name]` 

![Sign up Screen](https://github.com/JackKBroome/Carat_BOTC/blob/main/ReadMe%20Images/SignupSheet.PNG?raw=true)

- STs can also run signups manually using:
`>AddPlayer [Game Number] [@member]`  
`>RemovePlayer [Game Number] [@member]` 

- To see who is signed up to a game use:
`>ShowSignups [Game Number]`  

- Some STs choose to have private threads woth each player, this can be automated, including posting a setup message in each thread by:
`>CreateThreads [Game Number] [Setup Message]`  
## Text Game Voting (Player)

- You can set your preferered name with:
`>SetAlias [Game Number] [Alias]`

- You can nominate players with:
`>Nominate [Game Number] [Nominee Name]`

- As the Nominator or Nominatee you add the acusation or defense with:
`>AddAccusation [Game Number] [Accusation] [Nominee Name]`  
`>AddDefence [Game Number] [Defence] [Nominee Name]`

- You can vote through Carat with (note this does not have to be exclusivley Y/N, any input values will be given to the ST to evaluate), Private votes override public votes to the ST:
`>Vote [Game Number] [Nominee Name] [Vote]`  
`>PrivateVote [Game Number] [Nominee Name] [Vote]`  
`>RemovePrivateVote [Game Number] [Nominee Name]`  

![Player Voting](https://github.com/JackKBroome/Carat_BOTC/blob/main/ReadMe%20Images/VoteToPlayers.PNG?raw=true)


## Text Game Voting (ST)

- To setup or adjust the voting circle you can use:
`>SetupTownSquare [Game Number] [@member1] [@member2]...`  
`>UpdateTownSquare [Game Number] [@member1] [@member2]...`  
`>SubstitutePlayer [Game Number] [@player] [@substitute]`

- To create a thread for voting use:
`>CreateNomThread [Game Number]`  

- To set the required number of votes to put someone on the block:
`>SetVoteThreshold [Game Number] [Number]` 

- To enable players to Nominate:
`>TogglePlayerNoms [Game Number]`  

- To add a timer to how long votes last:
`>SetDefaultDeadline [Game Number] [Hours]`  
`>SetDeadline [Game Number] [Nominee] [Hours]` 

- To set the state of voting for a certain player (Dead & Dead vote):
`>ToggleDead [Game Number] [@member]`  
`>ToggleCanVote [Game Number] [@member]`  

- To toggle the visibility of votes you can:
`>ToggleOrganGrinder [Game Number]`  

- To count the votes you can:
`>CountVotes [Game Number] [Nominee]`  

![ST Voting](https://github.com/JackKBroome/Carat_BOTC/blob/main/ReadMe%20Images/VoteInProgress.PNG?raw=true)


## Ending & Archiving Games

- When a game is finished the ST can reset all game roles & post a feedback from by using:

`>EndGame [Game Number]`  

![End Game](https://github.com/JackKBroome/Carat_BOTC/blob/main/ReadMe%20Images/EndGame.PNG?raw=true)

- You can also save games on server (in the Archived games section) by:

`>ArchiveGame [Game Number]`  

- Carat can help store text games all in a location (even across servers) using:

`>OffServerArchive [Server ID] [Channel ID]`  
- Public threads are stored, private ones are not, but either can be adjusted on a thread by thread basis using:

`>IncludeInArchive`  
`>ExcludeFromArchive`
## Deployment instructions

1. Download the necessary files (`Carat.py`, `utility.py`, the `Cogs` directory) and make sure they are arranged correctly (`Carat.py` and `utility.py`, and the `Cogs` directory all lying in the same directory)
2. Install the necessary packages (`nextcord`, `python-dotenv`, `dataclasses-json`) - typically you'll want to use pip for this, with `pip install [package name]`. The other packages used should be included in your python installation.
3. Create a file called `.env`, if you don't have one. To do this, you can copy `.env-dist` or create it manually. `.env-dist` contains the appropriate values to run Carat for the BotC Unofficial discord, aside from the token, which you must add yourself. Make sure to never commit or otherwise upload any file containing the bot token. `.env` (unlike `.env-dist`) is included in the `.gitignore`, so it is safe from this. If you want to run Carat somewhere that is not the BotC Unofficial discord, set the environment variables to the appropriate values. The `.env` has to lie in the same directory as `Carat.py`
4. Create a directory named `data` for Carat to store information in - or if you want its information stored elsewhere, adjust the `STORAGE_LOCATION` in the `.env` accordingly
5. Run Carat.py!


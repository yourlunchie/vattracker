import discord
from dotenv import load_dotenv
from discord.ext import commands
import os
import logging
import atcnotifyfile as atcnotifyfile
import departure_arrivalboard

load_dotenv(".env")
token = os.getenv("DISCORD_TOKEN")
channel_id = int(os.getenv("CHANNEL_ID"))
# guildid = os.getenv("guildid") - use it if you need to test commands with guilds

logging.basicConfig(filename="discord.log",filemode="w", level=logging.ERROR)
intents = discord.Intents.default()
# Guild = discord.Object(id=guildid)

bot = commands.Bot(command_prefix="/", intents=intents)

# activetrackfile.activetrackcommand(bot)
atcnotifyfile.atcnotifycommands(bot)
departure_arrivalboard.departure_arrival_board_commands(bot)

@bot.event
async def on_ready():
    print(f"VatTracker is ready to operate!")
    channel = bot.get_channel(channel_id)
    
    await bot.load_extension("cogs.aircraftinfo")
    await bot.load_extension("cogs.weather")
    await bot.load_extension("cogs.atcinfo")
    await bot.load_extension("cogs.activetrack")
    # load any cogs above
    await bot.tree.sync()
    
    # activetrackfile.starttrackloop(bot) we are disabling for TESTING of new activetrack
    atcnotifyfile.atcnotifyloop(bot)
    if channel:
        await channel.send("hello world! run /help to look for commands!")
    else:
        print("channel not found")

@bot.tree.command(name="credits", description="Who built and supported this bot")
async def credits(interaction: discord.Interaction):
    creditsembed = discord.Embed(title="Credits")
    creditsembed.add_field(name="Creator", value="yourlunch321", inline=False)
    creditsembed.add_field(name="Friends who helped me along the way", value="**Argon** - thank u for server hosting and being a good friend \n**thereal** - the person who inspired me to learn programming\n**alphagolfcharlie** - help on the code")
    await interaction.response.send_message(embed=creditsembed)

bot.run(token)
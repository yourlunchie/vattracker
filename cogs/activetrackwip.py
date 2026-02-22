import discord
from discord.ext import commands
from discord import app_commands
import json
from pathlib import Path
import utils

class ActiveTrackCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currenttracks = utils.read_or_create_file("currenttracks.json")
        
    @app_commands.command(name="activetrackwip",description="Tracks your aircraft on the network, and DMs you if entering an active ARTCC/FIR")
    async def activetrackwip(self, interaction: discord.Interaction, callsign: str):
        self.currenttracks[callsign.upper()] = {
            "user_id": interaction.user.id,
            "pinged_artccs": []
        }
        with open("currenttracks.json") as file:
            json.dump(self.currenttracks, file)
        tracking_begunEmbed = discord.Embed(title=f"Tracking begun for {callsign.upper()}", description="Tracking begun! Please turn on DMs from bots to receive activetrack notifications.")
        await interaction.response.send_message(embed=tracking_begunEmbed)
        print(self.currenttracks)
        
class ActiveTrackLoop():
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(ActiveTrackCommand(bot))
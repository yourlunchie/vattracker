import discord
from discord.ext import commands
from discord import app_commands
import json
from pathlib import Path
from utils import read_or_create_file
import asyncio
import shapely
from shapely.geometry import shape, Point

class ActiveTrackCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currenttracks = read_or_create_file("currenttracks.json")
        self.build_artcc_polygons()
        
    @app_commands.command(name="activetrackwip",description="Tracks your aircraft on the network, and DMs you if entering an active ARTCC/FIR")
    async def activetrackwip(self, interaction: discord.Interaction, callsign: str):
        self.currenttracks[callsign.upper()] = {
            "user_id": interaction.user.id,
            "pinged_artccs": []
        }
        with open("currenttracks.json", "w") as file:
            json.dump(self.currenttracks, file, indent=4)
        tracking_begunEmbed = discord.Embed(title=f"Tracking begun for {callsign.upper()}", description="Tracking begun! Please turn on DMs from bots to receive activetrack notifications.")
        await interaction.response.send_message(embed=tracking_begunEmbed)
        print(self.currenttracks)
        
class ActiveTrackLoop():
    def __init__(self, bot):
        self.bot = bot
        self.interval = 10
        self.running = False
        self.artcc_polygons = self.build_artcc_polygons()
        
    def build_artcc_polygons(self):
        artcc_polygons = {}
        current_directory = Path.cwd()
        with open(f"{current_directory}\\Boundaries.geojson", "r") as file:
            artcc_polygonsRaw = json.load(file)
        for feature in artcc_polygonsRaw["features"]:
            artcc_polygons[feature["properties"]["id"]] = {
                "is_oceanic": feature["properties"]["oceanic"],
                "polygon": shape(feature["geometry"])
            }
        return artcc_polygons

    async def loop(self):
        while self.running:
            await asyncio.sleep(self.interval)
    
    def start(self):
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self.loop())
            
    def stop(self):
        self.running=False

    def cancel(self):
        if self.task:
            self.task.cancel()

async def setup(bot):
    await bot.add_cog(ActiveTrackCommand(bot))
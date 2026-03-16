import discord
from discord.ext import commands
from discord import app_commands
import json
from pathlib import Path
import utils
from utils import read_or_create_file
from parseaustraliasectors import parseaustraliasectors
import asyncio
import shapely
from shapely.geometry import shape, Point
import aiohttp

class ActiveTrackCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currenttracks = read_or_create_file("currenttracks.json")
        
    @app_commands.command(name="activetrackwip",description="Tracks your aircraft on the network, and DMs you if entering an active ARTCC/FIR")
    async def activetrackwip(self, interaction: discord.Interaction, callsign: str):
        self.currenttracks = read_or_create_file("currenttracks.json")
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
        self.interval = 5
        self.running = False
        self.artcc_polygons = self.build_artcc_polygons()
        self.current_tracks = ActiveTrackCommand(bot)
        with open("icaotoartccfir.json", "r") as file:
            self.icaotoartcc = json.load(file)
        
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
    
    async def fetch_vatsim_data(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://data.vatsim.net/v3/vatsim-data.json") as payload:
                vatsim_data = await payload.json()
                return vatsim_data

    async def loop(self):
        while self.running:
            self.vatsim_data = await self.fetch_vatsim_data()
            
            CTR_controllers = {}
            list_australianSectors = await parseaustraliasectors()
            for sector in list_australianSectors:
                sector_callsign = "Y" + sector
                CTR_controllers[sector_callsign] = {
                    "callsign": sector_callsign + "_CTR",
                    "parsed_callsign": "none",
                    "frequency": "none",
                    "name": "none"
                }
            
            for controller in self.vatsim_data["controllers"]:
                if controller["callsign"][-3:] == "CTR" or controller["callsign"][-3:] == "FSS":
                    parsed_callsign = controller["callsign"][:3] +"_"+ controller["callsign"][-3:]
                    if controller["callsign"] in self.icaotoartcc["vatuk"]:
                        # we do this because VATUK facilities are the only ones in icaotoartcc.json that arent shortened callsigns
                        CTR_controllers[self.icaotoartcc["vatuk"][controller["callsign"]]["facility"]] = {
                            "callsign": controller["callsign"],
                            "parsed_callsign": "none",
                            "frequency": controller["frequency"],
                            "name": self.icaotoartcc["vatuk"][controller["callsign"]]["callsign"]
                        }
                    elif parsed_callsign in self.icaotoartcc["everything_else"]:
                        CTR_controllers[self.icaotoartcc["everything_else"][parsed_callsign]["facility"]] = {
                            "callsign": controller["callsign"],
                            "parsed_callsign": parsed_callsign,
                            "frequency": controller["frequency"],
                            "name": self.icaotoartcc["everything_else"][parsed_callsign]["callsign"]
                        }
                    elif controller["callsign"][:2] == "ML" or controller["callsign"][:2] == "BN":
                        # we pass because we add all this before
                        pass 
                    else:
                        CTR_controllers[controller["callsign"][:4]] = {
                            "callsign": controller["callsign"],
                            "parsed_callsign": controller["callsign"][:4] + "_" + controller["callsign"][-3:],
                            "frequency": controller["frequency"],
                            "name": "none"
                        }
                    
                else:
                    pass
                
            # ok controller list done now pilot handling
            for track in self.current_tracks.currenttracks:
                for pilot in self.vatsim_data["pilots"]:
                    if pilot["callsign"] == track:
                        longitude = pilot["longitude"]
                        latitude = pilot["latitude"]
            
            print(CTR_controllers)
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
    
    loop = ActiveTrackLoop(bot)
    loop.start()
    
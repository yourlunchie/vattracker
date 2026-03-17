import discord
from discord.ext import commands
from discord import app_commands
import json
from pathlib import Path
from utils import read_or_create_file
from parseaustraliasectors import parseaustraliasectors
import asyncio
import shapely
from shapely.geometry import shape, Point
import aiohttp
from typing import Optional
import math
import traceback

class ActiveTrackCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currenttracks = read_or_create_file("currenttracks.json")
        
    @app_commands.command(name="activetrack",description="Tracks your aircraft on the network, and DMs you if entering an active ARTCC/FIR")
    async def activetrack(self, interaction: discord.Interaction, callsign: str, ping_in_advance_miles: Optional[int] = 0):
        self.currenttracks = read_or_create_file("currenttracks.json")
        self.currenttracks[callsign.upper()] = {
            "user_id": interaction.user.id,
            "pinged_artccs": [],
            "miles_in_advance": ping_in_advance_miles
        }
        with open("currenttracks.json", "w") as file:
            json.dump(self.currenttracks, file, indent=4)
        tracking_begunEmbed = discord.Embed(title=f"Tracking begun for {callsign.upper()}", description="Tracking begun! Please turn on DMs from bots to receive activetrack notifications.")
        await interaction.response.send_message(embed=tracking_begunEmbed)
        
class ActiveTrackLoop():
    def __init__(self, bot):
        super().__init__()
        
        self.bot = bot
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
            
    async def assemble_message(self):
        counter = 0
        center_callsignP = self.center_controller["parsed_callsign"]
        center_callsign = self.center_controller["callsign"]
        center_frequency = self.center_controller["frequency"]
        center_name = self.center_controller["name"]
        if center_callsignP != "none":
            for controller in self.vatsim_data["controllers"]:
                if controller["callsign"][:3] + "_" + controller["callsign"][-3:] == center_callsignP:
                    counter += 1
        else:
            counter = -1 #this indicates there is inherently no split available for a center
        if counter == 1 or counter == 0:
            if center_frequency == "none" and center_name == "none":
                return f"<@{self.current_iteminTrack["user_id"]}>, your flight **{self.current_trackinTrack}** is entering **{center_callsign}**"
            elif center_name == "none":
                return f"<@{self.current_iteminTrack["user_id"]}>, your flight **{self.current_trackinTrack}** is entering **{center_callsign}** ({center_frequency})"
            else:
                return f"<@{self.current_iteminTrack["user_id"]}>, your flight **{self.current_trackinTrack}** is entering **{center_callsign}** ({center_frequency}) - {center_name}"
    
    async def find_location_in_advance(self):
        radian = math.radians(self.heading)
        
        opposite = self.miles_in_advance * math.sin(radian) #longitude raw
        adjacent = self.miles_in_advance * math.cos(radian) #latitude raw
        
        shrink_ray = math.cos(math.radians(self.latitude_pre))
        longitude_add = opposite / (60 * shrink_ray)
        latitude_add = adjacent / 60 # convert latitude to minutes of a degree from degree
        
        latitude = self.latitude_pre + latitude_add
        longitude = self.longitude_pre + longitude_add
        
        return longitude, latitude
        
    async def loop(self):
        while self.running:
            try:
                self.current_tracks.currenttracks = read_or_create_file("currenttracks.json")
                
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
                for track, item in self.current_tracks.currenttracks.items():
                    self.artcc = None
                    
                    self.current_trackinTrack = track
                    self.current_iteminTrack = item
                    for pilot in self.vatsim_data["pilots"]:
                        if pilot["callsign"] == track:
                            
                            if item["miles_in_advance"] == 0:
                                longitude = pilot["longitude"]
                                latitude = pilot["latitude"]
                                point = Point(longitude,latitude)
                            else:
                                self.longitude_pre = pilot["longitude"]
                                self.latitude_pre = pilot["latitude"]
                                self.miles_in_advance = item["miles_in_advance"]
                                self.heading = pilot["heading"]
                                longitude2, latitude2 = await self.find_location_in_advance()
                                point = Point(longitude2, latitude2)
                                
                            for feature, featureitem in self.artcc_polygons.items():
                                if point.within(featureitem["polygon"]):
                                    self.artcc = feature[:4]
                                    break
                                    
                            # now we know what artcc they are in, we cross reference what artccs are online
                            if self.artcc in CTR_controllers and self.artcc not in self.current_tracks.currenttracks[pilot["callsign"]]["pinged_artccs"]:
                                userid = await self.bot.fetch_user(item["user_id"])
                                
                                self.center_controller = CTR_controllers[self.artcc]
                            
                                message = await self.assemble_message()
                                self.current_tracks.currenttracks[pilot["callsign"]]["pinged_artccs"].append(self.artcc)
                                
                                with open("currenttracks.json", "w") as file:
                                    json.dump(self.current_tracks.currenttracks, file, indent=4)
                                
                                try:
                                    await userid.send(message)
                                except:
                                    pass
            except Exception as e:
                print(e)
                traceback.print_exc()
                            
            await asyncio.sleep(5)
    
    def start(self):
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self.loop())
            
    def stop(self):
        self.running=False

    def cancel(self):
        if self.task:
            self.task.cancel()
            
class DeletionLoop():
    def __init__(self, bot):
        self.trackloop = ActiveTrackLoop(bot)
        self.running = False
    
    async def loop(self):
        while self.running:
            
            self.vatsim_data = await self.trackloop.fetch_vatsim_data()
            
            current_tracks = read_or_create_file("currenttracks.json")
            current_tracksCopy = current_tracks.copy()
                
            for track, item in current_tracks.items():
                found = False
                for pilot in self.vatsim_data["pilots"]:
                    if pilot["callsign"] == track:
                        found = True
                if found == False:
                    del current_tracksCopy[track]
            
            with open("currenttracks.json", "w") as file:
                json.dump(current_tracksCopy, file, indent=4)
            
            await asyncio.sleep(3)
            
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
    
    deletionLoop = DeletionLoop(bot)
    deletionLoop.start()
    
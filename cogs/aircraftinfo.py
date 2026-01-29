import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
import aiohttp
from typing import Optional
import time
from datetime import datetime, timezone
import json

class AircraftInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("icao_airlines.json") as file:
            self.icao_airlines = json.load(file)
        
    @app_commands.command(name="aircraftinfo", description="Shows information about an aircraft - fill in one search")
    async def aircraftinfo(self,interaction: discord.Interaction, callsign: Optional[str] = None, cid: Optional[int] = None):
        if callsign and cid == None:
            vatsim_pilot_data = await utils.fetch_vatsim_api(callsign.upper())
            view = View(vatsim_pilot_data, self.icao_airlines)
            view.create_vatsimradar_button(vatsim_pilot_data)
            await interaction.response.send_message(view=view)
        elif cid and callsign == None:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://data.vatsim.net/v3/vatsim-data.json') as rawdata:
                    vatsim_pilot_data = await rawdata.json()
            for pilot in vatsim_pilot_data["pilots"]:
                if pilot["cid"] == cid:
                    vatsim_pilot_data = pilot
            view = View(vatsim_pilot_data, self.icao_airlines)
            view.create_vatsimradar_button(vatsim_pilot_data)
            await interaction.response.send_message(view=view)
        elif callsign and cid:
            failure_embed = discord.Embed(title="Please fill in one search")
            await interaction.response.send_message(embed=failure_embed)
            
class View(ui.LayoutView):
    def __init__(self, vatsim_pilot_data, icao_airlines):
        super().__init__()
        
        self.icao_airlines = icao_airlines
        self.vatsim_pilot_data = vatsim_pilot_data
        #start creating the container and all the info inside
        container = ui.Container()     
        #name of the guy and time elapsed
        time_online = utils.convert_time(vatsim_pilot_data["logon_time"])
        container.add_item(
            ui.TextDisplay(f"# Information about {vatsim_pilot_data["callsign"]} on VATSIM\n-# {vatsim_pilot_data["name"]} - {vatsim_pilot_data["cid"]} (Online {time_online})")
        )
        
        #now all the stuff
        
        airline_information = self.get_airline_data(vatsim_pilot_data["callsign"])
        container = self.add_to_containerDefaultFormat(container, "Callsign", "callsign", False, airline_information)
        container = self.add_to_containerDefaultFormat(container, "Aircraft Type", "aircraft_short", True, "")
        
        #position is special, i need to do two variables
        container.add_item(
            ui.TextDisplay(f"### Current Location\n{vatsim_pilot_data["latitude"]}, {vatsim_pilot_data["longitude"]}")
        )
        
        container = self.add_to_containerDefaultFormat(container, "Current Altitude", "altitude", False, "ft")
        
        container.add_item(
            ui.TextDisplay(f"## Flight Plan")
        )
        
        container.add_item(
            ui.TextDisplay(f"### Route\n{vatsim_pilot_data["flight_plan"]["departure"]} - {vatsim_pilot_data["flight_plan"]["arrival"]} (Alt {vatsim_pilot_data["flight_plan"]["alternate"]})")
        )
        
        container = self.add_to_containerDefaultFormat(container, "Filed Flight Plan Route", "route", True, "")
        container = self.add_to_containerDefaultFormat(container, "Filed Cruising Altitude", "altitude", True, "ft")
        
        
        self.add_item(container)
    def create_vatsimradar_button(self, vatsim_pilot_data):
        row = ui.ActionRow()
        row.add_item(ui.Button(label="View on Vatsim Radar", url=f"https://vatsim-radar.com/?pilot={vatsim_pilot_data["cid"]}"))
        
        self.add_item(row)
    def add_to_containerDefaultFormat(self, container, title, dict_key, in_flight_plan, extra_str):
        flight_plan = self.vatsim_pilot_data.get("flight_plan")
        if in_flight_plan == True:
            value = flight_plan.get(dict_key ,"None")
        else:
            value = self.vatsim_pilot_data[dict_key]
        container.add_item(
            ui.TextDisplay(f"### {title}\n{value}{extra_str}") 
        )
        return container
    def get_airline_data(self, callsign):
        icao_code = callsign[:3]
        for airline in self.icao_airlines["rows"]:
            if airline["icao"] == icao_code:
                airline_callsign = airline["callsign"]
                airline_name = airline["airline"]
                return_str = f" (**{airline_callsign}** - {airline_name})"
                return return_str
        return " - No Airline"
        
class utils():
    # static so we dont have to create a class variable
    @staticmethod
    async def fetch_vatsim_api(callsign):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://data.vatsim.net/v3/vatsim-data.json') as rawdata:
                data = await rawdata.json()
                pilot_data = None
                for pilot in data["pilots"]:
                    if pilot["callsign"] == callsign.upper():
                        pilot_data = pilot
                return pilot_data
    @staticmethod
    def convert_time(timestamp_raw):
        timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
        iso_timestamp = timestamp.timestamp()

        time_elapsed_secondsRAW = time.time() - iso_timestamp
        time_elapsed_seconds = int(time_elapsed_secondsRAW)
        floor_minutes_result = time_elapsed_seconds // 60
        if floor_minutes_result >= 60:
            hour_floor_result = floor_minutes_result // 60
            minute_modulo_result = floor_minutes_result % 60
            result_string = f"{hour_floor_result}h {minute_modulo_result}m"
            return result_string
        if floor_minutes_result < 60:
            result_string = f"{floor_minutes_result}m"
            return result_string

async def setup(bot):
    await bot.add_cog(AircraftInfo(bot))
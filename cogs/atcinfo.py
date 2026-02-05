from discord import app_commands
from discord.ext import commands
import discord
import aiohttp
from datetime import datetime,timezone
import time

class AtcInfo(commands.Cog):
    def __init__(self, bot):
        self.ratingdata = RatingData()
        self.aircraft_on_frequency = Aircraft_On_Frequency()
    
    @app_commands.command(name="atcinfo", description="Shows information about a controller online on the VATSIM network")
    async def atcinfo(self, interaction: discord.Interaction,  controller_callsign: str):
        controller_callsign = controller_callsign.upper()
        vatsimdata = await self.fetch_vatsim_API()
        foundcontroller = None
        for controller in vatsimdata["controllers"]:
            if controller["callsign"] == controller_callsign:
                foundcontroller = controller
        if foundcontroller:

            if foundcontroller["name"] == str(foundcontroller["cid"]):
                embed_description = str(foundcontroller["cid"]) + f"(**{self.ratingdata.ratingdata[foundcontroller["rating"]]}**)"
            else:
                embed_description = foundcontroller["name"] + f" - {str(foundcontroller["cid"])} (**{self.ratingdata.ratingdata[foundcontroller["rating"]]}**)"

            info_embed = discord.Embed(title=f"Information about {controller_callsign}", description=embed_description)
            info_embed.add_field(name="Frequency",value=f"**{foundcontroller["frequency"]}**")

            pilots_on_frequency = await self.aircraft_on_frequency.find_aircrafts_on_frequency(foundcontroller)
            info_embed.add_field(name="Pilots on Frequency", value=pilots_on_frequency, inline=False)
            
            #online time
            online_time = self.convert_time(foundcontroller["logon_time"])
            info_embed.add_field(name="Time Online", value=f"**{online_time}** - Elapsed", inline=False)

            text_atis_raw = foundcontroller["text_atis"]
            text_atis = "\n".join(text_atis_raw)
            info_embed.add_field(name="Text Atis", value=f"{text_atis}", inline=False)

            await interaction.response.send_message(embed=info_embed)            
        else:
            failure_embed = discord.Embed(title=f"{controller_callsign} is not currently on the network.", colour=discord.Colour.dark_magenta())
            await interaction.response.send_message(embed=failure_embed)

    async def fetch_vatsim_API(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://data.vatsim.net/v3/vatsim-data.json") as response:
                vatsimdata = await response.json()
        return vatsimdata
    
    def convert_time(self, timestamp_raw):
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
        
class Aircraft_On_Frequency():
    async def find_aircrafts_on_frequency(self, controller_Data):
        tranceiver_data = await self.retrieve_tranceiver_data()
                
        running_count = 0
        
        for tranceiver in tranceiver_data:
            added_to_count = False
            for individual_transceiver in tranceiver["transceivers"]:
                raw_frequency = str(individual_transceiver["frequency"])
                raw_frequency = raw_frequency[:6]
                frequency = raw_frequency[:3] + "." + raw_frequency[3:6]
                if individual_transceiver["id"] != 0 and added_to_count == False and frequency == controller_Data["frequency"]:
                    running_count += 1
                    added_to_count = True
                else:
                    pass
        
        running_count_str = str(running_count)
        return running_count_str
                
    async def retrieve_tranceiver_data(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://data.vatsim.net/v3/transceivers-data.json") as response:
                tranceiver_data = await response.json()
        return tranceiver_data
                
                
class RatingData():
    ratingdata = {
        2: "S1",
        3: "S2",
        4: "S3",
        5: "C1",
        7: "C3",
        8: "I1",
        10: "I3"
    }
    
async def setup(bot):
    await bot.add_cog(AtcInfo(bot))
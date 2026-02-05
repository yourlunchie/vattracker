import discord
from datetime import datetime,timezone
import time
import aiohttp

ratingdata = {
    2: "S1",
    3: "S2",
    4: "S3",
    5: "C1",
    7: "C3",
    8: "I1",
    10: "I3"
}

def atcinfocommand(bot):
    
    @bot.tree.command(name="atcinfo", description="Shows information about a controller online on the VATSIM network")
    async def atcinfo(interaction: discord.Interaction,  controller_callsign: str):
        controller_callsign = controller_callsign.upper()
        vatsimdata = await fetch_vatsim_API()
        foundcontroller = None
        for controller in vatsimdata["controllers"]:
            if controller["callsign"] == controller_callsign:
                foundcontroller = controller
        if foundcontroller:

            if foundcontroller["name"] == str(foundcontroller["cid"]):
                embed_description = str(foundcontroller["cid"]) + f"(**{ratingdata[foundcontroller["rating"]]}**)"
            else:
                embed_description = foundcontroller["name"] + f" - {str(foundcontroller["cid"])} (**{ratingdata[foundcontroller["rating"]]}**)"

            info_embed = discord.Embed(title=f"Information about {controller_callsign}", description=embed_description)
            info_embed.add_field(name="Frequency",value=f"**{foundcontroller["frequency"]}**")

            #online time
            online_time = convert_time(foundcontroller["logon_time"])
            info_embed.add_field(name="Time Online", value=f"**{online_time}** - Elapsed", inline=False)

            text_atis_raw = foundcontroller["text_atis"]
            text_atis = "\n".join(text_atis_raw)
            info_embed.add_field(name="Text Atis", value=f"{text_atis}", inline=False)

            await interaction.response.send_message(embed=info_embed)            
        else:
            failure_embed = discord.Embed(title=f"{controller_callsign} is not currently on the network.", colour=discord.Colour.dark_magenta())
            await interaction.response.send_message(embed=failure_embed)

    async def fetch_vatsim_API():
        async with aiohttp.ClientSession() as session:
            async with session.get("https://data.vatsim.net/v3/vatsim-data.json") as response:
                vatsimdata = await response.json()
        return vatsimdata
    
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
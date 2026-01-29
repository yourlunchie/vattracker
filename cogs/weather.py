import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

class Weather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="weather", description="Shows METAR data from an airport")
    async def weather(self, interaction: discord.Interaction, airport: str):
        weatherdatajson, status_code = await utils.fetch_weather_api(airport.upper())
        if status_code != 200:
            invalidairportembed = discord.Embed(title=f"{airport.upper()} is not an airport, or has no weather data.")
            await interaction.response.send_message(embed=invalidairportembed)
        else:
            weatherdata = weatherdatajson[0]
            weatherembed = discord.Embed(
                title=f"Weather data for {airport.upper()}",
                description=f"{weatherdata["name"]}, {weatherdata["lat"]}, {weatherdata["lon"]}",
                colour=discord.Color.dark_green()
            )
            weatherembed.add_field(name="Raw METAR", value=f"{weatherdata["rawOb"]}", inline=True)
            weatherembed.add_field(name="Flight Category", value=f"{weatherdata["fltCat"]}", inline=False)

            #winds and gusts
            gusts = weatherdata.get("wgst", None)
            if gusts is not None:
                weatherembed.add_field(name="Winds", value=f"{weatherdata["wdir"]}° at {weatherdata["wspd"]}kts, Gusting {weatherdata["wgst"]}kts", inline=False)
            else:
                weatherembed.add_field(name="Winds", value=f"{weatherdata["wdir"]}° at {weatherdata["wspd"]}kts", inline=False)
            
            #temperature and dew point
            weatherembed.add_field(name="Temperature", value=f"{round(weatherdata["temp"], 0)}°C", inline=True)
            weatherembed.add_field(name="Dew Point", value=f"{round(weatherdata["dewp"], 0)}°C", inline=True)

            #clouds
            cloudembedvalue = ""
            clouds_check = weatherdata.get("clouds", None)
            clouds_check_length = len(clouds_check)
            if clouds_check_length == 0:
                weatherembed.add_field(name="Clouds", value="No Clouds", inline=False)
            else:
                for clouds in weatherdata["clouds"]:
                    cloudcover = clouds["cover"]
                    cloudbase = clouds["base"]
                    cloudembedvalue += f"{cloudcover} at {cloudbase}ft, "
                cloudembedvalue[:-2]
                weatherembed.add_field(name="Clouds", value=cloudembedvalue, inline=False)

            # inhg altimeter math
            inhgaltimeterunrounded = weatherdata["altim"] * 0.029529983071445
            inhgaltimeter = round(inhgaltimeterunrounded, 2)
            finalinhg = str(inhgaltimeter)
            if len(finalinhg) == 4:
                finalinhg += "0"
            # HPA altimeter rounding
            hparounded = round(int(weatherdata["altim"]), 0)
            hparoundedstr = str(hparounded)
            #altimeter input
            weatherembed.add_field(name="Altimeter - inHG", value=f"{finalinhg}", inline=True)
            weatherembed.add_field(name="Altimeter - hPA", value=f"{hparoundedstr}", inline=True)

            await interaction.response.send_message(embed=weatherembed)
    
class utils():
    @staticmethod
    async def fetch_weather_api(airport):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://aviationweather.gov/api/data/metar?ids={airport.upper()}&format=json") as response:
                datajson = await response.json()
                status = response.status
                return datajson, status

async def setup(bot):
    await bot.add_cog(Weather(bot))
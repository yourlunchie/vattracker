import discord
from dotenv import load_dotenv
import asyncio
from discord.ext import commands
import os
import requests
import logging
from discord import app_commands
from typing import Optional
import activetrackfile

load_dotenv(".env")
token = os.getenv("DISCORD_TOKEN")
ownerrole = "owner"
guildid = 1397781715879071894

logging.basicConfig(filename="discord.log", level=logging.DEBUG)
intents = discord.Intents.default()
Guild = discord.Object(id=guildid)

bot = commands.Bot(command_prefix="/", intents=intents)

activetrackfile.activetrackcommand(bot)

@bot.event
async def on_ready():
    print(f"VatTracker is ready to operate!")
    channel_id = 1397850913368051712
    channel = bot.get_channel(channel_id)
    await bot.tree.sync()
    activetrackfile.starttrackloop(bot)
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

@bot.tree.command(name="weather", description="Shows METAR data from an airport", guild=Guild)
async def weather(interaction: discord.Interaction, airport: str):
    weatherwebsite = (f"https://aviationweather.gov/api/data/metar?ids={airport.upper()}&format=json")
    weatherdataraw = requests.get(weatherwebsite)
    if requests.get(weatherwebsite).status_code != 200:
        invalidairportembed = discord.Embed(title=f"{airport.upper()} is not an airport, or has no weather data.")
        await interaction.response.send_message(embed=invalidairportembed)
    else:
        weatherdatajson = weatherdataraw.json()
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
        weatherembed.add_field(name="Temperature", value=f"{weatherdata["temp"]}°", inline=True)
        weatherembed.add_field(name="Dew Point", value=f"{weatherdata["dewp"]}°", inline=True)

        #clouds
        cloudembedvalue = ""
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
        # HPA altimeter rounding
        hparounded = round(int(weatherdata["altim"]), 0)
        hparoundedstr = str(hparounded)
        #altimeter input
        weatherembed.add_field(name="Altimeter - inHG", value=f"{finalinhg}", inline=True)
        weatherembed.add_field(name="Altimeter - hPA", value=f"{hparoundedstr}", inline=True)


        await interaction.response.send_message(embed=weatherembed)
        

@bot.tree.command(name="aircraftinfo", description="Shows information about an aircraft - fill in one search")
async def aircraftinfo(interaction: discord.Interaction, callsign:Optional[str] = None, cid:Optional[str] = None):
    #aircraftinfo was changed from /info cuz of stupid rhythm
    if callsign is None and cid is None:
        nocidorcallsignembed = discord.Embed(title="No CID or callsign input", description="Please input either a CID or callsign")
        await interaction.response.send_message(embed=nocidorcallsignembed)
    elif callsign is not None and cid is not None:
        bothcidandcallsignembed = discord.Embed(title="Both fields are filled in, please only fill in one")
        await interaction.response.send_message(embed=bothcidandcallsignembed)
    else:
        rawdata = requests.get('https://data.vatsim.net/v3/vatsim-data.json')
        data = rawdata.json()
        found_pilot = None
        if callsign is not None:
            for pilot in data["pilots"]:
                if pilot["callsign"].upper() == callsign.upper():
                    found_pilot = pilot
                    break
        elif cid is not None:
            for pilot in data["pilots"]:
                if pilot["cid"] == int(cid):
                    found_pilot = pilot
                    break
        if found_pilot: 
            flight_plan = found_pilot.get("flight_plan", {})
            longitude = found_pilot.get("longitude", {}) # done
            latitude = found_pilot.get("latitude", {}) # done
            realalt = found_pilot.get("altitude", {}) # done
            pilotname = found_pilot.get("name", {}) # done
            pilotCID = found_pilot.get("cid", {}) # done
            cruisespeed = flight_plan["cruise_tas"] # done
            longtype = flight_plan["aircraft_faa"] # done
            type = flight_plan["aircraft_short"] # done
            filedalt = flight_plan["altitude"] # done
            route = flight_plan["route"] # done
            depairport = flight_plan["departure"] # done
            ariairport = flight_plan["arrival"] # done

            # redefine callsign so i can use it for embed making
            callsign1 = found_pilot.get("name", {})
            
            # info collection done, now i format the embed

            infoembed = discord.Embed(
                title=f"Information about **{callsign1.upper()}**'s flight on VATSIM",
                description=f"{pilotname} - {pilotCID}",
                color=discord.Color.dark_purple()
            )
            infoembed.add_field(name=f"Callsign", value=f"{callsign1.upper()}", inline=True)
            infoembed.add_field(name=f"Aircraft Type", value=f"{type}", inline=True)
            infoembed.add_field(name=f"Aircraft Type - FAA", value=f"{longtype}", inline=True)
            infoembed.add_field(name=f"Route", value=f"{depairport} - {ariairport}", inline=True)
            infoembed.add_field(name=f"Filed Altitude", value=f"{filedalt}ft", inline=True)
            infoembed.add_field(name=f"Cruise Speed", value=f"{cruisespeed}kts", inline=True)
            infoembed.add_field(name=f"Filed Route", value=f"{route}", inline=False)
            infoembed.add_field(name=f"Longitude", value=f"{longitude}", inline=True)
            infoembed.add_field(name=f"Latitude", value=f"{latitude}", inline=True)
            infoembed.add_field(name=f"Real Altitude", value=f"{realalt}ft", inline=True)

            #the info embed is filled in and defined
            
            await interaction.response.send_message(embed=infoembed)
        else:
            if callsign is not None:
                noaircraftembed = discord.Embed(
                    title=f"No aircraft found",
                    description=f"{callsign.upper()} is not currently on the network."
                )
                await interaction.response.send_message(embed=noaircraftembed)
            elif cid is not None:
                cidstr = str(cid)
                noaicraftembedcid = discord.Embed(
                    title=f"No aicraft found",
                    description=f"{cidstr} is not currently on the network."
                )
                await interaction.response.send_message(embed=noaicraftembedcid)

@bot.tree.command(name="arrivalboard", description="Show arrivals at an airport",guild=Guild)
async def arrivalboard(interaction: discord.Interaction, airport: str):
    arrivalcounter = 0
    if len(airport) > 4 or len(airport) < 4:

        invalidembed = discord.Embed(
            title=f"Invalid ICAO Code",
            description=f"{airport} is not a valid ICAO code. Please input a **valid**, **4-letter** ICAO code.",
            color=discord.Color.blue()
        )
        invalidembed.set_footer(text=f"Executed by {interaction.user}")
        await interaction.response.send_message(embed=invalidembed)
        return
    else: 
        
        airportlist = requests.get("https://raw.githubusercontent.com/mwgg/Airports/refs/heads/master/airports.json")
        airportlistdata = airportlist.json()
        # get the list into a json variable

        if airport.upper() not in airportlistdata:
            unrealairportembed = discord.Embed(
                title=f"{airport.upper()} is not a real airport.",
                color=discord.Color.dark_blue()
                )
            unrealairportembed.set_footer(text=f"Executed by {interaction.user}")
            await interaction.response.send_message(embed=unrealairportembed)
            return
       
        if airport.upper() in airportlistdata:
            foundairport = airportlistdata[airport.upper()]
            airportname = foundairport.get("name", "Unknown Airport")

        rawdata = requests.get('https://data.vatsim.net/v3/vatsim-data.json')
        data = rawdata.json()
        arrivals = []
        # define the embeds
        embed = discord.Embed(
            title=f"{airport}'s Arrivals - Page 1",
                description=f"Current arrivals at **{airport}** - {airportname}",
                color=discord.Color.blue()
        )
        embed.set_footer(text=f"Executed by {interaction.user}")
        embed2 = discord.Embed(
            title=f"{airport}'s Arrivals - Page 2",
                description=f"Current arrivals at **{airport}** - {airportname}",
                color=discord.Color.blue()
        )
        embed2.set_footer(text=f"Page 2")
        embed3 = discord.Embed(
            title=f"{airport}'s Arrivals - Page 3",
                description=f"Current arrivals at **{airport}** - {airportname}",
                color=discord.Color.blue()
        )
        embed3.set_footer(text=f"Page 3")
        embed4 = discord.Embed(
            title=f"{airport}'s Arrivals - Page 4",
                description=f"Current arrivals at **{airport}** - {airportname}",
                color=discord.Color.blue()
        )
        # embed defining done

        for pilot in data["pilots"]:
            pilot_flightplan = pilot.get("flight_plan", None)
            if pilot_flightplan is not None:
                if airport.upper() == pilot_flightplan.get("arrival", ""):
                    arrivals.append(pilot)
        for pilot in arrivals:
            callsigns = pilot.get("callsign", "")
            departureairport = pilot.get("flight_plan").get("departure", "")
            if arrivalcounter < 24:
                embed.add_field(name=f"{callsigns}", value=f"{departureairport.upper()} - {airport.upper()}", inline=True)
                arrivalcounter += 1
            elif arrivalcounter < 48:
                embed2.add_field(name=f"{callsigns}", value=f"{departureairport.upper()} - {airport.upper()}", inline=True)
                arrivalcounter += 1
            elif arrivalcounter < 72:
                embed3.add_field(name=f"{callsigns}", value=f"{departureairport.upper()} - {airport.upper()}", inline=True)
                arrivalcounter += 1
            elif arrivalcounter < 96:
                embed4.add_field(name=f"{callsigns}", value=f"{departureairport.upper()} - {airport.upper()}", inline=True)
                arrivalcounter +=1
            elif arrivalcounter >= 96:
                break

        if arrivals:
            await interaction.response.send_message(embed=embed)

            if arrivalcounter >= 24:
                await interaction.followup.send(embed=embed2)
            if arrivalcounter >= 48:
                await interaction.followup.send(embed=embed3)
            if arrivalcounter >= 72:
                await interaction.followup.send(embed=embed4)
            if arrivalcounter >= 96:
                unshownarrivals = len(arrivals) - arrivalcounter
                embed4.set_footer(text=f"{unshownarrivals} remaining flights are not shown - Page 4")
                await interaction.followup.send(embed=embed4)
            return
        else:
            noarrivalembed = discord.Embed(
                        title=f"No current arrivals at {airport.upper()} - {airportname}",
                            description=f"There are no arrivals at {airport.upper()}",
                            color=discord.Color.dark_blue()
                    )
            noarrivalembed.set_footer(text=f"Executed by {interaction.user}")
            await interaction.response.send_message(embed=noarrivalembed)
            print(arrivals)
            return

@bot.tree.command(name="departureboard", description="Show current VATSIM departures from an airport")
@app_commands.describe(airport="4-letter ICAO code")
async def departureboard(interaction: discord.Interaction, airport: str):
    departurecounter = 0

    if len(airport) != 4:
        invalidembed = discord.Embed(
            title="Invalid ICAO Code",
            description=f"{airport} is not a valid ICAO code. Please input a **valid**, **4-letter** ICAO code.",
            color=discord.Color.blue()
        )
        invalidembed.set_footer(text=f"Executed by {interaction.user}")
        await interaction.response.send_message(embed=invalidembed)
        return

    airportlist = requests.get(
        "https://raw.githubusercontent.com/mwgg/Airports/refs/heads/master/airports.json"
    )
    airportlistdata = airportlist.json()

    if airport.upper() not in airportlistdata:
        unrealairportembed = discord.Embed(
            title=f"{airport.upper()} is not a real airport.",
            color=discord.Color.dark_blue()
        )
        unrealairportembed.set_footer(text=f"Executed by {interaction.user}")
        await interaction.response.send_message(embed=unrealairportembed)
        return

    foundairport = airportlistdata[airport.upper()]
    airportname = foundairport.get("name", "Unknown Airport")

    rawdata = requests.get("https://data.vatsim.net/v3/vatsim-data.json")
    data = rawdata.json()
    departures = []

    # define embeds
    embed = discord.Embed(
        title=f"{airport.upper()}'s Departures - Page 1",
        description=f"Current departures from **{airport.upper()}** - {airportname}",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Executed by {interaction.user}")

    embed2 = discord.Embed(
        title=f"{airport.upper()}'s Departures - Page 2",
        description=f"Current departures from **{airport.upper()}** - {airportname}",
        color=discord.Color.blue()
    )
    embed2.set_footer(text="Page 2")

    embed3 = discord.Embed(
        title=f"{airport.upper()}'s Departures - Page 3",
        description=f"Current departures from **{airport.upper()}** - {airportname}",
        color=discord.Color.blue()
    )
    embed3.set_footer(text="Page 3")

    embed4 = discord.Embed(
        title=f"{airport.upper()}'s Departures - Page 4",
        description=f"Current departures from **{airport.upper()}** - {airportname}",
        color=discord.Color.blue()
    )

    # collect departures
    for pilot in data["pilots"]:
        pilot_flightplan = pilot.get("flight_plan", None)
        if pilot_flightplan is not None:
            if airport.upper() == pilot_flightplan.get("departure", ""):
                departures.append(pilot)

    for pilot in departures:
        callsigns = pilot.get("callsign", "")
        arrivalairport = pilot.get("flight_plan").get("arrival", "")

        if departurecounter < 24:
            embed.add_field(
                name=callsigns,
                value=f"{airport.upper()} - {arrivalairport.upper()}",
                inline=True
            )
            departurecounter += 1
        elif departurecounter < 48:
            embed2.add_field(
                name=callsigns,
                value=f"{airport.upper()} - {arrivalairport.upper()}",
                inline=True
            )
            departurecounter += 1
        elif departurecounter < 72:
            embed3.add_field(
                name=callsigns,
                value=f"{airport.upper()} - {arrivalairport.upper()}",
                inline=True
            )
            departurecounter += 1
        elif departurecounter < 96:
            embed4.add_field(
                name=callsigns,
                value=f"{airport.upper()} - {arrivalairport.upper()}",
                inline=True
            )
            departurecounter += 1
        elif departurecounter >= 96:
            break

    if departures:
        # first response
        await interaction.response.send_message(embed=embed)

        if len(departures) >= 24:
            await interaction.followup.send(embed=embed2)
        if len(departures) >= 48:
            await interaction.followup.send(embed=embed3)
        if len(departures) >= 72:
            await interaction.followup.send(embed=embed4)

        if len(departures) >= 97:
            unshowndepartures = len(departures) - departurecounter
            embed4.set_footer(
                text=f"{unshowndepartures} remaining flights are not shown - Page 4"
            )
        return

    else:
        nodepartureembed = discord.Embed(
            title=f"No current departures from {airport.upper()} - {airportname}",
            description=f"There are no departures from {airport.upper()}",
            color=discord.Color.dark_blue()
        )
        nodepartureembed.set_footer(text=f"Executed by {interaction.user}")
        await interaction.response.send_message(embed=nodepartureembed)
        print(departures)
        return


bot.run(token)
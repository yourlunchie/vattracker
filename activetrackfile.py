import discord
from discord import app_commands
from discord.ext import commands
from shapely.geometry import shape, Point
import json
from discord.ext import tasks
import parseaustraliasectors
import aiohttp

from utils import read_or_create_file

guildid = 1397781715879071894
Guild = discord.Object(id=guildid)

artccpolygons = []

with open("Boundaries.geojson", "r") as file:
    boundariesraw = json.load(file)
with open ("icaotoartccfir.json", "r") as file:
    icaotoartcc = json.load(file)

for features in boundariesraw["features"]:
    artccpolygons.append({"name": features["properties"]["id"], "polygon": shape(features["geometry"]), "oceanic": features["properties"]["oceanic"]})

def activetrackcommand(bot):
    # run this in main.py so command gets ran

    @bot.tree.command(name="activetrack", description="Tracks your aircraft on the network, and DMs you if entering an active ARTCC/FIR")
    async def activetrack(interaction: discord.Interaction, callsign: str):
        currenttracks = read_or_create_file("currenttracks.json")
        currenttracks[callsign.upper()] = {
            "discord_channel": interaction.channel_id,
            "user_id": interaction.user.id,
            "pinged_artccs": []
        }
        with open("currenttracks.json", "w") as file:
            json.dump(currenttracks, file, indent=4)      
        trackingbegunembed = discord.Embed(title=f"Begun tracking for {callsign.upper()}")
        await interaction.response.send_message(embed=trackingbegunembed)

    @bot.tree.command(name="removeactivetrack", description="Removes activetrack from an aircraft")
    async def removeactivetrack(interaction: discord.Interaction, callsign: str):
        aircraftexist = False
        tracks = read_or_create_file("currenttracks.json")
        tracks_copy = tracks.copy()
        userid = interaction.user.id
        if tracks[callsign.upper()]["user_id"] == userid:
            aircraftexist = True
        if aircraftexist == True:
            del tracks_copy[callsign.upper()]
            deletionembed = discord.Embed(title=f"Tracking stopped for **{callsign.upper()}**")
            await interaction.response.send_message(embed=deletionembed)
            with open("currenttracks.json", "w") as file:
                json.dump(tracks_copy, file)
        else:
            failembed = discord.Embed(title=f"You are not the person who intiated the track for **{callsign.upper()}**, or no track was initiated in the first place.")
            await interaction.response.send_message(embed=failembed)


def starttrackloop(bot):
    @tasks.loop(seconds=10)
    async def trackloop():
        tracksdata = read_or_create_file("currenttracks.json")
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://data.vatsim.net/v3/vatsim-data.json") as response:
                vatsimdata = await response.json()

        for callsign, track in tracksdata.items():
            try:
                # always do TWO variables after "for" for any dictionaries, and put .items() - the first variable is the DICTIONARY KEY
                foundtrack = False
                vatusa_callsign = False
                londoncallsign = False
                asiancallsign = False
                vatpaccallsign = False
                isshanwickganderoceanic = False
                newyorkoceanic = False
                iscanada = False
                is_scottishcontrol = False

                userid = await bot.fetch_user(track["user_id"])

                for pilots in vatsimdata["pilots"]:
                    if callsign == pilots["callsign"]:
                        foundtrack = pilots
                        break
                if foundtrack:
                    latitude = foundtrack["latitude"]
                    longitude = foundtrack["longitude"]
                    point = Point(longitude, latitude)
                    for polygon in artccpolygons:
                        if point.within(polygon["polygon"]):
                            foundartcc = polygon["name"]
                            if foundartcc[:4] in track["pinged_artccs"]:
                                break
                                # stop program as ARTCC/FIR has been pinged already
                            else:
                                if foundartcc[:4] in icaotoartcc["america"]:
                                    # its america
                                    if foundartcc == "KZNY" and polygon["oceanic"] == "1":
                                        # it is KZNY oceanic sector
                                        newyorkoceanic = True
                                    else:
                                        foundartcc = foundartcc[:4]
                                        vatusa_CTR_callsign = icaotoartcc["america"][foundartcc][0]["identifier"]
                                        vatusa_callsign = True

                                elif foundartcc.startswith("Y"):
                                    # its australia
                                    australiasectors =  await parseaustraliasectors.parseaustraliasectors()
                                    vatpaccallsign = True
                                elif foundartcc.startswith("EGTT"):
                                    # its LONDON control
                                    londoncallsignstr = icaotoartcc["london"][foundartcc]["identifier"]
                                    londoncallsign = True
                                elif foundartcc.startswith("EGPX"):
                                    # its scottish control
                                    is_scottishcontrol = True
                                elif foundartcc == "EGGX" or foundartcc == "CZQO":
                                    isshanwickganderoceanic = True
                                elif foundartcc[:4] in icaotoartcc["canada"]:
                                    iscanada = True
                                    canada_CTR_callsign = icaotoartcc["canada"][foundartcc]["identifier"]
                                # check if they're in an asian FIR as they start with different stuff
                                elif foundartcc[:4] in icaotoartcc["specialasia"]:
                                    asiancallsign = True
                                
                                for onlineatc in vatsimdata["controllers"]:

                                    if vatusa_callsign == True:
                                            atccallsign = onlineatc["callsign"]
                                            parsedcallsign = atccallsign[:3] + atccallsign[-4:] # this is the onlineatc
                                            if vatusa_CTR_callsign == parsedcallsign:
                                                message = await controller_counter_function(vatusa_CTR_callsign, callsign, onlineatc, userid, False)
                                                # i get the data about the pilot and send a DM
                                                await userid.send(message)
                                                artccappend = foundartcc[:4]
                                                tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                                with open("currenttracks.json", "w") as file:
                                                    json.dump(tracksdata, file)
                                                return
                                    
                                    elif newyorkoceanic == True:
                                        if onlineatc["callsign"] == "NY_CL_FSS":
                                            message = f"<@{userid.id}>, your flight **{callsign}** is entering **{onlineatc["callsign"]}** - New York Oceanic Radio."
                                            await userid.send(message)
                                            artccappend = foundartcc[:4]
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
                                            return                                                                      

                                    elif londoncallsign == True:
                                        if onlineatc["callsign"] == londoncallsignstr:
                                            # i do not need the whole "how many controllers per sector" there is, because this inherently tracks split sectors of london, which can only 1 have controller
                                            message = f"<@{userid.id}>, your flight **{callsign}** is entering **{onlineatc["callsign"]}** - {icaotoartcc["london"][foundartcc]["callsign"]} ({onlineatc["frequency"]})."
                                            await userid.send(message)
                                            artccappend = foundartcc[:4]
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
                                            return    
                                                                            
                                    elif is_scottishcontrol == True:
                                        if onlineatc["callsign"] == icaotoartcc["scottish"][foundartcc]["identifier"]:
                                            # since EGPX is a seperate thingy in boundaries.geojson, again no need for sector controllers because its inherently a sector, and it will still work if scottish opens as one
                                            # as it goes through each one and each identifier callsign
                                            message = f"<@{userid.id}>, your flight **{callsign}** is entering **{onlineatc["callsign"]}** - {icaotoartcc["scottish"][foundartcc]["callsign"]} ({onlineatc["frequency"]})."
                                            await userid.send(message)
                                            artccappend = foundartcc[:4]
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
                                            return                                                
                                    
                                    elif vatpaccallsign == True:
                                        # i get the data about the pilot and send a DM
                                        # once i get the list from here, i run for X in list, then check if the artcc is in that found list with regex
                                        # i dont use onlineatc here, as i have a seperate .py file which gives ALL sectors in australia
                                        for sector in australiasectors:
                                            if sector == foundartcc[1:4]:
                                                message = f"<@{userid.id}>, your flight **{callsign}** is entering **{foundartcc}**."
                                                await userid.send(message)
                                                artccappend = foundartcc[:4] 
                                                tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                                with open("currenttracks.json", "w") as file:
                                                    json.dump(tracksdata, file)
                                                return
                                    
                                    elif asiancallsign == True:
                                        foundartcc = foundartcc[:4]
                                        atccallsign = onlineatc["callsign"]
                                        parsedcallsign = atccallsign[:3] + atccallsign[-4:]
                                        asian_CTR_callsign = icaotoartcc["specialasia"][foundartcc]["identifier"]
                                        # makes it easier to hunt the icaotoartcc dict
                                        if asian_CTR_callsign == parsedcallsign:
                                            message = await controller_counter_function(asian_CTR_callsign, callsign, onlineatc, userid, False)
                                            await userid.send(message)
                                            artccappend = foundartcc[:4]
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
                                            return                                                             

                                    elif isshanwickganderoceanic == True:
                                        if icaotoartcc["shanwickgander"][foundartcc]["identifier"] == onlineatc["callsign"]:
                                            message = f"<@{userid.id}>, your flight **{callsign}** is entering **{onlineatc["callsign"]}** - {icaotoartcc["shanwickgander"][foundartcc]["callsign"]}."
                                            await userid.send(message)
                                            artccappend = foundartcc[:4] 
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
                                            return
                                        
                                    elif iscanada == True:
                                        foundartcc = foundartcc[:4]
                                        atccallsign = onlineatc["callsign"]
                                        atc_callsign_parsed = atccallsign[:3] + atccallsign[-4:]
                                        if atc_callsign_parsed == canada_CTR_callsign:
                                            message = await controller_counter_function(canada_CTR_callsign, callsign, onlineatc, userid, False)
                                            await userid.send(message)
                                            artccappend = foundartcc[:4] 
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
                                            return                                        

                                    else:
                                        # if its a ARTCC/FIR starting with its ICAOdesignator and doesnt fulfill any special conditions
                                        if onlineatc["callsign"].startswith(foundartcc[:4]) and onlineatc["callsign"].endswith("_CTR"):
                                            # loop through vatsimdata to see how many controllers are online in 1 ARTCC/FIR - if theres more than one, the bot cannot get the correct frequency 100%, which is pretty bad
                                            center_callsign = foundartcc[:4] + "_CTR"
                                            message = await controller_counter_function(center_callsign, callsign, onlineatc, userid, True) 
                                            await userid.send(message)
                                            artccappend = foundartcc[:4] 
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
            
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"oop i broke {callsign, None}, {foundartcc, None}, {e}")
                continue

    async def controller_counter_function(CTR_callsign, callsign, atc, id, is_4letterICAO): # callsign and onlineatc are input here as accepted data
        async with aiohttp.ClientSession() as session:
            async with session.get("https://data.vatsim.net/v3/vatsim-data.json") as rawdata:
                vatsimdata = await rawdata.json()
        controller_counter = 0
        for controller in vatsimdata["controllers"]:
            if is_4letterICAO == True:
                parsed_callsign_loop = controller["callsign"][:4] + "_CTR"
            else:
                parsed_callsign_loop = controller["callsign"][:3] + controller["callsign"][-4:]
            if CTR_callsign == parsed_callsign_loop:
                controller_counter += 1
        if controller_counter == 1:
            DM_message = f"<@{id.id}>, your flight **{callsign}** is entering **{atc["callsign"]}** ({atc["frequency"]})."
        else:
            DM_message = f"<@{id.id}>, your flight **{callsign}** is entering **{CTR_callsign}**."
        return DM_message

    @tasks.loop(seconds=30)
    async def deletionloop():
        async with aiohttp.ClientSession() as session:
            async with session.get("https://data.vatsim.net/v3/vatsim-data.json") as response:
                vatsimdata = await response.json()
                
        trackdata = read_or_create_file("currenttracks.json")
        trackdata_copy = trackdata.copy()
        for aircraft, items in trackdata.items():
            still_online = False
            for callsign in vatsimdata["pilots"]:
                aircraftcallsign = callsign["callsign"]
                if aircraft == aircraftcallsign:
                    still_online = True
            if still_online == False:
                del trackdata_copy[aircraft]
            with open("currenttracks.json", "w") as file:
                json.dump(trackdata_copy, file)

    trackloop.start()
    deletionloop.start()

# point = Point(-79.10762, 42.04464)

# for artcc in artccpolygons:
    # if artcc["name"] == "KZOB":
        # if point.within(artcc["polygon"]):
            # print("this works")


# legendary moment preserved for history

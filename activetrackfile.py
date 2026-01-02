import discord
from discord import app_commands
from discord.ext import commands
from shapely.geometry import shape, Point
import json
from discord.ext import tasks
import requests
import parseaustraliasectors

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
        with open("currenttracks.json", "r") as file:
            currenttracks = json.load(file)
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
        with open("currenttracks.json", "r") as file:
            tracks = json.load(file)
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
        with open("currenttracks.json", "r") as file:
            tracksdata = json.load(file)
        
        vatsimdata = requests.get("https://data.vatsim.net/v3/vatsim-data.json").json()

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
                                    if foundartcc == "KZNY":
                                        # its new york i have to see if its new york center or radio
                                        if polygon["oceanic"] == "1":                                        
                                            #checking if its NEW YORK OCEANIC
                                            newyorkoceanic = True
                                        else:
                                            # if its just new york center we proceed as normal
                                            foundartcc = foundartcc[:4]
                                            diffvatusacentercallsign = icaotoartcc["america"][foundartcc][0]["identifier"]
                                            vatusa_callsign = True                            
                                    else:
                                        foundartcc = foundartcc[:4]
                                        diffvatusacentercallsign = icaotoartcc["america"][foundartcc][0]["identifier"]
                                        vatusa_callsign = True

                                elif foundartcc.startswith("Y"):
                                    # its australia
                                    australiasectors =  await parseaustraliasectors.parseaustraliasectors()
                                    vatpaccallsign = True
                                elif foundartcc.startswith("EGTT-"):
                                    # its LONDON control
                                    londoncallsignstr = icaotoartcc["london"][foundartcc]["identifier"]
                                    londoncallsign = True
                                elif foundartcc == "EGGX" or foundartcc == "CZQO":
                                    isshanwickganderoceanic = True
                                elif foundartcc == "CZYZ":
                                    # its czyz rn cuz to my knowledge other canadian FIRs use XXXX_CTR
                                    iscanada = True
                                # check if they're in an asian FIR as they start with different stuff
                                for fir in icaotoartcc["specialasia"]:
                                    if foundartcc[:4] == fir:
                                        asiancallsign = True
                                
                                for onlineatc in vatsimdata["controllers"]:
                                    
                                    if vatusa_callsign == True:
                                        atccallsign = onlineatc["callsign"]
                                        parsedcallsign = atccallsign[:3] + atccallsign[-4:]
                                        if diffvatusacentercallsign == parsedcallsign:
                                            # i get the data about the pilot and send a DM
                                            userid = await bot.fetch_user(track["user_id"])
                                            message = f"<@{userid.id}>, your flight **{callsign}** is entering **{onlineatc["callsign"]}** - {icaotoartcc["america"][foundartcc][0]["callsign"]}."
                                            await userid.send(message)
                                            artccappend = foundartcc[:4]
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
                                            return
                                    
                                    elif newyorkoceanic == True:
                                        if onlineatc["callsign"] == "NY_CL_FSS":
                                            userid = await bot.fetch_user(track["user_id"])
                                            message = f"<@{userid.id}>, your flight **{callsign}** is entering **{onlineatc["callsign"]}** - New York Oceanic Radio."
                                            await userid.send(message)
                                            artccappend = foundartcc[:4]
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
                                            return                                                                      


                                    elif londoncallsign == True:
                                        if onlineatc["callsign"] == londoncallsignstr:
                                            userid = await bot.fetch_user(track["user_id"])
                                            message = f"<@{userid.id}>, your flight **{callsign}** is entering **{onlineatc["callsign"]}** - {icaotoartcc["london"][foundartcc]["callsign"]}."
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
                                                userid = await bot.fetch_user(track["user_id"])
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
                                        # makes it easier to hunt the icaotoartcc dict
                                        if icaotoartcc["specialasia"][foundartcc]["identifier"] == parsedcallsign:
                                            userid = await bot.fetch_user(track["user_id"])
                                            message = f"<@{userid.id}>, your flight **{callsign}** is entering **{onlineatc["callsign"]}** - {icaotoartcc["specialasia"][foundartcc]["callsign"]}."
                                            await userid.send(message)
                                            artccappend = foundartcc[:4]
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
                                            return                                        

                                    elif isshanwickganderoceanic == True:
                                        if icaotoartcc["shanwickgander"][foundartcc]["identifier"] == onlineatc["callsign"]:
                                            userid = await bot.fetch_user(track["user_id"])
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
                                        parsedcallsign = atccallsign[:3] + atccallsign[-4:]                                    
                                        if icaotoartcc["canada"][foundartcc]["identifier"] == parsedcallsign:
                                            userid = await bot.fetch_user(track["user_id"])
                                            message = f"<@{userid.id}>, your flight **{callsign}** is entering **{onlineatc["callsign"]}** - {icaotoartcc["canada"][foundartcc]["callsign"]}."
                                            await userid.send(message)
                                            artccappend = foundartcc[:4] 
                                            tracksdata[callsign]["pinged_artccs"].append(artccappend)
                                            with open("currenttracks.json", "w") as file:
                                                json.dump(tracksdata, file)
                                            return                                        

                                    else:
                                        # if its a ARTCC/FIR starting with its ICAOdesignator and doesnt fulfill any special conditions
                                        if onlineatc["callsign"].startswith(foundartcc[:4]) and onlineatc["callsign"].endswith("_CTR"):
                                            # i get the data about the pilot and send a DM
                                            userid = await bot.fetch_user(track["user_id"])
                                            message = f"<@{userid.id}>, your flight **{callsign}** is entering **{onlineatc["callsign"]}**."
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

    @tasks.loop(seconds=30)
    async def deletionloop():
        vatsimdata = requests.get("https://data.vatsim.net/v3/vatsim-data.json").json()
        with open("currenttracks.json", "r") as file:
            trackdata = json.load(file)
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

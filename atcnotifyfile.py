import discord
import json
from discord import app_commands
from typing import Optional
from discord.ext import tasks
import aiohttp

from utils import read_or_create_file

artccpolygons = {}
with open("Boundaries.geojson", "r") as file:
    raw_boundary_data = json.load(file)

for feature in raw_boundary_data["features"]:
    artccpolygons[feature["properties"]["id"]] = {
        "identifier": feature["properties"]["id"]
    }

with open("icaotoartccfir.json", "r") as file:
    icao_to_artccJSON = json.load(file)

def atcnotifycommands(bot):

    @bot.tree.command(name="atcnotify", description="DMs you when an ATC comes online. Optionally notify a channel.")
    @app_commands.describe(input="Input a CALLSIGN of any ATC.")
    async def atcnotify(interaction: discord.Interaction, input: str, channel_id: Optional[str] = None):
        current_notify_list = read_or_create_file("currentnotifylist.json")
        current_notify_list[str(interaction.user.id) + input] = {
            "atc_id": input.upper(),
            "user_id": interaction.user.id,
            "channel_id": channel_id,
            "pinged": False
        }
        if current_notify_list[str(interaction.user.id) + input]["channel_id"] == None:
            success_embed = discord.Embed(title=f"Success! You will be DMed if {input} comes online.")
        else:
            success_embed = discord.Embed(title=f"Success! Your channel will be notified if {input} comes online.")
        await interaction.response.send_message(embed=success_embed)
        with open("currentnotifylist.json", "w") as file:
            json.dump(current_notify_list, file)
    
    @bot.tree.command(name="removeatcnotify", description="Stop getting DMs/notifications if an ATC online.")
    @app_commands.describe(input="Input a CALLSIGN of any ATC.")
    async def removeatcnotify(interaction: discord.Interaction, input: str):
        current_notify_list = read_or_create_file("currentnotifylist.json")
        current_notify_list_copy = current_notify_list.copy()
        parsed_key = str(interaction.user.id) + input
        if parsed_key in current_notify_list:
            del current_notify_list_copy[parsed_key]
            success_embed = discord.Embed(title=f"Success! You will not get a DM/notification for {input}")
            await interaction.response.send_message(embed=success_embed)
            with open("currentnotifylist.json", "w") as file:
                json.dump(current_notify_list_copy, file)
        else:
            failure_embed = discord.Embed(title=f"You did not run /atcnotify for {input}")
            await interaction.response.send_message(embed=failure_embed)
    
def atcnotifyloop(bot):
    @tasks.loop(seconds=15)
    async def atcnotifyloop():
        vatsim_data = await fetch_vatsim_API()
        current_notify_list = read_or_create_file("currentnotifylist.json")
        current_notify_list_copy = current_notify_list.copy()

        for key, item in current_notify_list.items():
            try:
                if item["pinged"] == True:
                    pass
                else:
                    user_id = await bot.fetch_user(item["user_id"])

                    for controller in vatsim_data["controllers"]:
                        item_callsignParsed = parse_controller_callsign(item["atc_id"])
                        controller_callsignParsed = parse_controller_callsign(controller["callsign"])
                        if controller_callsignParsed == item_callsignParsed:
                            if item["channel_id"] == None:
                                message = f"<@{item["user_id"]}>, **{controller["callsign"]}** is online."
                                await user_id.send(message)
                                for key_copy, item in current_notify_list_copy.items():
                                    if key_copy == key:
                                        current_notify_list_copy[key]["pinged"] = True
                                        write_to_json(current_notify_list_copy)

                            else:
                                channel = await bot.fetch_channel(item["channel_id"])
                                message = f"**{controller["callsign"]}** is online."
                                await channel.send(message)
                                for key_copy, item in current_notify_list_copy.items():
                                    if key_copy == key:
                                        current_notify_list_copy[key]["pinged"] = True
                                        write_to_json(current_notify_list_copy)

            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"oop i broke {e}")

    @tasks.loop(seconds=15)
    async def pinged_false_loop():
        vatsimdata = await fetch_vatsim_API()
        current_notify_list = read_or_create_file("currentnotifylist.json")
        current_notify_list_copy = current_notify_list.copy()
        for key, item in current_notify_list.items():
            try:
                controller_online = False
                for controller in vatsimdata["controllers"]:
                    controller_callsignParsed = parse_controller_callsign(controller["callsign"])
                    item_callsignParsed = parse_controller_callsign(item["atc_id"])
                    if controller_callsignParsed == item_callsignParsed:
                        controller_online = True
                if controller_online == False:
                    for key_copy, item_copy in current_notify_list_copy.items():
                        if key_copy == key:
                            current_notify_list_copy[key]["pinged"] = False
                            write_to_json(current_notify_list_copy)

            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"oop i broke {e}")

    atcnotifyloop.start()
    pinged_false_loop.start()
        
    async def fetch_vatsim_API():
        async with aiohttp.ClientSession() as session:
            async with session.get("https://data.vatsim.net/v3/vatsim-data.json") as response:
                vatsimdata = await response.json()
        return vatsimdata
    
    def write_to_json(current_notify_list):
        with open("currentnotifylist.json", "w") as file:
            json.dump(current_notify_list, file)
        
    def parse_controller_callsign(controller_callsign):
        callsign_split = controller_callsign.split("_")
        parsed_callsign = f"{callsign_split[0]}_{callsign_split[-1]}"
        return parsed_callsign
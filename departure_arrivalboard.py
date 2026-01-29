import json
import discord
import aiohttp
from discord import app_commands, ui

def departure_arrival_board_commands(bot):
    @bot.tree.command(name="departureboard", description="Show departures at an airport")
    @app_commands.describe(icao_code = "4-letter ICAO code")
    async def departureboard(interaction: discord.Interaction, icao_code: str):
        icao_code = icao_code.upper()
        vatsimdata = await fetch_vatsim_api()
        airportname_database = await fetch_airportname_database()

        found_pilots_list = []
        for pilot in vatsimdata["pilots"]:
            pilot_flight_plan = pilot.get("flight_plan", None)
            if pilot_flight_plan:
                if pilot_flight_plan["departure"] == icao_code:
                    found_pilots_list.append(pilot)
                else:
                    pass
            else:
                pass
        if found_pilots_list:
            view = View(found_pilots_list, airportname_database, icao_code, True)
            await interaction.response.send_message(view=view)
        else:
            failure_embed = discord.Embed(title=f"No departures at {icao_code}")
            await interaction.response.send_message(embed=failure_embed)

    @bot.tree.command(name="arrivalboard", description="Show arrivals at an airport")
    @app_commands.describe(icao_code = "4-letter ICAO code")
    async def arrivalboard(interaction: discord.Interaction, icao_code: str):
        icao_code = icao_code.upper()
        vatsimdata = await fetch_vatsim_api()
        airportname_database = await fetch_airportname_database()

        found_pilots_list = []
        for pilot in vatsimdata["pilots"]:
            pilot_flight_plan = pilot.get("flight_plan", None)
            if pilot_flight_plan:
                if pilot_flight_plan["arrival"] == icao_code:
                    found_pilots_list.append(pilot)
                else:
                    pass
            else:
                pass
        if found_pilots_list:
            view = View(found_pilots_list, airportname_database, icao_code, False)
            await interaction.response.send_message(view=view)
        else:
            failure_embed = discord.Embed(title=f"No Arrivals at {icao_code}")
            await interaction.response.send_message(embed=failure_embed)

    async def fetch_vatsim_api():
        async with aiohttp.ClientSession() as session:
            async with session.get("https://data.vatsim.net/v3/vatsim-data.json") as response:
                vatsim_data = await response.json()
        return vatsim_data
    
    async def fetch_airportname_database():
        async with aiohttp.ClientSession() as session:
            async with session.get("https://raw.githubusercontent.com/mwgg/Airports/refs/heads/master/airports.json") as response:
                airportname_database = await response.json(content_type=None)
        return airportname_database
    
    class View(ui.LayoutView):
        def __init__(self, found_pilots, airportname_database, icaocode, is_for_departureBoard):
            super().__init__()

            self.page_count = 0 # this is for previous and next buttons

            self.pilot_list = found_pilots
            self.is_for_departureBoard = is_for_departureBoard
            self.icao_code = icaocode.upper()
            self.airportname_database = airportname_database

            pilot_counter = 0

            first_container_sent = False

            page_counter_forContainers = 1

            self.containers = [] # we will add to this later
            
            
            # create first container
            container = ui.Container()
            if self.is_for_departureBoard == True:
                header = ui.TextDisplay(f"# {self.airportname_database[self.icao_code]["name"]} ({self.icao_code}) Departures - Page {page_counter_forContainers}")
            else:
                header = ui.TextDisplay(f"# {self.airportname_database[self.icao_code]["name"]} ({self.icao_code}) Arrivals - Page {page_counter_forContainers}")
            container.add_item(header)

            for pilot in self.pilot_list:
                if self.is_for_departureBoard == True:
                # convert icaocode to departure mode (versatility)
                    pilot_arrivalICAO = pilot["flight_plan"]["arrival"]
                    pilot_target_icao_code = pilot_arrivalICAO
                if self.is_for_departureBoard == False:
                    # convert icaocode to arrival mode
                    pilot_arrivalICAO = pilot["flight_plan"]["departure"]
                    pilot_target_icao_code = pilot_arrivalICAO

                button_label = f"{pilot.get("callsign")}"

                if self.is_for_departureBoard == True:
                    container.add_item(
                        ui.Section(  
                            ui.TextDisplay(
                                f"### {pilot.get("callsign")} - {str(pilot.get("cid"))} \n-# Departing to {self.airportname_database.get(pilot_target_icao_code, {}).get("name")}"
                            ),
                            accessory = ui.Button(label=button_label, url=f"https://vatsim-radar.com/?pilot={pilot.get("cid")}")
                        )
                    )
                    
                elif self.is_for_departureBoard == False:
                    container.add_item(
                        ui.Section(
                            ui.TextDisplay(
                                f"### {pilot.get("callsign")} - {str(pilot.get("cid"))} \n-# From {self.airportname_database.get(pilot_target_icao_code, {}).get("name")}"
                            ),
                            accessory = ui.Button(label=button_label, url=f"https://vatsim-radar.com/?pilot={pilot.get("cid")}")
                        )
                    )

                pilot_counter += 1
                
                if pilot_counter == 8:
                    # 8 pilots are already added to a container

                    pilot_counter = 0
                    self.containers.append(container)
                    page_counter_forContainers += 1   # add the first container to be messaged

                    if first_container_sent == False:
                        self.add_item(self.containers[0]) 
                        first_container_sent = True

                    container = ui.Container()
                    if self.is_for_departureBoard == True:
                        header = ui.TextDisplay(f"# {self.airportname_database[self.icao_code]["name"]} ({self.icao_code}) Departures - Page {page_counter_forContainers}")
                    else:
                        header = ui.TextDisplay(f"# {self.airportname_database[self.icao_code]["name"]} ({self.icao_code}) Arrivals - Page {page_counter_forContainers}")
                    container.add_item(header)
            # when the code reaches here, that means it has looped through all pilots. 
            # at this stage, the container may have 0 pilots or up to 8 pilots (the remainder). 
            if pilot_counter > 0:
                # only add the container if we had added pilots into it for the last couple pilots that dont reach 8
                self.containers.append(container)
                if first_container_sent == False:
                    self.add_item(self.containers[0]) 
                    first_container_sent = True

        row = ui.ActionRow()

        @row.button(label="Previous")
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page_count != 0:
                self.page_count -= 1
            self.clear_items()
            self.add_item(self.containers[self.page_count])

            self.add_item(self.row)
            await interaction.response.edit_message(view=self)

        @row.button(label="Next")
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page_count != len(self.containers) - 1:
                self.page_count += 1
            self.clear_items()
            self.add_item(self.containers[self.page_count])

            self.add_item(self.row)
            await interaction.response.edit_message(view=self)
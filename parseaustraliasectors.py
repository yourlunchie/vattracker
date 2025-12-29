import asyncio
import requests


async def parseaustraliasectors():
# add async def later
# here i am trying to get a LIST of extended sectors (ARL, WOL, etc., then return it to the main file)
    extendedsectorslist = []
    vatsimdataraw = requests.get("https://data.vatsim.net/v3/vatsim-data.json")
    vatsimdata = vatsimdataraw.json()
    controllerdata = vatsimdata["controllers"]
    for controller in controllerdata:
        found_controller = None
        extendedsectors_textatis = None
        if controller["callsign"].startswith("ML-") or controller["callsign"].startswith("BN-"):
            found_controller = controller # dont use this variable again to avoid confusion
            controllerdescription = found_controller["text_atis"]
            for description in controllerdescription:
                if description.startswith("Extending "):
                    extendedsectors_textatis = description
                    # we've got the extended list as a raw format (Extending WOL 125.0, BLA 132.2, etc.)
                    # here i clean up the string from (Extending WOL 125.0, BLA 132.2, etc.) to (WOL BLA etc.)
                    extendedsectors_textatis = extendedsectors_textatis.replace("Extending ", "")
                    extendedsectors_textatis = extendedsectors_textatis.replace(",", "")
                    extendedsectors_textatis = extendedsectors_textatis.replace("and ", "")
                    extendedsectors = extendedsectors_textatis.split()
                    extendedsectorslist.extend(extendedsectors[::2])
            extendedsectorslist.append(controller["callsign"][3:6])

    return extendedsectorslist

samplecontrollerdescription = [
    "Melbourne Centre",
    "Airspace, Charts, Tools - vats.im/pac/tools",
    "Pilot Procedures - vats.im/pac/pilot",
    "ATC feedback - vats.im/pac/helpdesk",
    "Extending WOL 125.0, BLA 132.2 and ARL 130.9"
    ]


        


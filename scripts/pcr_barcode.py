import os, csv, requests, atexit

import commands as cmd
import deck as dk
import state as st

from pyhamilton import (
    HamiltonInterface,
    LayoutManager,
    Plate96,
    Plate384,
    Lid,
    Tip96,
    Tip384,
    Reservoir300,
)

# Notification settings for Slack on script exit

slack_token = "xoxb-4612406885399-4627932099202-REL8YycwsJbdBKYkGJ7qeq75"
slack_channel = "#main"
slack_icon_emoji = ":see_no_evil:"
slack_user_name = "pyhamilton"


def notify(text):
    return requests.post(
        "https://slack.com/api/chat.postMessage",
        {
            "token": slack_token,
            "channel": slack_channel,
            "text": text,
            "icon_emoji": slack_icon_emoji,
            "username": slack_user_name,
            "blocks": None,
        },
    ).json()


atexit.register(notify, "Script complete or error.")

# Empty deck dictionary

deck = {
    "A": [
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
    ],
    "B": [
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
    ],
    "C": [
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
    ],
    "D": [
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
    ],
    "E": [
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
    ],
    "F": [
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
        {"level": None, "labware": None, "state": None},
    ],
}

# Define layout file and parse it

LAYOUT_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pcr-barcode.lay"
)

lmgr = LayoutManager(LAYOUT_FILE_PATH)

types = {
    "Lid": Lid,
    "Plate96": Plate96,
    "Plate384": Plate384,
    "Tip96": Tip96,
    "Tip384": Tip384,
    "Reservoir300": Reservoir300,
}

dk.parse_layout_file(deck, lmgr, types)
dk.print_deck(deck)

# Plate information and variables
# TODO: Pull information from csv file

RACKS = 12
TIPS_96 = 96
TIPS_384 = 384

CHANNELS_384 = "1" * 384
CHANNELS_384_96 = (("10" * 12) + ("0" * 24)) * 8

MIXING = "50ulTip_conductive_384COREHead_Water_DispenseSurface_Empty"

pcr_plates = [f"P{i}" for i in range(4)]

source_pcr_plates = dk.get_labware_list(
    deck,
    ["E1"],
    Plate384,
    [5],
    True,
)[0 : len(pcr_plates)]

dest_pcr_plates = dk.get_labware_list(
    deck,
    ["E2"],
    Plate384,
    [4],
    False,
)[0 : len(pcr_plates)]

barcode_plate = dk.get_labware_list(deck, ["D1"], Plate384)[0]
barcode_wells = [(barcode_plate, i) for i in range(384)]

active_pcr_plate = dk.get_labware_list(deck, ["C1"], Plate384)[0]
active_pcr_lid = dk.get_labware_list(deck, ["C1"], Lid)[0]
temp_pcr_lid = dk.get_labware_list(deck, ["C2"], Lid)[0]

tip_racks_transport = dk.get_labware_list(
    deck, ["B1", "B2", "B3"], Tip384, [3, 3, 3], True
)
tip_rack_pipet, tip_rack_transport = dk.get_labware_list(deck, ["D2"], Tip384, [2])
tips = [(tip_rack_pipet, i) for i in range(384)]


# Define state variables to keep track of current plate, well, and step in the protocol
# TODO: Make this more general, useful for other protocols

state = {
    "current_pcr_plate": 1,
    "current_rack": 1,
}

# Main script starts here
# TODO: reduce loops to functions to make it more readable
# TODO: Add error recovery
# TODO: Check if total number of tips available is enough for the protocol, add prompt when new tip racks are needed

# simulate = True opens VENUS run control in a separate window where you can enable simulation mode to test protocol

with HamiltonInterface(simulate=True) as hammy:
    cmd.initialize(hammy)

    # Loop over plates as long as there are still bact plates to process
    # TODO: check if the last plate is processed correctly

    while state["current_pcr_plate"] < len(source_pcr_plates):

        cmd.grip_get(
            hammy,
            source_pcr_plates[state["current_pcr_plate"]],
            mode=0,
            gripWidth=81.0,
            gripHeight=4.0,
        )
        cmd.grip_place(hammy, active_pcr_plate, mode=0)

        cmd.grip_get(
            hammy,
            active_pcr_lid,
            mode=1,
            gripWidth=85.0,
            gripHeight=0.5,
        )
        cmd.grip_place(hammy, temp_pcr_lid, mode=1)

        # aspirate from oligo plate to active pcr plate

        pcr_wells = [(active_pcr_plate, i) for i in range(384)]

        # get next tip rack

        cmd.grip_get_tip_rack(hammy, tip_racks_transport[state["current_rack"]])
        cmd.grip_place_tip_rack(hammy, tip_rack_transport)

        cmd.tip_pick_up_384(hammy, tips)
        cmd.aspirate_384(
            hammy,
            barcode_wells,
            1.0,
            liquidHeight=3.0,
            mixCycles=3,
            mixVolume=5.0,
            liquidClass=MIXING,
        )
        cmd.dispense_384(
            hammy, pcr_wells, 1.0, mixCycles=3, mixVolume=5.0, liquidClass=MIXING
        )
        cmd.tip_eject_384(hammy, tips, 2)

        # discard current active rack to waste

        cmd.grip_get_tip_rack(hammy, tip_rack_pipet)
        cmd.grip_place_tip_rack(hammy, tip_rack_pipet, waste=True)

        # if all currently active pcr plates are processed, place them in the dest pcr plate stack
        cmd.grip_get(
            hammy,
            temp_pcr_lid,
            mode=1,
            gripWidth=85.0,
            gripHeight=1.0,
        )
        cmd.grip_place(hammy, active_pcr_lid, mode=1)

        cmd.grip_get(
            hammy,
            active_pcr_plate,
            mode=0,
            gripWidth=81.0,
            gripHeight=6.0,
        )
        cmd.grip_place(
            hammy,
            dest_pcr_plates[state["current_pcr_plate"]],
            mode=0,
        )

        # update state variables for loop

        st.update_state(state, "current_rack", 1)
        st.update_state(state, "current_pcr_plate", 1)

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
    EppiCarrier24,
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


# atexit.register(notify, "Script complete or error.")

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
    os.path.dirname(os.path.abspath(__file__)), "pooling.lay"
)

lmgr = LayoutManager(LAYOUT_FILE_PATH)

types = {
    "Lid": Lid,
    "Plate96": Plate96,
    "Plate384": Plate384,
    "Tip96": Tip96,
    "Tip384": Tip384,
    "Reservoir300": Reservoir300,
    "EppiCarrier24": EppiCarrier24,
}

dk.parse_layout_file(deck, lmgr, types)
dk.print_deck(deck)

# Plate information and variables
# TODO: Pull information from csv file

RACKS = 12
TIPS_96 = 96
TIPS_384 = 384

CHANNELS_384_96_8 = "1" + ("0" * 11)

WASTE96 = "Waste_plate96"
MIXING = "50ulTip_conductive_384COREHead_Water_DispenseSurface_Empty"

pcr_plates = [f"P{i}" for i in range(6)]

source_pcr_plates = dk.get_labware_list(
    deck,
    ["E1"],
    Plate384,
    [6],
    True,
)[0 : len(pcr_plates)]

dest_pcr_plates = dk.get_labware_list(
    deck,
    ["E3"],
    Plate384,
    [6],
    False,
)[0 : len(pcr_plates)]

source_pooling_plates = dk.get_labware_list(
    deck,
    ["E2"],
    Plate96,
    [7],
    True,
)[0 : len(pcr_plates)]

edta_reservoir = dk.get_labware_list(deck, ["C5"], Reservoir300)[0]
edta = [(edta_reservoir, i) for i in range(384)]

edta_rack = dk.get_labware_list(deck, ["B5"], Tip384)[0]
edta_tips = [(edta_rack, i) for i in range(384)]

active_pcr_plate = dk.get_labware_list(deck, ["C4"], Plate384)[0]
active_pcr_lid = dk.get_labware_list(deck, ["C4"], Lid)[0]
temp_pcr_lid = dk.get_labware_list(deck, ["C2"], Lid)[0]
active_pcr_wells = [(active_pcr_plate, i) for i in range(384)]

active_pooling_plate = dk.get_labware_list(deck, ["C3"], Plate96)[0]
active_pooling_wells = [(active_pooling_plate, i) for i in range(96)]
active_pooling_wells_column_384 = [(active_pooling_plate, i) for i in range(8)]
active_pooling_wells_column_2 = [(active_pooling_plate, i) for i in dk.pos_2ch(8)]

eppicarrier = dk.get_labware_list(deck, ["C1"], EppiCarrier24)[0]
eppies = [(eppicarrier, i) for i in range(24)]

column_rack = dk.get_labware_list(deck, ["A3"], Tip96)[0]
column_rack_tips = [(column_rack, i) for i in range(96)]
column_holder = dk.get_labware_list(deck, ["A4"], Tip96)[0]
column_holder_tips = [(column_holder, i) for i in range(96)]

rack_300 = dk.get_labware_list(deck, ["F5"], Tip96)[0]
tips_300 = [(rack_300, i) for i in dk.pos_2ch(96)]

racks_96 = dk.get_labware_list(deck, ["B1", "B2", "B3"], Tip96, [3, 3, 3], True)
tip_rack_96_pipet, tip_rack_96_transport = dk.get_labware_list(deck, ["D2"], Tip96, [2])
tips_96 = [(tip_rack_96_pipet, i) for i in range(96)]

# Define state variables to keep track of current plate, well, and step in the protocol
# TODO: Make this more general, useful for other protocols

state = {
    "current_pcr_plate": 0,
    "current_pooling_plate": 0,
    "current_rack": 0,
    "current_tip_column": 0,
    "current_tip": 0,
}

# Main script starts here
# TODO: reduce loops to functions to make it more readable
# TODO: Add error recovery
# TODO: Check if total number of tips available is enough for the protocol, add prompt when new tip racks are needed

# simulate = True opens VENUS run control in a separate window where you can enable simulation mode to test protocol

with HamiltonInterface(simulate=True) as hammy:
    cmd.initialize(hammy)

    cmd.tip_pick_up_384(hammy, column_rack_tips, tipMode=1)
    cmd.tip_eject_384(hammy, column_holder_tips)

    # Loop over plates as long as there are still bact plates to process
    # TODO: check if the last plate is processed correctly

    while state["current_pcr_plate"] < len(source_pcr_plates):

        # get pcr plate

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

        # get pooling plate

        cmd.grip_get(
            hammy,
            source_pooling_plates[state["current_pooling_plate"]],
            mode=0,
            gripWidth=81.0,
            gripHeight=5.0,
        )
        cmd.grip_place(hammy, active_pooling_plate, mode=0)

        # add EDTA

        cmd.tip_pick_up_384(hammy, edta_tips)
        cmd.aspirate_384(hammy, edta, 20.0, liquidHeight=2.0)
        cmd.dispense_384(
            hammy, active_pcr_wells, 20.0, liquidHeight=10.0, dispenseMode=9
        )
        cmd.tip_eject_384(hammy, edta_tips, 1)

        # get next 96/384-tip rack, pickup tips and transfer to pooling plate

        cmd.grip_get_tip_rack(hammy, racks_96[state["current_rack"]])
        cmd.grip_place_tip_rack(hammy, tip_rack_96_transport)

        cmd.tip_pick_up_384(hammy, tips_96, tipMode=1)

        for i in range(4):

            pcr_wells = [(active_pcr_plate, i) for i in dk.pos_96_in_384(i)]

            cmd.aspirate_384(
                hammy,
                pcr_wells,
                4.0,
                liquidHeight=3.0,
                mixCycles=3,
                mixVolume=20.0,
                liquidClass=MIXING,
            )
            cmd.dispense_384(
                hammy,
                active_pooling_wells,
                4.0,
                liquidHeight=10.0,
                dispenseMode=9,
                liquidClass=MIXING,
            )

        cmd.tip_eject_384(hammy, tips_96, 2)

        # discard current active rack to waste

        cmd.grip_get_tip_rack(hammy, tip_rack_96_pipet)
        cmd.grip_place_tip_rack(hammy, tip_rack_96_pipet, waste=True)

        # transfer columns 2-12 to column 1 in pooling plate

        column_tips = [(column_holder, i) for i in dk.pos_96_rev()][
            state["current_tip_column"] * 8 :
        ]

        cmd.tip_pick_up_384(
            hammy,
            column_tips,
            tipMode=1,
            reducedPatternMode=4,
            headPatternAsVariable=1,
            headPatternVariable=CHANNELS_384_96_8,
        )

        for i in range(1, 12):
            cmd.aspirate_384(
                hammy, active_pooling_wells[8 * i : 8 * (i + 1)], 16.0, liquidHeight=0.1
            )
            cmd.dispense_384(
                hammy,
                active_pooling_wells_column_384,
                16.0,
                dispenseMode=9,
                liquidHeight=10.0,
            )

        cmd.tip_eject_384(hammy, column_tips, 2)

        st.update_state(state, "current_tip_column", 1)

        # transfer to eppendorf tube

        cmd.tip_pick_up(
            hammy, tips_300[state["current_tip"] : state["current_tip"] + 2]
        )

        for i in range(0, 8, 2):

            cmd.aspirate(
                hammy, active_pooling_wells_column_2[i : i + 2], [192], liquidHeight=0.1
            )
            cmd.dispense(
                hammy,
                [
                    eppies[state["current_pcr_plate"]],
                    eppies[state["current_pcr_plate"]],
                ],
                [192],
                dispenseMode=9,
                liquidHeight=30.0,
            )

        cmd.tip_eject(
            hammy, tips_300[state["current_tip"] : state["current_tip"] + 2], waste=True
        )

        st.update_state(state, "current_tip", 2)

        # move current pcr plate to done stack

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

        # discard current pooling plate

        cmd.grip_get(
            hammy,
            active_pooling_plate,
            mode=0,
            gripWidth=81.0,
            gripHeight=5.0,
        )
        cmd.grip_place(hammy, active_pooling_plate, mode=0, eject=True)

        st.update_state(state, "current_pcr_plate", 1)
        st.update_state(state, "current_pooling_plate", 1)
        st.update_state(state, "current_rack", 1)

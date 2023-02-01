import os, sys, csv, requests, atexit

sys.path.append("test-scripts")

import commands as cmd
import deck as dk
import state as st

from pyhamilton import (
    HamiltonInterface,
    LayoutManager,
    Lid,
    Plate96,
    Plate384,
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
    os.path.dirname(os.path.abspath(__file__)), "pooling.lay"
)


lmgr = LayoutManager(LAYOUT_FILE_PATH)

dk.parse_layout_file(deck, lmgr)
dk.clean_deck(deck)
dk.print_deck(deck)

# Plate information and variables

RACKS = 9
TIPS_96 = 96
TIPS_384 = 384

CHANNELS_384_96_8 = "1" + ("0" * 11)

pcr_plates = [f"P{i}" for i in range(8)]

# Define labware from parsed layout file
# TODO: Allow user to specify labware type and number of labware from prompt

source_pcr_plates = dk.get_labware_list(
    deck,
    ["E1"],
    Plate384,
    [8],
    True,
)[0 : len(pcr_plates)]

dest_pcr_plates = dk.get_labware_list(
    deck,
    ["E2"],
    Plate384,
    [8],
    False,
)[0 : len(pcr_plates)]

source_pooling_plates = dk.get_labware_list(
    deck,
    ["F1"],
    Plate96,
    [8],
    True,
)[0 : len(pcr_plates)]

dest_pooling_plates = dk.get_labware_list(
    deck,
    ["F2"],
    Plate96,
    [8],
    False,
)[0 : len(pcr_plates)]

edta_reservoir = dk.get_labware_list(deck, ["C5"], Reservoir300)[0]
edta = [(edta_reservoir, i) for i in range(384)]

edta_rack = dk.get_labware_list(deck, ["B5"], Tip384)[0]
edta_tips = [(edta_rack, i) for i in range(384)]

active_pcr_plate = dk.get_labware_list(deck, ["C4"], Plate384)[0]
active_pcr_wells = [(active_pcr_plate, i) for i in range(384)]
active_pcr_lid = dk.get_labware_list(deck, ["C4"], Lid)[0]
temp_pcr_lid = dk.get_labware_list(deck, ["C2"], Lid)[0]

active_pooling_plate = dk.get_labware_list(deck, ["C3"], Plate96)[0]
active_pooling_wells = [(active_pooling_plate, i) for i in range(96)]
active_pooling_wells_8ch = [(active_pooling_plate, i) for i in range(8)]
active_pooling_wells_2ch = [(active_pooling_plate, i) for i in dk.pos_2ch(8)]

eppicarrier = dk.get_labware_list(deck, ["C1"], EppiCarrier24)[0]
eppies = [(eppicarrier, i) for i in range(24)]

column_rack = dk.get_labware_list(deck, ["A3"], Tip96)[0]
column_rack_tips = [(column_rack, i) for i in range(96)]

column_holder = dk.get_labware_list(deck, ["A4"], Tip96)[0]
column_holder_tips = [(column_holder, i) for i in range(96)]

rack_300 = dk.get_labware_list(deck, ["F5"], Tip96)[0]
tips_300 = [(rack_300, i) for i in dk.pos_2ch(96)]

racks_96 = dk.get_labware_list(deck, ["B1", "B2", "B3"], Tip96, [3, 3, 3], True)
rack_96_tips, rack_96_virtual = dk.get_labware_list(deck, ["D2"], Tip96, [2])
tips_96 = [(rack_96_tips, i) for i in range(96)]

# Define state variables to keep track of current plate, well, and step in the protocol
# TODO: Make this more general, useful for other protocols

STATE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

state = {
    "current_pcr_plate": 0,
    "current_pooling_plate": 0,
    "current_quadrant": 0,
    "current_column": 0,
    "current_well": 0,
    "current_eppi": 0,
    "current_rack": 0,
    "current_tip_column": 0,
    "current_tip": 0,
    "active_pooling_plate": 0,
    "active_pcr_plate": 0,
    "edta": 0,
    "active_rack": 0,
}

if not os.path.exists(STATE_FILE_PATH):
    st.save_state(state, STATE_FILE_PATH)
else:
    st.recover_state(STATE_FILE_PATH)

# Main script starts here
# TODO: reduce loops to functions to make it more readable
# TODO: Add error recovery


if __name__ == "__main__":
    ## simulate = True opens VENUS run control in a separate window where you can enable simulation mode to test protocol

    with HamiltonInterface(simulate=True) as hammy:
        cmd.initialize(hammy)

        cmd.tip_pick_up_384(hammy, column_rack_tips, tipMode=1)
        cmd.tip_eject_384(hammy, column_holder_tips)

        # Loop over plates as long as there are still pcr plates to process

        while state["current_pcr_plate"] < len(source_pcr_plates):
            # Get next pcr plate from source stack if not already done

            if not state["active_pcr_plate"]:
                cmd.grip_get(
                    hammy,
                    source_pcr_plates[state["current_pcr_plate"]],
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=4.0,
                )
                cmd.grip_place(hammy, active_pcr_plate, mode=0)
                cmd.grip_get(
                    hammy, active_pcr_lid, mode=1, gripWidth=85.0, gripHeight=0.5
                )
                cmd.grip_place(hammy, temp_pcr_lid, mode=1)

                st.reset_state(state, STATE_FILE_PATH, "active_pcr_plate", 1)

            # Get next pooling plate from source stack if not already done

            if not state["active_pooling_plate"]:
                cmd.grip_get(
                    hammy,
                    source_pooling_plates[state["current_pooling_plate"]],
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=5.0,
                )
                cmd.grip_place(hammy, active_pooling_plate, mode=0)

                st.reset_state(state, STATE_FILE_PATH, "active_pooling_plate", 1)

            # Add EDTA to pcr plate if not already done

            if not state["edta"]:
                cmd.tip_pick_up_384(hammy, edta_tips)
                cmd.aspirate_384(hammy, edta, 20.0, liquidHeight=2.0)
                cmd.dispense_384(
                    hammy, active_pcr_wells, 20.0, liquidHeight=11.0, dispenseMode=9
                )
                cmd.tip_eject_384(hammy, edta_tips, 1)

                st.reset_state(state, STATE_FILE_PATH, "edta", 1)

            # Get next 96_384-tip rack if not already done

            if not state["active_rack"]:
                cmd.grip_get_tip_rack(hammy, racks_96[state["current_rack"]])
                cmd.grip_place_tip_rack(hammy, rack_96_virtual)

                st.reset_state(state, STATE_FILE_PATH, "active_rack", True)

            # Transfer 384 wells in pcr plate to 96 in pooling plate

            cmd.tip_pick_up_384(hammy, tips_96, tipMode=1)

            for quadrant in range(state["current_quadrant"], 4):
                pcr_wells = [(active_pcr_plate, i) for i in dk.pos_96_in_384(quadrant)]

                cmd.aspirate_384(
                    hammy,
                    pcr_wells,
                    5.0,
                    liquidHeight=3.0,
                    mixCycles=3,
                    mixVolume=20.0,
                )
                cmd.dispense_384(
                    hammy,
                    active_pooling_wells,
                    5.0,
                    liquidHeight=10.0,
                    dispenseMode=9,
                )

                st.update_state(state, STATE_FILE_PATH, "current_quadrant", 1)

            cmd.tip_eject_384(hammy, tips_96, 2)

            # Transfer columns 2-12 to column 1 in pooling plate using 8 tips on 384-head

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

            for column in range(state["current_column"], 12):
                cmd.aspirate_384(
                    hammy,
                    active_pooling_wells[8 * column : 8 * (column + 1)],
                    16.0,
                    liquidHeight=0.5,
                )
                cmd.dispense_384(
                    hammy,
                    active_pooling_wells_8ch,
                    16.0,
                    dispenseMode=9,
                    liquidHeight=10.0,
                )

                st.update_state(state, STATE_FILE_PATH, "current_column", 1)

            cmd.tip_eject_384(hammy, column_tips, 2)
            st.update_state(state, STATE_FILE_PATH, "current_tip_column", 1)

            # Transfer column 1 in pooling plate to next eppendorf tube using 2 channels

            cmd.tip_pick_up(
                hammy, tips_300[state["current_tip"] : state["current_tip"] + 2]
            )

            for well in range(state["current_well"], 8, 2):
                cmd.aspirate(
                    hammy,
                    active_pooling_wells_2ch[well : well + 2],
                    [192],
                    liquidHeight=0.5,
                )
                cmd.dispense(
                    hammy,
                    [
                        eppies[state["current_pcr_plate"]],
                        eppies[state["current_pcr_plate"]],
                    ],
                    [192],
                    dispenseMode=9,
                    liquidHeight=35.0,
                )

                st.update_state(state, STATE_FILE_PATH, "current_well", 2)

            cmd.tip_eject(
                hammy,
                tips_300[state["current_tip"] : state["current_tip"] + 2],
                waste=True,
            )
            st.update_state(state, STATE_FILE_PATH, "current_tip", 2)

            # Move active pcr plate to destination stack if not already done

            if state["active_pcr_plate"]:
                cmd.grip_get(
                    hammy,
                    temp_pcr_lid,
                    mode=1,
                    gripWidth=85.0,
                    gripHeight=0.5,
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
                st.update_state(state, STATE_FILE_PATH, "current_pcr_plate", 1)

            # Move active pooling plate to destination stack if not already done

            if state["active_pooling_plate"]:
                cmd.grip_get(
                    hammy,
                    active_pooling_plate,
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=9.0,
                )
                cmd.grip_place(
                    hammy, dest_pooling_plates[state["current_pooling_plate"]], mode=0
                )
                st.update_state(state, STATE_FILE_PATH, "current_pooling_plate", 1)

            # Discard current 96_384-tip rack if not already done

            if state["active_rack"]:
                cmd.grip_get_tip_rack(hammy, rack_96_tips)
                cmd.grip_place_tip_rack(hammy, rack_96_tips, waste=True)
                st.update_state(state, STATE_FILE_PATH, "current_rack", 1)

            # Reset state variables for next run

            st.reset_state(state, STATE_FILE_PATH, "current_quadrant", 0)
            st.reset_state(state, STATE_FILE_PATH, "current_column", 0)
            st.reset_state(state, STATE_FILE_PATH, "current_well", 0)
            st.reset_state(state, STATE_FILE_PATH, "active_pcr_plate", 0)
            st.reset_state(state, STATE_FILE_PATH, "active_pooling_plate", 0)
            st.reset_state(state, STATE_FILE_PATH, "edta", 0)
            st.reset_state(state, STATE_FILE_PATH, "active_rack", 0)

            st.print_state(state)

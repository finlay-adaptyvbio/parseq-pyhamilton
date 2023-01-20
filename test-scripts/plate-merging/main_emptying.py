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
    os.path.dirname(os.path.abspath(__file__)), "plate-merging-emptying.lay"
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

plates = [
    "P4.2",
    "P4.3",
    "P1.9",
    "P1.8",
    "P1.12",
    "P4.7",
    "P2.4",
    "P1.13",
    "P2.2",
    "P4.5",
    "P4.4",
    "P4.1",
]

channels = 2
channel_1 = "10"
channel_2 = "01"

# Define labware from parsed layout file
# TODO: Adjust stacks depending on number of plates

## Each labware is defined manually for now, this probably won't change in the future

source_bact_plates = dk.get_labware_list(
    deck,
    ["F1", "F2", "F3", "F4", "E1", "E2"],
    Plate384,
    [6, 6, 6, 6, 6, 6],
    True,
)[0 : len(plates)]

dest_bact_plates = dk.get_labware_list(
    deck,
    ["E3", "F1", "F2", "F3", "F4", "E1", "E2"],
    Plate384,
    [6, 6, 6, 6, 6, 6, 6],
    False,
)[0 : len(plates)]

active_bact_plate = dk.get_labware_list(deck, ["E5"], Plate384)[0]
active_bact_lid = dk.get_labware_list(deck, ["E5"], Lid)[0]
temp_bact_lid = dk.get_labware_list(deck, ["E4"], Lid)[0]

ethanol_reservoir = dk.get_labware_list(deck, ["C5"], Reservoir300)[0]
waste_reservoir = dk.get_labware_list(deck, ["D1"], Reservoir300)[0]

active_pipet_tips = dk.get_labware_list(deck, ["F5"], Tip96)[0]
tip_indexes = dk.sort_96_indexes_2channel([dk.index_to_string_96(i) for i in range(96)])
tips = [
    (active_pipet_tips, dk.string_to_index_96(tip_index)) for tip_index in tip_indexes
]

waste = [(waste_reservoir, position) for position in range(182, 187, channels * 2)]
ethanol = [(ethanol_reservoir, position) for position in range(368, 373, channels * 2)]

# Get wells to empty from csv file

discard = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "plate_merging_emptying.csv"
)

with open(discard) as f:
    reader = csv.reader(f)
    wells_to_empty = [tuple(row) for row in reader]

# Define state variables to keep track of current plate, well, and step in the protocol
# TODO: Make this more general, useful for other protocols

state = {
    "current_plate": 0,
    "current_well": 0,
    "current_step": 0,
    "current_rack": 0,
    "current_tip": 0,
    "channel_steps": 0,
}

## We need to define separate liquid classes for ethanol dispense and aspirate steps

ETHANOL_ASPIRATE = "StandardVolume_EtOH_DispenseJet_Empty"
ETHANOL_DISPENSE = "StandardVolume_EtOH_DispenseJet_Part"

# Main script starts here
# TODO: reduce loops to functions to make it more readable
# TODO: add error recovery
# TODO: add tip rack handling if necessary (large number of plates)

## simulate = True opens VENUS run control in a separate window where you can enable simulation mode to test protocol

with HamiltonInterface(simulate=True) as hammy:
    cmd.initialize(hammy)

    # Iterate through plates
    ## TODO: switch to explicit variables for current plate and well for better state tracking

    while state["current_plate"] < len(plates):
        # Build well list for current plate and sort for efficient pipetting

        raw_wells = [
            well[1]
            for well in wells_to_empty
            if well[0] == plates[state["current_plate"]]
        ]
        indexes = dk.sort_384_indexes_2channel(raw_wells)
        wells = [
            (active_bact_plate, dk.string_to_index_384(index)) for index in indexes
        ]

        # Get next plate and move to active position, remove lid

        cmd.grip_get(
            hammy,
            source_bact_plates[state["current_plate"]],
            mode=0,
            gripWidth=82.0,
            gripHeight=9.0,
        )
        cmd.grip_place(hammy, active_bact_plate, mode=0)
        cmd.grip_get(hammy, active_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0)
        cmd.grip_place(hammy, temp_bact_lid, mode=1, eject=True)

        # Get next 2 tips from active tip stack

        cmd.tip_pick_up(
            hammy, tips[state["current_tip"] : state["current_tip"] + channels]
        )
        st.update_state(state, "current_tip", channels)

        # Aspirate media from active plate and dispense to waste reservoir
        ## We loop through the wells in groups of 4 (2 * 2 channels) and aspirate 140 uL from each well

        while state["current_well"] < len(wells) and state["current_step"] == 0:
            ## In the case where there are less than 4 wells left, we only aspirate from the remaining wells

            stop = min(4, len(wells[state["current_well"] :]))

            for i in range(0, stop, 2):
                ## Currently there seems to be a bug in VENUS when aspirating > 60 times from one channel consecutively
                ## This is a workaround to reset the channel after 58 steps

                if state["channel_steps"] % 58 == 0:
                    cmd.tip_eject(
                        hammy,
                        tips[state["current_tip"] : state["current_tip"] + channels],
                        waste=True,
                    )
                    cmd.tip_pick_up(
                        hammy,
                        tips[state["current_tip"] : state["current_tip"] + channels],
                    )
                    st.update_state(state, "current_tip", channels)

                ## The first aspirate command must be set to aspirateMode = 0, otherwise the pipette will not aspirate blowout volume
                ## This doesn't seem to work (VENUS still outputs warning about aspiration mode)

                if i >= 2:
                    aspirateMode = 1
                else:
                    aspirateMode = 0

                # Aspirate from wells (with mixing) and dispense to waste
                ## If there are an odd number of wells left, aspirate and dispense with one channel

                if stop - i == 1:
                    cmd.aspirate(
                        hammy,
                        [wells[state["current_well"] + i]],
                        [140],
                        channelVariable=channel_1,
                        aspirateMode=aspirateMode,
                        mixCycles=3,
                        mixVolume=50.0,
                    )
                    dispense_volume = [
                        140 * int((i + channels) / channels),
                        100 * (i / channels),
                    ]
                    st.update_state(state, "current_well", 1)

                else:
                    cmd.aspirate(
                        hammy,
                        wells[
                            state["current_well"]
                            + i : state["current_well"]
                            + i
                            + channels
                        ],
                        [140],
                        aspirateMode=aspirateMode,
                        mixCycles=3,
                        mixVolume=50.0,
                    )
                    dispense_volume = [140 * int((i + channels) / channels)]
                    st.update_state(state, "current_well", 2)

                st.update_state(state, "channel_steps", 1)

            cmd.dispense(hammy, waste, dispense_volume, dispenseMode=9)

        # Dispense ethanol into emptied wells of active plate
        ## This loop advances in steps of 6 (3 * 2 channels) and dispenses 100 uL into each well

        while state["current_well"] < len(wells) and state["current_step"] == 1:
            ## In the case where there are less than 6 wells left, we only dispense into the remaining wells

            stop = min(6, len(wells[state["current_well"] :]))

            ## Currently there seems to be a bug in VENUS when aspirating > 60 times from one channel consecutively
            ## This is a workaround to reset the channel after 58 steps

            if state["channel_steps"] % 58 == 0:
                cmd.tip_eject(
                    hammy,
                    tips[state["current_tip"] : state["current_tip"] + channels],
                    waste=True,
                )
                cmd.tip_pick_up(
                    hammy,
                    tips[state["current_tip"] : state["current_tip"] + channels],
                )
                st.update_state(state, "current_tip", channels)

            # Set aspirate volume depending on number of channels used and aspirate

            if stop % 2 == 0:
                aspirate_volume = [100 * stop / channels]
            else:
                aspirate_volume = [
                    100 * (stop + 1) / channels,
                    100 * (stop - 1) / channels,
                ]

            cmd.aspirate(hammy, ethanol, aspirate_volume, liquidClass=ETHANOL_DISPENSE)

            st.update_state(state, "channel_steps", 1)

            for i in range(0, stop, 2):
                state["channel_steps"] += 1

                # Dispense into wells
                ## If there are an odd number of wells left, dispense with one channel

                if stop - i == 1:
                    cmd.dispense(
                        hammy,
                        [wells[state["current_well"] + i]],
                        [100],
                        channelVariable=channel_1,
                        liquidClass=ETHANOL_DISPENSE,
                    )
                    st.update_state(state, "current_well", 1)

                else:
                    cmd.dispense(
                        hammy,
                        wells[
                            state["current_well"]
                            + i : state["current_well"]
                            + i
                            + channels
                        ],
                        [100],
                        liquidClass=ETHANOL_DISPENSE,
                    )
                    st.update_state(state, "current_well", 2)

        # Update state variables for next step

        st.update_state(state, "current_step", 1)
        st.reset_state(state, "current_well", 0)

        # Aspirate ethanol from active plate and dispense to waste reservoir
        ## Loop advances in steps of 4 (2 * 2 channels) and aspirates 140 uL from each well

        while state["current_well"] < len(wells) and state["current_step"] == 2:
            ## In the case where there are less than 4 wells left, we only aspirate from the remaining wells

            stop = min(4, len(wells[state["current_well"] :]))

            for i in range(0, stop, 2):
                ## Currently there seems to be a bug in VENUS when aspirating > 60 times from one channel consecutively
                ## This is a workaround to reset the channel after 58 steps

                if state["channel_steps"] % 58 == 0:
                    cmd.tip_eject(
                        hammy,
                        tips[state["current_tip"] : state["current_tip"] + channels],
                        waste=True,
                    )
                    cmd.tip_pick_up(
                        hammy,
                        tips[state["current_tip"] : state["current_tip"] + channels],
                    )
                    st.update_state(state, "current_tip", channels)

                ## The first aspirate command must be set to aspirateMode = 0, otherwise the pipette will not aspirate blowout volume
                ## This doesn't seem to work (VENUS still outputs warning about aspiration mode)

                if i >= 2:
                    aspirateMode = 1
                else:
                    aspirateMode = 0

                # Aspirate from wells (with mixing) and dispense to waste
                ## If there are an odd number of wells left, aspirate and dispense with one channel

                if stop - i == 1:
                    cmd.aspirate(
                        hammy,
                        [wells[state["current_well"] + i]],
                        [140],
                        channelVariable=channel_1,
                        aspirateMode=aspirateMode,
                        liquidClass=ETHANOL_ASPIRATE,
                        mixCycles=3,
                        mixVolume=50.0,
                    )
                    dispense_volume = [
                        140 * int((i + channels) / channels),
                        100 * (i / channels),
                    ]
                    st.update_state(state, "current_well", 1)

                else:
                    cmd.aspirate(
                        hammy,
                        wells[
                            state["current_well"]
                            + i : state["current_well"]
                            + i
                            + channels
                        ],
                        [140],
                        aspirateMode=aspirateMode,
                        liquidClass=ETHANOL_ASPIRATE,
                        mixCycles=3,
                        mixVolume=50.0,
                    )
                    dispense_volume = [140 * int((i + channels) / channels)]
                    st.update_state(state, "current_well", 2)

                st.update_state(state, "channel_steps", 1)

            cmd.dispense(
                hammy,
                waste,
                dispense_volume,
                liquidClass=ETHANOL_ASPIRATE,
                dispenseMode=9,
            )

        # Update state variables for next step

        st.update_state(state, "current_step", 1)
        st.reset_state(state, "current_well", 0)

        # Eject tips on pickup position

        cmd.tip_eject(
            hammy, tips[state["current_tip"] : state["current_tip"] + channels]
        )

        # Place lid on active plate and move to done stack

        cmd.grip_get(hammy, temp_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0)
        cmd.grip_place(hammy, active_bact_lid, mode=1)
        cmd.grip_get(hammy, active_bact_plate, mode=0, gripWidth=82.0, gripHeight=9.0)
        cmd.grip_place(hammy, dest_bact_plates[state["current_plate"]], mode=0)

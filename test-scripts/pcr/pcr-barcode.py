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
    os.path.dirname(os.path.abspath(__file__)), "plate-merging-filling.lay"
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
TIPS = 96

CHANNELS = 2
CHANNEL_1 = "10"
CHANNEL_2 = "01"

target_plates = [
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

source_plates = [
    "P1.7",
    "P1.4",
    "P1.3",
    "P1.6",
    "P1.5",
    "P2.6",
    "P2.5",
    "P1.1",
    "P1.2",
    "P2.1",
    "P4.6",
    "P2.3",
    "P4.8",
]

target_bact_plates = dk.get_labware_list(
    deck,
    ["F1", "F2"],
    Plate384,
    [6, 6],
    True,
)[0 : len(target_plates)]

source_bact_plates = dk.get_labware_list(
    deck,
    ["E1", "E2", "E3"],
    Plate384,
    [6, 6, 6],
    True,
)[0 : len(source_plates)]

dest_target_bact_plates = dk.get_labware_list(
    deck,
    ["F3", "F1", "F2"],
    Plate384,
    [6, 6, 6],
    False,
)[0 : len(target_plates)]

dest_source_bact_plates = dk.get_labware_list(
    deck,
    ["F4", "E1", "E2", "E3"],
    Plate384,
    [6, 6, 6, 6],
    False,
)[0 : len(source_plates)]

active_source_bact_plate = dk.get_labware_list(deck, ["E5"], Plate384)[0]
active_source_bact_lid = dk.get_labware_list(deck, ["E5"], Lid)[0]
temp_source_bact_lid = dk.get_labware_list(deck, ["C3"], Lid)[0]

active_target_bact_plate = dk.get_labware_list(deck, ["E4"], Plate384)[0]
active_target_bact_lid = dk.get_labware_list(deck, ["E4"], Lid)[0]
temp_target_bact_lid = dk.get_labware_list(deck, ["C2"], Lid)[0]

active_pipet_tips, active_dest_tips = dk.get_labware_list(deck, ["F5"], Tip96, [2])

tip_racks = dk.get_labware_list(deck, ["B1", "B2", "B3"], Tip96, [4, 4, 4], True)

tip_indexes = dk.sort_96_indexes_2channel([dk.index_to_string_96(i) for i in range(96)])
tips = [
    (active_pipet_tips, dk.string_to_index_96(tip_index)) for tip_index in tip_indexes
]


discard = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "plate_merging_emptying.csv"
)

keep = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "plate_merging_filling.csv"
)

with open(discard) as f:
    reader = csv.reader(f)
    wells_to_fill = [tuple(row) for row in reader][0:1248]

with open(keep) as f:
    reader = csv.reader(f)
    wells_to_empty = [tuple(row) for row in reader][0:1248]

# Define state variables to keep track of current plate, well, and step in the protocol
# TODO: Make this more general, useful for other protocols

state = {
    "current_source_plate": 0,
    "current_target_plate": 0,
    "current_source_well": 0,
    "current_target_well": 0,
    "current_tip": 0,
    "current_rack": 0,
    "channel_steps": 0,
}

# Main script starts here
# TODO: reduce loops to functions to make it more readable
# TODO: Add error recovery
# TODO: Check if total number of tips available is enough for the protocol, add prompt when new tip racks are needed

## simulate = True opens VENUS run control in a separate window where you can enable simulation mode to test protocol

with HamiltonInterface(simulate=True) as hammy:
    cmd.initialize(hammy)

    # Initial placement for first plates in each stack
    # TODO: Add check if starting from error recovery (no need for initial placement)

    cmd.grip_get(
        hammy, source_bact_plates[state["current_source_plate"]], mode=0, gripWidth=82.0
    )
    cmd.grip_place(hammy, active_source_bact_plate, mode=0)
    cmd.grip_get(hammy, active_source_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0)
    cmd.grip_place(hammy, temp_source_bact_lid, mode=1)
    cmd.grip_get(
        hammy, target_bact_plates[state["current_target_plate"]], mode=0, gripWidth=82.0
    )
    cmd.grip_place(hammy, active_target_bact_plate, mode=0)
    cmd.grip_get(hammy, active_target_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0)
    cmd.grip_place(hammy, temp_target_bact_lid, mode=1, eject=True)

    # Build list of source and target wells for current plates and sort them

    source_raw_wells = [
        well[1]
        for well in wells_to_empty
        if well[0] == source_plates[state["current_source_plate"]]
    ]
    source_indexes = dk.sort_384_indexes_2channel(source_raw_wells)
    source_wells = [
        (active_source_bact_plate, dk.string_to_index_384(index))
        for index in source_indexes
    ]

    target_raw_wells = [
        well[1]
        for well in wells_to_fill
        if well[0] == target_plates[state["current_target_plate"]]
    ]
    target_indexes = dk.sort_384_indexes_2channel(target_raw_wells)
    target_wells = [
        (active_target_bact_plate, dk.string_to_index_384(index))
        for index in target_indexes
    ]

    # Loop over plates as long as there are still plates (source or target) to process
    # TODO: check if the last plate is processed correctly

    while (
        state["current_source_plate"] < len(source_plates) - 1
        or state["current_target_plate"] < len(target_plates) - 1
    ):
        # Check if there are still wells to process in the current source plate
        # Swich to next source plate if current one is done

        if state["current_source_well"] >= len(source_wells):
            cmd.grip_get(
                hammy, temp_source_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0
            )
            cmd.grip_place(hammy, active_source_bact_lid, mode=1)
            cmd.grip_get(
                hammy, active_source_bact_plate, mode=0, gripWidth=82.0, gripHeight=9.0
            )
            cmd.grip_place(
                hammy, dest_source_bact_plates[state["current_source_plate"]], mode=0
            )

            print(
                f"Source plate {source_plates[state['current_source_plate']]} done."
                " Getting new source plate"
                f" {source_plates[state['current_source_plate'] + 1]}."
            )
            st.update_state(state, "current_source_plate", 1)

            cmd.grip_get(
                hammy,
                source_bact_plates[state["current_source_plate"]],
                mode=0,
                gripWidth=82.0,
            )
            cmd.grip_place(hammy, active_source_bact_plate, mode=0)
            cmd.grip_get(
                hammy,
                active_source_bact_lid,
                mode=1,
                gripWidth=85.2,
                gripHeight=5.0,
            )
            cmd.grip_place(hammy, temp_source_bact_lid, mode=1, eject=True)

            # Build new list of wells for next source plate and sort them

            source_raw_wells = [
                well[1]
                for well in wells_to_empty
                if well[0] == source_plates[state["current_source_plate"]]
            ]
            source_indexes = dk.sort_384_indexes_2channel(source_raw_wells)
            source_wells = [
                (active_source_bact_plate, dk.string_to_index_384(index))
                for index in source_indexes
            ]
            st.reset_state(state, "current_source_well", 0)

        # Check if there are still wells to process in the current target plate
        # Swich to next target plate if current one is done

        if state["current_target_well"] >= len(target_wells):
            cmd.grip_get(
                hammy, temp_target_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0
            )
            cmd.grip_place(hammy, active_target_bact_lid, mode=1)
            cmd.grip_get(
                hammy, active_target_bact_plate, mode=0, gripWidth=82.0, gripHeight=9.0
            )
            cmd.grip_place(
                hammy, dest_target_bact_plates[state["current_target_plate"]], mode=0
            )

            print(
                f"Target plate {target_plates[state['current_target_plate']]} done."
                " Getting new target plate"
                f" {target_plates[state['current_target_plate'] + 1]}."
            )
            st.update_state(state, "current_target_plate", 1)

            cmd.grip_get(
                hammy,
                target_bact_plates[state["current_target_plate"]],
                mode=0,
                gripWidth=82.0,
            )
            cmd.grip_place(hammy, active_target_bact_plate, mode=0)
            cmd.grip_get(
                hammy,
                active_target_bact_lid,
                mode=1,
                gripWidth=85.2,
                gripHeight=5.0,
            )
            cmd.grip_place(hammy, temp_target_bact_lid, mode=1, eject=True)

            # Build new list of wells for next target plate and sort them

            target_raw_wells = [
                well[1]
                for well in wells_to_fill
                if well[0] == target_plates[state["current_target_plate"]]
            ]
            target_indexes = dk.sort_384_indexes_2channel(target_raw_wells)
            target_wells = [
                (active_target_bact_plate, dk.string_to_index_384(index))
                for index in target_indexes
            ]
            st.reset_state(state, "current_target_well", 0)

        # Check if there are still tips in the active rack
        # Discard rack and get new one from stacked racks if current one is done

        if state["current_tip"] >= TIPS:
            print(f"Active rack done. Picking up rack {state['current_rack'] + 1}.")

            cmd.grip_get_tip_rack(hammy, active_pipet_tips)
            cmd.grip_place_tip_rack(hammy, active_pipet_tips, waste=True)
            cmd.grip_get_tip_rack(hammy, tip_racks[state["current_rack"]])
            cmd.grip_place_tip_rack(hammy, active_dest_tips)

            st.update_state(state, "current_rack", 1)
            st.reset_state(state, "current_tip", 0)

        # Check how many wells are left to pipet in the current source and target plate
        # Also check if there are enough tips left to pipet the remaining wells

        ## This outputs the minimum of the three values (wells left, tips left, channels)

        source_well_stop = min(
            CHANNELS,
            len(source_wells[state["current_source_well"] :]),
            (TIPS - state["current_tip"]),
        )
        target_well_stop = min(
            CHANNELS,
            len(target_wells[state["current_target_well"] :]),
            (TIPS - state["current_tip"]),
        )

        print(
            f"Source wells to pipet: {source_well_stop} | Target wells to pipet:"
            f" {target_well_stop}"
        )

        # In the case that there is only one well left to pipet, use only one channel

        if source_well_stop == 1 or target_well_stop == 1:
            print(
                "Aspirating:"
                f" {dk.index_to_string_384(source_wells[state['current_source_well']][1])} |"
                " Dispensing:"
                f" {dk.index_to_string_384(target_wells[state['current_target_well']][1])}"
            )

            cmd.tip_pick_up(
                hammy, [tips[state["current_tip"]]], channelVariable=CHANNEL_1
            )
            cmd.aspirate(
                hammy,
                [source_wells[state["current_source_well"]]],
                [100],
                channelVariable=CHANNEL_1,
                mixCycles=3,
                mixVolume=50.0,
            )
            cmd.dispense(
                hammy,
                [target_wells[state["current_target_well"]]],
                [100],
                channelVariable=CHANNEL_1,
                dispenseMode=9,
            )
            cmd.tip_eject(hammy, [tips[state["current_tip"]]], waste=True)

            st.update_state(state, "current_source_well", 1)
            st.update_state(state, "current_target_well", 1)
            st.update_state(state, "current_tip", 1)

        # Otherwise, use all channels

        elif source_well_stop == CHANNELS and target_well_stop == CHANNELS:
            print(
                "Aspirating: "
                f"{[dk.index_to_string_384(w[1]) for w in source_wells[state['current_source_well'] : state['current_source_well'] + CHANNELS]]}"
                " | Dispensing: "
                f"{[dk.index_to_string_384(w[1]) for w in target_wells[state['current_target_well'] : state['current_target_well'] + CHANNELS]]}"
            )

            cmd.tip_pick_up(
                hammy, tips[state["current_tip"] : state["current_tip"] + CHANNELS]
            )
            cmd.aspirate(
                hammy,
                source_wells[
                    state["current_source_well"] : state["current_source_well"]
                    + CHANNELS
                ],
                [100],
                mixCycles=3,
                mixVolume=50.0,
            )
            cmd.dispense(
                hammy,
                target_wells[
                    state["current_target_well"] : state["current_target_well"]
                    + CHANNELS
                ],
                [100],
                dispenseMode=9,
            )
            cmd.tip_eject(
                hammy,
                tips[state["current_tip"] : state["current_tip"] + CHANNELS],
                waste=True,
            )

            st.update_state(state, "current_source_well", CHANNELS)
            st.update_state(state, "current_target_well", CHANNELS)
            st.update_state(state, "current_tip", CHANNELS)

        # Output the current state of the protocol

        print(
            f"Source well: {state['current_source_well']}/{len(source_wells)} | Target"
            f" well: {state['current_target_well']}/{len(target_wells)}"
        )
        print(
            f"Source plate: {state['current_source_plate']}/{len(source_plates)} |"
            f" Target plate: {state['current_target_plate']}/{len(target_plates)}"
        )
        print(
            f"Tip: {state['current_tip'] + 1}/{TIPS} | Tip rack:"
            f" {state['current_rack'] + 1}/{RACKS}"
        )

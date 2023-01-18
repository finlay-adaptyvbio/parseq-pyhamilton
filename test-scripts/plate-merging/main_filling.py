import json
import math
import os
import helpers as hp
import load
import actions as act
import cmd_wrappers as cmdw
import deck as dk
import datetime
import shutil
import csv
import atexit
import requests

from pyhamilton import (
    HamiltonInterface,
    LayoutManager,
    ResourceType,
    DeckResource,
    Plate96,
    Plate384,
    Lid,
    Tip96,
    Tip384,
    Reservoir300,
    INITIALIZE,
)

from pyhamilton.oemerr import ResourceUnavailableError

# -------------------------
#         NOTIFICATIONS
# -------------------------

slack_token = "xoxb-4612406885399-4627932099202-REL8YycwsJbdBKYkGJ7qeq75"
slack_channel = "#main"
slack_icon_emoji = ":see_no_evil:"
slack_user_name = "pyhamilton"


def rip(text):
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


# atexit.register(rip, "Script complete or error.")


# -------------------------
#         DECK
# -------------------------


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


# -------------------------
#         SETUP
# -------------------------

racks = 12
current_rack = 0
tips_per_rack = 96
current_tip = 0

channel_steps = 0
channels = 2
channel_1 = "10"
channel_2 = "01"

done_source_plates = 0
done_target_plates = 0
done_source_wells = 0
done_target_wells = 0
pipet = True

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

state = {
    "current_plate": "",
    "current_well": "",
    "current_step": "",
}

# -------------------------
#         ACTIONS
# -------------------------

with HamiltonInterface(simulate=True) as hammy:

    hammy.wait_on_response(hammy.send_command(INITIALIZE))

    ## Initial placement

    cmdw.grip_get(hammy, source_bact_plates[done_source_plates], mode=0, gripWidth=82.0)
    cmdw.grip_place(hammy, active_source_bact_plate, mode=0)
    cmdw.grip_get(hammy, active_source_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0)
    cmdw.grip_place(hammy, temp_source_bact_lid, mode=1)
    cmdw.grip_get(hammy, target_bact_plates[done_target_plates], mode=0, gripWidth=82.0)
    cmdw.grip_place(hammy, active_target_bact_plate, mode=0)
    cmdw.grip_get(hammy, active_target_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0)
    cmdw.grip_place(hammy, temp_target_bact_lid, mode=1, eject=True)

    source_raw_wells = [
        well[1]
        for well in wells_to_empty
        if well[0] == source_plates[done_source_plates]
    ]
    source_indexes = dk.sort_384_indexes_2channel(source_raw_wells)
    source_wells = [
        (active_source_bact_plate, dk.string_to_index_384(index))
        for index in source_indexes
    ]

    target_raw_wells = [
        well[1]
        for well in wells_to_fill
        if well[0] == target_plates[done_target_plates]
    ]
    target_indexes = dk.sort_384_indexes_2channel(target_raw_wells)
    target_wells = [
        (active_target_bact_plate, dk.string_to_index_384(index))
        for index in target_indexes
    ]

    ## Loop over plates

    while done_source_plates < len(source_plates) or done_target_plates < len(
        target_plates
    ):
        if done_source_wells >= len(source_wells):
            cmdw.grip_get(
                hammy, temp_source_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0
            )
            cmdw.grip_place(hammy, active_source_bact_lid, mode=1)
            cmdw.grip_get(
                hammy, active_source_bact_plate, mode=0, gripWidth=82.0, gripHeight=9.0
            )
            cmdw.grip_place(hammy, dest_source_bact_plates[done_source_plates], mode=0)

            done_source_plates += 1

            try:
                print(f"Source plate {source_plates[done_source_plates]} done.")

                cmdw.grip_get(
                    hammy,
                    source_bact_plates[done_source_plates],
                    mode=0,
                    gripWidth=82.0,
                )
                cmdw.grip_place(hammy, active_source_bact_plate, mode=0)
                cmdw.grip_get(
                    hammy,
                    active_source_bact_lid,
                    mode=1,
                    gripWidth=85.2,
                    gripHeight=5.0,
                )
                cmdw.grip_place(hammy, temp_source_bact_lid, mode=1, eject=True)

                source_raw_wells = [
                    well[1]
                    for well in wells_to_empty
                    if well[0] == source_plates[done_source_plates]
                ]
                source_indexes = dk.sort_384_indexes_2channel(source_raw_wells)
                source_wells = [
                    (active_source_bact_plate, dk.string_to_index_384(index))
                    for index in source_indexes
                ]
                done_source_wells = 0

            except IndexError:
                pipet = False

        if done_target_wells >= len(target_wells):
            cmdw.grip_get(
                hammy, temp_target_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0
            )
            cmdw.grip_place(hammy, active_target_bact_lid, mode=1)
            cmdw.grip_get(
                hammy, active_target_bact_plate, mode=0, gripWidth=82.0, gripHeight=9.0
            )
            cmdw.grip_place(hammy, dest_target_bact_plates[done_target_plates], mode=0)

            done_target_plates += 1

            try:
                print(f"Target plate {target_plates[done_target_plates]} done.")

                cmdw.grip_get(
                    hammy,
                    target_bact_plates[done_target_plates],
                    mode=0,
                    gripWidth=82.0,
                )
                cmdw.grip_place(hammy, active_target_bact_plate, mode=0)
                cmdw.grip_get(
                    hammy,
                    active_target_bact_lid,
                    mode=1,
                    gripWidth=85.2,
                    gripHeight=5.0,
                )
                cmdw.grip_place(hammy, temp_target_bact_lid, mode=1, eject=True)

                target_raw_wells = [
                    well[1]
                    for well in wells_to_fill
                    if well[0] == target_plates[done_target_plates]
                ]
                target_indexes = dk.sort_384_indexes_2channel(target_raw_wells)
                target_wells = [
                    (active_target_bact_plate, dk.string_to_index_384(index))
                    for index in target_indexes
                ]
                done_target_wells = 0

            except IndexError:
                pipet = False

        if current_tip >= tips_per_rack:

            print(f"Active rack done. Picking up rack {current_rack+1}/{racks}")

            cmdw.grip_get_tip_rack(hammy, active_pipet_tips)
            cmdw.grip_place_tip_rack(hammy, active_pipet_tips, waste=True)
            cmdw.grip_get_tip_rack(hammy, tip_racks[current_rack])
            cmdw.grip_place_tip_rack(hammy, active_dest_tips)

            current_rack += 1
            current_tip = 0

        if pipet:

            source_well_stop = min(
                2, len(source_wells[done_source_wells:]), (tips_per_rack - current_tip)
            )
            target_well_stop = min(
                2, len(target_wells[done_target_wells:]), (tips_per_rack - current_tip)
            )

            print(
                f"Source wells to pipet: {source_well_stop} | Target wells to pipet: {target_well_stop}"
            )

            if source_well_stop == 1 or target_well_stop == 1:

                print(
                    f"Aspirating: {dk.index_to_string_384(source_wells[done_source_wells][1])}"
                )
                print(
                    f"Dispensing: {dk.index_to_string_384(target_wells[done_target_wells][1])}"
                )

                cmdw.tip_pick_up(hammy, [tips[current_tip]], channelVariable=channel_1)
                cmdw.aspirate(
                    hammy,
                    [source_wells[done_source_wells]],
                    [100],
                    channelVariable=channel_1,
                    mixCycles=3,
                    mixVolume=50.0,
                )
                cmdw.dispense(
                    hammy,
                    [target_wells[done_target_wells]],
                    [100],
                    channelVariable=channel_1,
                    dispenseMode=9,
                )
                cmdw.tip_eject(hammy, [tips[current_tip]], waste=True)

                done_source_wells += 1
                done_target_wells += 1
                current_tip += 1

            elif source_well_stop == 2 and target_well_stop == 2:

                print(
                    f"Aspirating: {[dk.index_to_string_384(w[1]) for w in source_wells[done_source_wells : done_source_wells + 2]]}"
                )
                print(
                    f"Dispensing: {[dk.index_to_string_384(w[1]) for w in target_wells[done_target_wells : done_target_wells + 2]]}"
                )

                cmdw.tip_pick_up(hammy, tips[current_tip : current_tip + 2])
                cmdw.aspirate(
                    hammy,
                    source_wells[done_source_wells : done_source_wells + 2],
                    [100],
                    mixCycles=3,
                    mixVolume=50.0,
                )
                cmdw.dispense(
                    hammy,
                    target_wells[done_target_wells : done_target_wells + 2],
                    [100],
                    dispenseMode=9,
                )
                cmdw.tip_eject(hammy, tips[current_tip : current_tip + 2], waste=True)

                done_source_wells += 2
                done_target_wells += 2
                current_tip += 2

        print(
            f"Source well: {done_source_wells}/{len(source_wells)} | Target well: {done_target_wells}/{len(target_wells)},"
        )
        print(
            f"Source plate: {done_source_plates+1}/{len(source_plates)} | Target plate: {done_target_plates+1}/{len(target_plates)},"
        )

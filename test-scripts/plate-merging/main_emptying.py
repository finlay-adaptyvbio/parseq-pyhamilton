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


atexit.register(rip, "Script complete or error.")


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
    os.path.dirname(os.path.abspath(__file__)), "plate-merging.lay"
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

channel_steps = 0
channels = 2
channel_1 = "10"
channel_2 = "01"

current_tip = 0

plates_in_stack = len(plates)

source_bact_plates = dk.get_labware_list(
    deck,
    ["F1", "F2", "F3", "F4", "E1", "E2"],
    Plate384,
    [6, 6, 6, 6, 6, 6],
    True,
)[0:plates_in_stack]

dest_bact_plates = dk.get_labware_list(
    deck,
    ["E3", "F1", "F2", "F3", "F4", "E1", "E2"],
    Plate384,
    [6, 6, 6, 6, 6, 6, 6],
    False,
)[0:plates_in_stack]

active_bact_plate = dk.get_labware_list(deck, ["E5"], Plate384)[0]
active_bact_lid = dk.get_labware_list(deck, ["E5"], Lid)[0]
temp_bact_lid = dk.get_labware_list(deck, ["E4"], Lid)[0]

ethanol_reservoir = dk.get_labware_list(deck, ["C5"], Reservoir300)[0]
waste = dk.get_labware_list(deck, ["D1"], Reservoir300)[0]

tips_300 = dk.get_labware_list(deck, ["F5"], Tip96)[0]

tips = [(tips_300, position) for position in range(0, 96)]
bact_waste = [(waste, position) for position in range(182, 187, channels * 2)]
ethanol = [(ethanol_reservoir, position) for position in range(368, 373, channels * 2)]

discard = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "plate_merging_emptying.csv"
)

with open(discard) as f:
    reader = csv.reader(f)
    wells_to_empty = [tuple(row) for row in reader]

state = {
    "current_plate": "",
    "current_well": "",
    "current_step": "",
}

ETHANOL_ASPIRATE = "StandardVolume_EtOH_DispenseJet_Empty"
ETHANOL_DISPENSE = "StandardVolume_EtOH_DispenseJet_Part"

# -------------------------
#         ACTIONS
# -------------------------

with HamiltonInterface(simulate=True) as hammy:

    hammy.wait_on_response(hammy.send_command(INITIALIZE))

    for i, plate in enumerate(plates):

        raw_wells = [well[1] for well in wells_to_empty if well[0] == plate]

        indexes = dk.sort_384_indexes_2channel(raw_wells)

        wells = [
            (active_bact_plate, dk.string_to_index_384(index)) for index in indexes
        ]

        print(indexes)

        cmdw.grip_get(
            hammy, source_bact_plates[i], mode=0, gripWidth=82.0, gripHeight=9.0
        )
        cmdw.grip_place(hammy, active_bact_plate, mode=0)

        state.update({"current_plate": plate, "current_step": "move_to_active"})
        print(json.dumps(state))

        cmdw.grip_get(hammy, active_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0)
        cmdw.grip_place(hammy, temp_bact_lid, mode=1, eject=True)

        state.update({"current_step": "remove_lid"})
        print(json.dumps(state))

        cmdw.tip_pick_up(hammy, tips[current_tip : current_tip + 2])
        current_tip += channels

        ### Aspirate media

        for j in range(0, len(wells), 4):

            stop = min(4, len(wells[j:]))

            for k in range(0, stop, 2):

                channel_steps += 1

                if channel_steps % 58 == 0:
                    cmdw.tip_eject(
                        hammy, tips[current_tip : current_tip + 2], waste=True
                    )
                    cmdw.tip_pick_up(hammy, tips[current_tip : current_tip + 2])
                    current_tip += channels

                if k >= 2:
                    aspirateMode = 1
                else:
                    aspirateMode = 0

                if stop - k == 1:
                    cmdw.aspirate(
                        hammy,
                        [wells[j + k]],
                        [140],
                        channelVariable=channel_1,
                        aspirateMode=aspirateMode,
                        mixCycles=3,
                        mixVolume=50.0,
                        liquidHeight=0.05,
                    )

                    dispense_volume = [140 * int((k + channels) / 2), 100 * (k / 2)]

                    state.update(
                        {
                            "current_well": dk.index_to_string_384(wells[j + k][1]),
                            "current_step": "aspirate_media",
                        }
                    )
                    print(json.dumps(state))

                else:
                    cmdw.aspirate(
                        hammy,
                        wells[j + k : j + k + 2],
                        [140],
                        aspirateMode=aspirateMode,
                        mixCycles=3,
                        mixVolume=50.0,
                        liquidHeight=0.05,
                    )

                    dispense_volume = [140 * int((k + channels) / 2)]

                    state.update(
                        {
                            "current_well": dk.index_to_string_384(wells[j + k + 1][1]),
                            "current_step": "aspirate_media",
                        }
                    )
                    print(json.dumps(state))

            cmdw.dispense(hammy, bact_waste, dispense_volume, dispenseMode=9)

            state.update({"current_step": "dispense_media"})
            print(json.dumps(state))

        ### Dispense ethanol

        for j in range(0, len(wells), 6):

            stop = min(6, len(wells[j:]))

            if stop % 2 == 0:
                aspirate_volume = [100 * stop / 2]

            else:
                aspirate_volume = [100 * (stop + 1) / 2, 100 * (stop - 1) / 2]

            cmdw.aspirate(hammy, ethanol, aspirate_volume, liquidClass=ETHANOL_DISPENSE)

            state.update({"current_step": "aspirate_ethanol"})
            print(json.dumps(state))

            for k in range(0, stop, 2):

                channel_steps += 1

                if channel_steps % 58 == 0:
                    cmdw.tip_eject(
                        hammy, tips[current_tip : current_tip + 2], waste=True
                    )
                    cmdw.tip_pick_up(hammy, tips[current_tip : current_tip + 2])
                    current_tip += channels

                if stop - k == 1:
                    cmdw.dispense(
                        hammy,
                        [wells[j + k]],
                        [100],
                        channelVariable=channel_1,
                        liquidClass=ETHANOL_DISPENSE,
                    )

                    state.update(
                        {
                            "current_well": dk.index_to_string_384(wells[j + k][1]),
                            "current_step": "dispense_ethanol",
                        }
                    )
                    print(json.dumps(state))

                else:
                    cmdw.dispense(
                        hammy,
                        wells[j + k : j + k + 2],
                        [100],
                        liquidClass=ETHANOL_DISPENSE,
                    )

                    state.update(
                        {
                            "current_well": dk.index_to_string_384(wells[j + k + 1][1]),
                            "current_step": "dispense_ethanol",
                        }
                    )
                    print(json.dumps(state))

        ### Aspirate ethanol

        for j in range(0, len(wells), 4):

            stop = min(4, len(wells[j:]))

            for k in range(0, stop, 2):

                channel_steps += 1

                if channel_steps % 58 == 0:
                    cmdw.tip_eject(
                        hammy, tips[current_tip : current_tip + 2], waste=True
                    )
                    cmdw.tip_pick_up(hammy, tips[current_tip : current_tip + 2])
                    current_tip += channels

                if k >= 2:
                    aspirateMode = 1
                else:
                    aspirateMode = 0

                if stop - k == 1:
                    cmdw.aspirate(
                        hammy,
                        [wells[j + k]],
                        [140],
                        channelVariable=channel_1,
                        aspirateMode=aspirateMode,
                        liquidClass=ETHANOL_ASPIRATE,
                        mixCycles=3,
                        mixVolume=50.0,
                        liquidHeight=0.2,
                    )

                    dispense_volume = [140 * int((k + channels) / 2), 100 * (k / 2)]

                    state.update(
                        {
                            "current_well": dk.index_to_string_384(wells[j + k][1]),
                            "current_step": "aspirate_ethanol",
                        }
                    )
                    print(json.dumps(state))

                else:
                    cmdw.aspirate(
                        hammy,
                        wells[j + k : j + k + 2],
                        [140],
                        aspirateMode=aspirateMode,
                        liquidClass=ETHANOL_ASPIRATE,
                        mixCycles=3,
                        mixVolume=50.0,
                        liquidHeight=0.2,
                    )

                    dispense_volume = [140 * int((k + channels) / 2)]

                    state.update(
                        {
                            "current_well": dk.index_to_string_384(wells[j + k + 1][1]),
                            "current_step": "aspirate_ethanol",
                        }
                    )
                    print(json.dumps(state))

            cmdw.dispense(
                hammy,
                bact_waste,
                dispense_volume,
                liquidClass=ETHANOL_ASPIRATE,
                dispenseMode=9,
            )

            state.update({"current_step": "dispense_ethanol"})
            print(json.dumps(state))

        cmdw.tip_eject(hammy, tips[current_tip : current_tip + 2], waste=True)

        cmdw.grip_get(hammy, temp_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0)
        cmdw.grip_place(hammy, active_bact_lid, mode=1)

        state.update({"current_step": "place_lid"})
        print(json.dumps(state))

        cmdw.grip_get(hammy, active_bact_plate, mode=0, gripWidth=82.0, gripHeight=9.0)
        cmdw.grip_place(hammy, dest_bact_plates[i], mode=0, eject=True)

        state.update({"current_step": "move_to_done"})
        print(json.dumps(state))

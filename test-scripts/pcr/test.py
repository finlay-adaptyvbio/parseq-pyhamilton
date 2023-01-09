import json
import math
import os
import helpers as hp
import load
import actions as act
import cmd_wrappers as cmdw
import datetime
import shutil
from pyhamilton import (
    HamiltonInterface,
    LayoutManager,
    ResourceType,
    Plate384,
    Lid,
    Tip96,
    Tip384,
    INITIALIZE,
)

LAYOUT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pcr.lay")

deck = {
    "A": [
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
    ],
    "B": [
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
    ],
    "C": [
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
    ],
    "D": [
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
    ],
    "E": [
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
    ],
    "F": [
        {"level": None, "labware": None, "names": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
    ],
}


# -------------------------
#         SETUP
# -------------------------


def add_to_stack(position: tuple, stack: list):
    level = len(stack) + 1
    deck[position[0]][position[1] - 1]["labware"] = stack
    deck[position[0]][position[1] - 1]["level"] = (0, level)


def pos(position: str) -> tuple:
    return position[0], int(position[1])


def get_labware(position: tuple):
    level = deck[position[0]][position[1] - 1]["level"]
    return deck[position[0]][position[1] - 1]["labware"][level]


def update_deck(source, target):
    if (
        deck[source[0]][source[1] - 1]["level"][0]
        < deck[source[0]][source[1] - 1]["level"][1]
    ):
        deck[source[0]][source[1] - 1]["level"] += 1
    else:
        raise ValueError("No available labware at %s%i." % source)

    if (
        deck[target[0]][target[1] - 1]["level"][0]
        < deck[target[0]][target[1] - 1]["level"][1]
    ):
        deck[target[0]][target[1] - 1]["level"] += 1
    else:
        raise ValueError("No available labware at %s%i." % target)


lmgr = LayoutManager(LAYOUT_FILE_PATH)
plates_in_stack = 10
pcr_active_positions = 4
bact_active_positions = 1

### BACT PLATES ###

source_bact_lids = hp.resource_list_with_filter(
    lmgr, "SOURCE_BACT_PLATE", Lid, plates_in_stack, suffix="_lid", reverse=True
)
source_bact_plates = hp.resource_list_with_filter(
    lmgr, "SOURCE_BACT_PLATE", Plate384, plates_in_stack, reverse=True
)

dest_bact_lids = hp.resource_list_with_filter(
    lmgr, "DEST_BACT_PLATE", Lid, plates_in_stack, suffix="_lid", reverse=True
)
dest_bact_plates = hp.resource_list_with_filter(
    lmgr, "DEST_BACT_PLATE", Plate384, plates_in_stack, reverse=True
)

active_bact_lid = hp.resource_list_with_filter(
    lmgr, "ACTIVE_BACT_PLATE", Lid, bact_active_positions, suffix="_lid", reverse=True
)
active_bact_plate = hp.resource_list_with_filter(
    lmgr, "ACTIVE_BACT_PLATE", Plate384, bact_active_positions, reverse=True
)

temp_bact_lid = hp.resource_list_with_filter(
    lmgr, "TEMP_BACT_LID", Lid, bact_active_positions, reverse=True
)

### PCR PLATES ###

source_pcr_lids = hp.resource_list_with_filter(
    lmgr, "SOURCE_PCR_LID", Lid, plates_in_stack, reverse=True
)
source_pcr_plates = hp.resource_list_with_filter(
    lmgr, "SOURCE_PCR_PLATE", Plate384, plates_in_stack, reverse=True
)

dest_pcr_lids = hp.resource_list_with_filter(
    lmgr, "DEST_PCR_PLATE", Lid, plates_in_stack, suffix="_lid", reverse=True
)
dest_pcr_plates = hp.resource_list_with_filter(
    lmgr, "DEST_PCR_PLATE", Plate384, plates_in_stack, reverse=True
)

active_pcr_lids = hp.resource_list_with_filter(
    lmgr, "ACTIVE_PCR_PLATE", Lid, pcr_active_positions, suffix="_lid", reverse=True
)
active_pcr_plates = hp.resource_list_with_filter(
    lmgr, "ACTIVE_PCR_PLATE", Plate384, pcr_active_positions, reverse=True
)

### ACTIONS ###

plates = 8
stack_index = plates_in_stack - plates

# with HamiltonInterface(simulate=True) as hammy:

#     hammy.wait_on_response(hammy.send_command(INITIALIZE))

#     for i in range(stack_index, plates_in_stack, pcr_active_positions):
#         for j in range(0, pcr_active_positions):
#             cmdw.move_plate(
#                 hammy, source_pcr_plates[i + j], active_pcr_plates[j], gripHeight=5.0
#             )

#         for j in range(0, pcr_active_positions):
#             cmdw.move_plate(hammy, source_bact_plates[i + j], active_bact_plate[0])
#             cmdw.move_lid(hammy, active_bact_lid[0], temp_bact_lid[0], gripHeight=3.0)

#             cmdw.move_lid(hammy, temp_bact_lid[0], active_bact_lid[0], gripHeight=3.0)
#             cmdw.move_plate(
#                 hammy,
#                 active_bact_plate[0],
#                 dest_bact_plates[plates_in_stack - (i + j) + 1],
#             )

#         for j in range(0, pcr_active_positions):
#             cmdw.move_lid(
#                 hammy, source_pcr_lids[i + j], active_pcr_lids[j], gripHeight=3.0
#             )
#             cmdw.move_plate(
#                 hammy,
#                 active_pcr_plates[j],
#                 dest_pcr_plates[plates_in_stack - (i + j) + 1],
#                 gripHeight=5.0,
#             )

import logging, itertools, string
import pandas as pd

import labware as lw

from pyhamilton import (
    LayoutManager,
    ResourceType,
    Lid,  # type: ignore
    Plate96,
    Plate384,
    Tip96,
    Tip384,  # type: ignore
    Reservoir300,  # type: ignore
    EppiCarrier24,  # type: ignore
)

from pyhamilton.oemerr import ResourceUnavailableError

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

TYPES = {
    "Lid": Lid,
    "Plate96": Plate96,
    "Plate384": Plate384,
    "Tip96": Tip96,
    "Tip384": Tip384,
    "Reservoir300": Reservoir300,
    "EppiCarrier24": EppiCarrier24,
}

DECK = {
    "A": [
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
    ],
    "B": [
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
    ],
    "C": [
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
    ],
    "D": [
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
    ],
    "E": [
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
    ],
    "F": [
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
        {"labware": None, "frame": None},
    ],
}


def get_deck(layout_file_path: str) -> dict:
    logger.debug(f"Getting deck from: {layout_file_path}")
    lmgr = LayoutManager(layout_file_path)

    deck = parse_layout_file(DECK, lmgr)
    deck = clean_deck(deck)
    # print_deck(deck)

    return deck


def parse_layout_file(deck: dict, lmgr: LayoutManager) -> dict:
    logger.debug(f"Parsing layout file...")
    for col in deck.keys():
        for row in range(len(deck[col])):
            position = col + str(row + 1)
            resource_list = []

            for resource in TYPES.values():
                resource_test = lambda line: extract_resource_from_field(
                    LayoutManager.name_from_line(line), resource, position
                )
                resource_type = ResourceType(
                    resource, resource_test, LayoutManager.name_from_line
                )
                while True:
                    try:
                        resource_list.append(
                            LayoutManager.assign_unused_resource(
                                lmgr, resource_type, reverse=False
                            )
                        )
                    except ResourceUnavailableError:
                        logger.debug(f"Resource {resource} not found in {position}.")
                        break

            deck[col][row]["labware"] = resource_list

    return deck


def clean_deck(deck: dict) -> dict:
    logger.debug(f"Cleaning deck...")
    for col in deck.keys():
        for row in range(len(deck[col])):
            ghost_labware = []
            stack = False
            for idx, labware in enumerate(deck[col][row]["labware"]):
                if labware.layout_name().count("0") > 2:
                    stack = True
                else:
                    ghost_labware.append(idx)
            if stack:
                logger.debug(f"Column: {col}, Row: {row}, Ghosts: {ghost_labware}")
                for shift, idx in enumerate(ghost_labware):
                    del deck[col][row]["labware"][idx - shift]
    return deck


def add_dataframes(deck: dict) -> dict:
    logger.debug(f"Adding dataframes to labware...")
    for col in deck.keys():
        for row in range(len(deck[col])):
            frames = []
            for labware in deck[col][row]["labware"]:
                frame = lw.assign_labware(labware)
                frames.append(frame)
            deck[col][row]["frame"] = frames

    return deck


def print_deck(deck: dict):
    logger.debug(f"Printing deck...")
    for col in deck.keys():
        for row in range(0, len(deck[col])):
            position = col + str(row + 1)
            if len(deck[col][row]["labware"]) > 0:
                print(f"--- {position} ---")

                for labware in deck[col][row]["labware"]:
                    print(f"{labware.layout_name()[3:]}")


def get_labware_list(
    deck: dict,
    positions: list[str],
    labware_type,  # : Union[Lid, Plate96, Plate384, Tip384, Tip96, Reservoir300],
    n: list[int] = [1],
    reverse: bool = False,
):
    labwares_merged = []
    for idx, position in enumerate(positions):
        col, row = position[0], int(position[1])
        labwares = [
            labware
            for labware in deck[col][row - 1]["labware"]
            if type(labware) == labware_type
        ][: n[idx]]

        if reverse:
            labwares.reverse()

        labwares_merged.extend(labwares)

    return labwares_merged


def extract_resource_from_field(field, resource, position):
    if resource == Lid:
        if field.startswith(position) and field.find("_lid") > 0:
            return True
        else:
            return False

    elif resource == Plate384:
        if field.startswith(position) and field.find("_plate384") > 0:
            return True
        else:
            return False

    elif resource == Plate96:
        if field.startswith(position) and field.find("_plate96") > 0:
            return True
        else:
            return False

    elif resource == Tip384:
        if field.startswith(position) and field.find("_tip384") > 0:
            return True
        else:
            return False

    elif resource == Tip96:
        if field.startswith(position) and field.find("_tip96") > 0:
            return True
        else:
            return False

    elif resource == Reservoir300:
        if field.startswith(position) and field.find("_reservoir300") > 0:
            return True
        else:
            return False

    elif resource == EppiCarrier24:
        if field.startswith(position) and field.find("_eppi24") > 0:
            return True
        else:
            return False

    else:
        return False

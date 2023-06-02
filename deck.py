import logging, sys, shelve

import labware as lw

from pyhamilton import LayoutManager, ResourceType, Plate96, Plate384, Tip96
from labware import Tip384, Reservoir300, Lid, EppiCarrier24

from pyhamilton.oemerr import ResourceUnavailableError

# Logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# Class mapping
TYPES = {
    "Lid": Lid,
    "Plate96": Plate96,
    "Plate384": Plate384,
    "Tip96": Tip96,
    "Tip384": Tip384,
    "Reservoir300": Reservoir300,
    "EppiCarrier24": EppiCarrier24,
}

# Empty deck dictionary in dict["Column": list[rows]] format
# labware list for PyHamilton objects
# frame list for DataFrames provided by labware module
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
    """Get deck from provided layout file. Returns deck dictionary.

    Args:
        - layout_file_path: Path to layout file.

    Returns:
        - dict: Deck dictionary with labware.
    """
    logger.debug(f"Getting deck from: {layout_file_path}")
    lmgr = LayoutManager(layout_file_path)

    deck = parse_layout_file(DECK, lmgr)
    deck = clean_deck(deck)

    return deck


def parse_layout_file(deck: dict, lmgr: LayoutManager) -> dict:
    """
    Parse provided layout file, extracting valid labware into default deck dictionary.
    Labware in layout file must named according to scheme provided in documentation.

    Args:
        - deck: Empty deck dictionary.
        - lmgr: LayoutManager object.

    Returns:
        - dict: Deck dictionary with labware.
    """
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
    """
    Layout files can contain non-existent labware (especially in stacks).
    This function finds and removes 'ghost' labware.

    Args:
        - deck: Deck dictionary with labware.

    Returns:
        - dict: Cleaned deck dictionary with labware.
    """
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
    """
    Assign labware classes (DataFrame wrapper) to objects in deck.

    Args:
        - deck: Deck dictionary with labware.

    Returns:
        - dict: Deck dictionary with labware and dataframes.
    """
    logger.debug(f"Adding dataframes to labware...")
    for col in deck.keys():
        for row in range(len(deck[col])):
            frames = []
            for labware in deck[col][row]["labware"]:
                frame = lw.assign_labware(labware)
                frames.append(frame)
            deck[col][row]["frame"] = frames

    return deck


def print_deck(shelf: shelve.Shelf | dict) -> None:
    """Convenience function to print deck and its contents in a nicely formatted layout.

    Args:
        - shelf: Shelf or dictionary with deck contents.
    """
    logger.debug(f"Printing deck...")
    for col in shelf.keys():
        for row in range(0, len(shelf[col])):
            position = col + str(row + 1)
            if len(shelf[col][row]["labware"]) > 0:
                print(f"--- {position} ---")

                for labware in shelf[col][row]["labware"]:
                    print(f"{labware.layout_name()[3:]}")


def delete_lids(shelf: shelve.Shelf, position: str) -> None:
    """
    Deletes lids from stacks of plates with lids.
    Lids in plate stacks are not used for transport and cause issues in indexing.

    Args:
        - shelf: Shelf with deck contents.
        - position: Deck position to delete lids from.
    """
    logger.debug(f"Deleting lids from {position}.")
    try:
        letter, number = lw.pos(position)
        for t in list(
            zip(shelf[letter][number]["labware"], shelf[letter][number]["frame"])
        )[::-1]:
            if isinstance(t[0], Lid) and isinstance(t[1], lw.lid):
                shelf[letter][number]["labware"].remove(t[0])
                shelf[letter][number]["frame"].remove(t[1])
    except Exception as e:
        logger.exception(e)
        sys.exit()


def delete_unused(shelf: shelve.Shelf, position: str, n: int) -> None:
    """Delete n labware for a provided deck position.

    Args:
        - shelf: Shelf with deck contents.
        - position: Deck position to delete labware from.
        - n: Number of labware to delete."""
    logger.debug(f"Deleting {n} labware from {position}.")
    if n != 0:
        try:
            letter, number = lw.pos(position)
            for k in shelf[letter][number]:
                del shelf[letter][number][k][-n:]
        except:
            sys.exit()


def delete_labware(shelf: shelve.Shelf, labware):
    """Delete specific labware from deck by finding it in provided shelf.

    Args:
        - shelf: Shelf with deck contents.
        - labware: Labware to delete from deck.
    """
    logger.debug(f"Deleting {labware.layout_name()} from deck.")
    for col in shelf.keys():
        for row in range(0, len(shelf[col])):
            if len(shelf[col][row]["labware"]) > 0:
                if labware in shelf[col][row]["labware"]:
                    shelf[col][row]["labware"].remove(labware)


def extract_resource_from_field(field, resource, position) -> bool:
    """Check if a labware of provided type exists at a position.

    Args:
        - field: Field name from layout file.
        - resource: Labware type to check for.

    Returns:
        - bool: True if labware of provided type exists at position, False otherwise."""
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

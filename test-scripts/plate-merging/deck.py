from pyhamilton import (
    LayoutManager,
    ResourceType,
    DeckResource,
    Lid,
    Plate96,
    Plate384,
    Tip384,
    Tip96,
    Reservoir300,
)

from pyhamilton.oemerr import ResourceUnavailableError
from typing import Union


def parse_layout_file(deck: dict, lmgr: LayoutManager, types: dict):
    for col in deck.keys():
        for row in range(0, len(deck[col])):
            position = col + str(row + 1)
            resource_list = []

            for resource in types.values():
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
                        break

            deck[col][row]["labware"] = resource_list

            deck[col][row]["state"] = [
                (f"name_{i}", 0) for i in range(0, len(resource_list))
            ]


def print_deck(deck: dict):
    for col in deck.keys():
        for row in range(0, len(deck[col])):
            position = col + str(row + 1)
            print(f"--- {position} ---")

            for idx, labware in enumerate(deck[col][row]["labware"]):
                state = deck[col][row]["state"][idx]
                print(labware.layout_name(), type(labware), state)


def assign_to_stack(deck: dict, position: str, stack: list):
    level = len(stack) + 1
    col, row = pos(position)
    deck[col][row - 1]["labware"] = stack
    deck[col][row - 1]["level"] = (0, level)


def pos(position: str) -> tuple:
    return position[0], int(position[1])


def string_to_index(position: str) -> int:
    alphabet = "ABCDEFGHIJKLMNOP"
    return alphabet.index(position[0]) + (int(position[1:]) - 1) * 16


def index_to_string(position: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOP"
    x, y = int(position) // 16, int(position) % 16
    return alphabet[y] + str(x + 1)


def sort_well_indexes_col(indexes: list[int], channels: int) -> list:
    indexes_set = set(indexes)

    pairs = [(x, y) for x in indexes if (y := channels + x) in indexes_set and x < y]

    s = set()

    unique_pairs = [(x, y) for x, y in pairs if not (x in s or s.add(y))]

    sorted_indexes = [w for t in unique_pairs for w in t]
    unsorted_indexes = [w for w in indexes if w not in sorted_indexes]

    return sorted_indexes + unsorted_indexes


def sort_well_indexes(wells: list[tuple]) -> list:
    sorted_wells = []
    alphabet = "ABCDEFGHIJKLMNOP"

    wells = sorted(wells, key=lambda x: int(x[1][-2:]))

    for col in range(1, 25):
        rows = [well for well in wells if int(well[1][-2:]) == col]

        row_indexes = [alphabet.index(row[1][0]) for row in rows]

        sorted_row_indexes = sort_well_indexes_col(row_indexes, 4)
        sorted_rows = [alphabet[row] + str(col) for row in sorted_row_indexes]
        sorted_wells.extend(sorted_rows)

    return sorted_wells


def get_labware_list(
    deck: dict,
    positions: list[str],
    labware_type,  # : Union[Lid, Plate96, Plate384, Tip384, Tip96, Reservoir300],
    n: list[int] = [1],
    reverse: bool = False,
):
    labwares_merged = []
    for idx, position in enumerate(positions):
        col, row = pos(position)
        labwares = [
            labware
            for labware in deck[col][row - 1]["labware"]
            if type(labware) == labware_type
        ][: n[idx]]

        if reverse:
            labwares.reverse()

        labwares_merged.extend(labwares)

    return labwares_merged


def assign_labels(deck: dict, position: str):
    col, row = pos(position)
    names = []
    for labware in deck[col][row - 1]["labware"]:
        if isinstance(labware, (Plate96, Plate384)):
            while True:
                label = input(f"Label for {labware.layout_name()}: ")

                try:
                    names.append(str(label))
                except:
                    continue

                break

    deck[col][row - 1]["names"] = names


def get_labware(deck: dict, labware):
    for col, l in deck.items():
        for row, d in enumerate(l):
            for level, r in enumerate(d["labware"]):
                if labware == r:
                    return col, row, level


def update_deck(deck: dict, source, target):

    source_col, source_row, source_level = get_labware(deck, source)
    target_col, target_row, target_level = get_labware(deck, target)

    source_name = deck[source_col][source_row]["state"][source_level]
    target_name = deck[target_col][target_row]["state"][target_level]

    deck[source_col][source_row]["state"][source_level][0] = target_name
    deck[target_col][target_row]["state"][target_level][0] = source_name

    deck[source_col][source_row]["state"][source_level][0] = target_name
    deck[target_col][target_row]["state"][target_level][0] = source_name

    deck[source_col][source_row]["level"][0] += 1
    deck[target_col][target_row]["level"][0] += 1


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

    else:
        return False

from pyhamilton import (
    LayoutManager,
    ResourceType,
    Lid,
    Plate96,
    Plate384,
    Tip96,
    Tip384,
    Reservoir300,
    EppiCarrier24,
)

from pyhamilton.oemerr import ResourceUnavailableError
from typing import Union

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
    ],
    "C": [
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
    ],
    "E": [
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
    ],
    "F": [
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
        {"level": None, "labware": None},
    ],
}


def get_deck(layout_file_path: str) -> dict:
    lmgr = LayoutManager(layout_file_path)

    deck = parse_layout_file(DECK, lmgr)
    deck = clean_deck(deck)
    print_deck(deck)

    return deck


def parse_layout_file(deck: dict, lmgr: LayoutManager) -> dict:
    for col in deck.keys():
        for row in range(0, len(deck[col])):
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
                        break

            deck[col][row]["labware"] = resource_list

    return deck


def clean_deck(deck: dict) -> dict:
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
                print(ghost_labware)
                for shift, idx in enumerate(ghost_labware):
                    del deck[col][row]["labware"][idx - shift]
    return deck


def print_deck(deck: dict):
    for col in deck.keys():
        for row in range(0, len(deck[col])):
            position = col + str(row + 1)
            print(f"--- {position} ---")

            for labware in deck[col][row]["labware"]:
                print(labware.layout_name(), type(labware))


def print_list(labwares: list):
    for labware in labwares:
        print(labware.layout_name())


def assign_to_stack(deck: dict, position: str, stack: list):
    level = len(stack) + 1
    col, row = pos(position)
    deck[col][row - 1]["labware"] = stack
    deck[col][row - 1]["level"] = (0, level)


def pos(position: str) -> tuple:
    return position[0], int(position[1])


def string_to_index_384(position: str) -> int:
    alphabet = "ABCDEFGHIJKLMNOP"
    return alphabet.index(position[0]) + (int(position[1:]) - 1) * 16


def index_to_string_384(position: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOP"
    x, y = int(position) // 16, int(position) % 16
    return alphabet[y] + str(x + 1)


def string_to_index_96(position: str) -> int:
    alphabet = "ABCDEFGH"
    return alphabet.index(position[0]) + (int(position[1:]) - 1) * 8


def index_to_string_96(position: int) -> str:
    alphabet = "ABCDEFGH"
    x, y = int(position) // 8, int(position) % 8
    return alphabet[y] + str(x + 1)


def pos_96_in_384(quadrant: int):
    pos = []
    if quadrant == 1:
        q1, q2 = 1, 0
    elif quadrant == 2:
        q1, q2 = 0, 1
    elif quadrant == 3:
        q1, q2 = 1, 1
    else:
        q1, q2 = 0, 0

    for i in range(0 + q1, 24 + q1, 2):
        for j in range(1 + q2, 17 + q2, 2):
            pos.append(j + i * 16 - 1)
    return pos


def pos_2ch(stop: int, start: int = 0):
    pos = []
    for i in range(start, stop - 1, 2):
        pos.append(i)
    for j in range(start + 1, stop, 2):
        pos.append(j)
    return pos


def pos_96_rev():
    pos = []
    for i in range(12):
        col = []
        for j in range(8):
            col.append((12 - i) * 8 - j - 1)
        col.reverse()
        pos.extend(col)
    return pos


def sort_384_indexes_2channel(unsorted_indexes: list[str]) -> list[str]:
    sorted_cols = []
    unsorted_cols = []

    rows = "ABCDEFGHIJKLMNOP"

    unsorted_indexes_set = set(unsorted_indexes)
    unsorted_indexes_by_col = sorted(unsorted_indexes, key=lambda x: int(x[1:]))

    for col in range(1, 25):
        col_indexes = [
            col_index
            for col_index in unsorted_indexes_by_col
            if int(col_index[1:]) == col
        ]
        row_indexes = [rows.index(row[0]) for row in col_indexes]
        row_indexes_set = set(row_indexes)

        pairs_set = set()
        pairs = [
            (x, y) for x in row_indexes if (y := x + 4) in row_indexes_set and x < y
        ]
        unique_pairs = [
            (x, y) for x, y in pairs if not (x in pairs_set or pairs_set.add(y))
        ]

        sorted_row_indexes = [i for t in unique_pairs for i in t]
        unsorted_row_indexes = [i for i in row_indexes if i not in sorted_row_indexes]

        sorted_rows = [rows[row] + str(col) for row in sorted_row_indexes]
        unsorted_rows = [rows[row] + str(col) for row in unsorted_row_indexes]

        sorted_cols.extend(sorted_rows)
        unsorted_cols.extend(unsorted_rows)

    return sorted_cols + unsorted_cols


def sort_96_indexes_2channel(unsorted_indexes: list[str]) -> list[str]:
    sorted_cols = []
    unsorted_cols = []

    rows = "ABCDEFGH"

    unsorted_indexes_set = set(unsorted_indexes)
    unsorted_indexes_by_col = sorted(unsorted_indexes, key=lambda x: int(x[1:]))

    for col in range(1, 13):
        col_indexes = [
            col_index
            for col_index in unsorted_indexes_by_col
            if int(col_index[1:]) == col
        ]
        row_indexes = [rows.index(row[0]) for row in col_indexes]
        row_indexes_set = set(row_indexes)

        pairs_set = set()
        pairs = [
            (x, y) for x in row_indexes if (y := x + 2) in row_indexes_set and x < y
        ]
        unique_pairs = [
            (x, y) for x, y in pairs if not (x in pairs_set or pairs_set.add(y))
        ]

        sorted_row_indexes = [i for t in unique_pairs for i in t]
        unsorted_row_indexes = [i for i in row_indexes if i not in sorted_row_indexes]

        sorted_rows = [rows[row] + str(col) for row in sorted_row_indexes]
        unsorted_rows = [rows[row] + str(col) for row in unsorted_row_indexes]

        sorted_cols.extend(sorted_rows)
        unsorted_cols.extend(unsorted_rows)

    return sorted_cols + unsorted_cols


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

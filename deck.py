import logging, itertools, string
import pandas as pd

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
from typing import Union

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
    logger.debug(f"Getting deck from: {layout_file_path}")
    lmgr = LayoutManager(layout_file_path)

    deck = parse_layout_file(DECK, lmgr)
    deck = clean_deck(deck)
    # print_deck(deck)

    return deck


def parse_layout_file(deck: dict, lmgr: LayoutManager) -> dict:
    logger.debug(f"Parsing layout file...")
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


def print_deck(deck: dict):
    logger.debug(f"Printing deck...")
    for col in deck.keys():
        for row in range(0, len(deck[col])):
            position = col + str(row + 1)
            if len(deck[col][row]["labware"]) > 0:
                print(f"--- {position} ---")

                for labware in deck[col][row]["labware"]:
                    print(labware.layout_name()[3:])


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


def pos_96_2ch(stop: int, start: int = 0):
    pos = []
    for i in range(2):
        for j in range(start + i, stop, 2):
            pos.append(j)
    return pos


def pos_96_2row_2ch(start: int = 0, stop: int = 96):
    index = [i for j in range(4) for i in range(j, 96, 4)]
    return index[start:stop]


def pos_96_2row(start: int = 0, stop: int = 96):
    index = [[i for i in range(j, 96, 8)] for j in range(0, 8, 4)]
    sep = int((stop - start + 1) / 2)
    return index[0][start:sep] + index[1][start : stop - sep]


def pos_96_1row(start: int = 0, stop: int = 96):
    index = [i for j in range(8) for i in range(j, 96, 8)]
    return index[start:stop]


def pos_24_2row_2ch(stop: int, start: int = 0):
    pos = []
    for i in range(6):
        for j in range(start + i, stop, 6):
            pos.append(j)
    return pos


def pos_384_2ch(stop: int, start: int = 0):
    pos = []
    for i in range(5):
        for j in range(start + i, stop, 5):
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

    unsorted_indexes_by_col = sorted(unsorted_indexes, key=lambda x: int(x[1:]))

    for col in range(1, 25):
        col_indexes = [
            col_index
            for col_index in unsorted_indexes_by_col
            if int(col_index[1:]) == col
        ]
        row_indexes = [rows.index(row[0]) for row in col_indexes]

        pairs = [
            pair
            for pair in itertools.combinations(row_indexes, 2)
            if abs(pair[0] - pair[1]) >= 4
        ]
        pairs_sorted = sorted(pairs, key=lambda x: x[1])
        pairs_unique = []

        while pairs_sorted:
            pair = pairs_sorted[0]
            pairs_sorted.remove(pair)
            pairs_unique.append(pair)
            pairs_sorted = [
                p for p in pairs_sorted if p[0] not in pair and p[1] not in pair
            ]

        sorted_row_indexes = [i for t in pairs_unique for i in t]
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

    unsorted_indexes_by_col = sorted(unsorted_indexes, key=lambda x: int(x[1:]))

    for col in range(1, 13):
        col_indexes = [
            col_index
            for col_index in unsorted_indexes_by_col
            if int(col_index[1:]) == col
        ]
        row_indexes = [rows.index(row[0]) for row in col_indexes]

        pairs = [
            pair
            for pair in itertools.combinations(row_indexes, 2)
            if abs(pair[0] - pair[1]) >= 4
        ]
        pairs_sorted = sorted(pairs, key=lambda x: x[1])
        pairs_unique = []

        while pairs_sorted:
            pair = pairs_sorted[0]
            pairs_sorted.remove(pair)
            pairs_unique.append(pair)
            pairs_sorted = [
                p for p in pairs_sorted if p[0] not in pair and p[1] not in pair
            ]

        sorted_row_indexes = [i for t in pairs_unique for i in t]
        unsorted_row_indexes = [i for i in row_indexes if i not in sorted_row_indexes]

        sorted_rows = [rows[row] + str(col) for row in sorted_row_indexes]
        unsorted_rows = [rows[row] + str(col) for row in unsorted_row_indexes]

        sorted_cols.extend(sorted_rows)
        unsorted_cols.extend(unsorted_rows)

    return sorted_cols + unsorted_cols


def sort_list(row_indexes, sep):
    pairs = [
        pair
        for pair in itertools.combinations(row_indexes, 2)
        if abs(pair[0] - pair[1]) >= sep
    ]
    pairs_sorted = sorted(pairs, key=lambda x: x[1])
    pairs_unique = []

    while pairs_sorted:
        pair = pairs_sorted[0]
        pairs_sorted.remove(pair)
        pairs_unique.append(pair)
        pairs_sorted = [
            p for p in pairs_sorted if p[0] not in pair and p[1] not in pair
        ]

    sorted_row_indexes = [i for t in pairs_unique for i in t]
    unsorted_row_indexes = [i for i in row_indexes if i not in sorted_row_indexes]

    return sorted_row_indexes + unsorted_row_indexes


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


default_index_96 = pd.DataFrame(
    [[i for i in range(j, 96, 8)] for j in range(8)],
    index=list(string.ascii_uppercase)[:8],
    columns=range(1, 13),
)

default_index_384 = pd.DataFrame(
    [[i for i in range(j, 384, 16)] for j in range(16)],
    index=list(string.ascii_uppercase)[:16],
    columns=range(1, 25),
)


class tip_384:
    def __init__(
        self, rack: Tip384, positions: list[str], current_tip: int = 0
    ) -> None:
        self.rack = rack
        self.positions = positions
        self._frame = pd.DataFrame(
            index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )
        for position in positions:
            letter, number = position[0], int(position[1:])
            self._frame.loc[letter, number] = 1

        self.original = self._frame.copy()

        self.current_tips = len(positions)
        self.current_tip = current_tip

    def reset_frame(self):
        self._frame = self.original

    def frame(self):
        return self._frame.fillna(0)

    def tips(self):
        return self._frame.sum().sum()

    def get_rows_384mph(self, rows: int = 1) -> list[tuple[Tip384, int]]:
        row = self._frame.T[self._frame.T.sum(axis=1) >= rows].last_valid_index()
        try:
            mask = self._frame.loc[:, row] == 1
        except KeyError as e:
            logger.error(f"Not enough tips in {self.rack.layout_name()}")
            exit()
        index = default_index_384.loc[:, row][mask].tolist()[-rows:]

        self._frame[default_index_384.isin(index)] = pd.NA

        tips = [(self.rack, tip) for tip in index]

        return tips

    def get_columns_384mph(self, columns: int = 1) -> list[tuple[Tip384, int]]:
        column = self._frame[self._frame.sum(axis=1) >= columns].last_valid_index()
        try:
            mask = self._frame.loc[column, :] == 1
        except KeyError as e:
            logger.error(f"Not enough tips in {self.rack.layout_name()}")
            exit()
        index = default_index_384.loc[column, :][mask].tolist()[-columns:]

        self._frame[default_index_384.isin(index)] = pd.NA

        tips = [(self.rack, tip) for tip in index]

        return tips


class plate_384:
    def __init__(
        self, plate: Plate384, positions: list[str] = [], current_well: int = 0
    ) -> None:
        self.plate = plate
        if not positions:
            positions = [
                f"{letter}{number}"
                for letter in list(string.ascii_uppercase)[:16]
                for number in range(1, 25)
            ]
        self.positions = positions
        self._frame = pd.DataFrame(
            index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )
        for position in positions:
            letter, number = position[0], int(position[1:])
            self._frame.loc[letter, number] = 1

        self.original = self._frame.copy()

        self.current_wells = len(positions)
        self.current_well = current_well

    def reset_frame(self):
        self._frame = self.original.copy()

    def frame(self):
        return self._frame.fillna(0)

    def wells(self):
        return self._frame.sum().sum()

    def get_wells_2ch(self, n: int = 2) -> list[tuple[Plate384, int]]:
        """Get wells from a 384 well plate in 2 channel mode."""
        if self.current_well == self.current_wells:
            self.current_well = 0
            self.reset_frame()

        column = default_index_384.T[self._frame.sum(axis=0) >= n].first_valid_index()

        for _ in range(2):
            try:
                row = self._frame.T.loc[column] == 1
            except KeyError as e:
                logger.debug(
                    f"Column with {n} wells not found in {self.plate.layout_name()},"
                    " trying again with 1 well."
                )
                column = default_index_384.T[
                    self._frame.sum(axis=0) >= 1
                ].first_valid_index()
                continue
            else:
                break
        else:
            exit()

        index = sort_list(default_index_384.T.loc[column, row].tolist(), 4)[:n]
        self._frame[default_index_384.isin(index)] = 0
        self.current_well += n

        wells = [(self.plate, well) for well in index]
        return wells

    def get_wells_384mph(
        self, rows: int = 1, columns: int = 1
    ) -> list[tuple[Plate384, int]]:
        if self.current_well == self.current_wells:
            self.current_well = 0
            self.reset_frame()

        row_frame = self._frame[self._frame.sum(axis=1) >= columns].dropna(
            axis=1, how="any"
        )
        column_frame = row_frame.T[(row_frame.T.sum(axis=1) >= rows)].T
        mask = column_frame.iloc[:rows, :columns] == 1
        index = (
            default_index_384[mask]
            .convert_dtypes()
            .dropna(axis=1, how="all")
            .dropna(axis=0, how="all")
            .values.flatten()
        )
        try:
            index[-1]
        except IndexError as e:
            logger.error(f"Not enough wells in {self.plate.layout_name()}")
            exit()
        self._frame[default_index_384.isin(index)] = pd.NA
        self.current_well += rows * columns

        wells = [(self.plate, well) for well in index]

        return wells

    def static_wells(self, well_list: list[str]):
        """Get specific wells from input list."""
        wells = [
            (self.plate, default_index_384.loc[well[0], int(well[1:])])
            for well in well_list
        ]

        return wells


class rack_stack:
    def __init__(self, stack) -> None:
        self.stack = stack
        self.starting_racks = len(stack)
        self.remaining_racks = len(stack)

    def get_rack(self):
        current_rack = self.starting_racks - self.remaining_racks
        rack = self.stack[current_rack]
        self.remaining_racks -= 1
        return rack

    def reset_rack(self, current_rack):
        self.current_rack = current_rack

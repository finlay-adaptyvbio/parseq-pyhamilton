import logging, itertools, string, sys
import pandas as pd

from pyhamilton import (
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

import deck as dk

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

default_index_24 = pd.DataFrame(
    [[i for i in range(j, 24, 6)] for j in range(6)],
    columns=list(string.ascii_uppercase)[:4],
    index=range(1, 7),
).T

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


def string_to_index_24(position: str) -> int:
    alphabet = "ABCD"
    return alphabet.index(position[0]) + (int(position[1:]) - 1) * 4


def index_to_string_24(position: int) -> str:
    alphabet = "ABCD"
    x, y = int(position) // 4, int(position) % 4
    return alphabet[y] + str(x + 1)


def pos_row_column_384(n: int = 384) -> list:
    return [
        f"{letter}{number}"
        for number in range(1, 25)
        for letter in list(string.ascii_uppercase)[:16]
    ][:n]


def pos_column_row_384(n: int = 384) -> list:
    pos = [
        f"{letter}{number}"
        for letter in list(string.ascii_uppercase)[:16]
        for number in range(1, 25)
    ][:n]
    return pos


def pos_row_column_96(n: int = 96) -> list:
    return [
        f"{letter}{number}"
        for number in range(1, 13)
        for letter in list(string.ascii_uppercase)[:8]
    ][:n]


def pos_column_row_96(n: int = 96) -> list:
    pos = [
        f"{letter}{number}"
        for letter in list(string.ascii_uppercase)[:8]
        for number in range(1, 13)
    ][:n]
    return pos


def pos_row_column_24(n: int = 24) -> list:
    return [
        f"{letter}{number}"
        for number in range(1, 7)
        for letter in list(string.ascii_uppercase)[:4]
    ][:n]


def pos_column_row_24(n: int = 24) -> list:
    pos = [
        f"{letter}{number}"
        for letter in list(string.ascii_uppercase)[:4]
        for number in range(1, 7)
    ][:n]
    return pos


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


def sort_list(indexes, sep):
    pairs = [
        pair
        for pair in itertools.combinations(indexes, 2)
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

    sorted_indexes = [i for t in pairs_unique for i in t]
    unsorted_indexes = [i for i in indexes if i not in sorted_indexes]

    return sorted_indexes + unsorted_indexes


class tip_384:
    def __init__(
        self,
        rack: Tip384,
        positions: Union[list[str], list[int]] = [],
        current_tip: int = 0,
    ) -> None:
        self.rack = rack
        self._frame = pd.DataFrame(
            index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )

        if not positions:
            self.positions = [i for i in range(384)]
        else:
            self.positions = positions

        if isinstance(self.positions, list) and all(
            isinstance(i, int) for i in self.positions
        ):
            self.positions = [index_to_string_384(i) for i in self.positions]

        for position in self.positions:
            letter, number = position[0], int(position[1:])
            self._frame.loc[letter, number] = 1

        self.original = self._frame.copy()

        self.current_tips = len(positions)
        self.current_tip = current_tip

    def reset(self):
        self._frame = self.original.copy()

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
        self,
        deck,
        plate: str,
        positions: Union[list[str], list[int]] = [],
        current_well: int = 0,
    ) -> None:
        self.plate = dk.get_labware_list(deck, [plate], Plate384)[0]
        self._frame = pd.DataFrame(
            index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )

        if not positions:
            self.positions = [i for i in range(384)]
        else:
            self.positions = positions

        if isinstance(self.positions, list) and all(
            isinstance(i, int) for i in self.positions
        ):
            self.positions = [index_to_string_384(i) for i in self.positions]

        for position in self.positions:
            letter, number = position[0], int(position[1:])
            self._frame.loc[letter, number] = 1

        self.original = self._frame.copy()

        self.current_wells = len(positions)
        self.current_well = current_well

    def reset(self):
        self._frame = self.original.copy()

    def frame(self):
        return self._frame.fillna(0)

    def wells(self):
        return self._frame.sum().sum()

    def get_wells_2ch(self, n: int = 2) -> list[tuple[Plate384, int]]:
        """Get wells from a 384 well plate in 2 channel mode."""
        if self.current_well == self.current_wells:
            self.current_well = 0
            self.reset()

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
            logger.error(f"Not enough wells in {self.plate.layout_name()}.")
            exit()

        index = sort_list(default_index_384.T.loc[column, row].tolist(), 4)[:n]
        self._frame[default_index_384.isin(index)] = 0
        self.current_well += n

        wells = [(self.plate, well) for well in index]
        return wells

    def get_wells_384mph(
        self, rows: int = 1, columns: int = 1
    ) -> list[tuple[Plate384, int]]:
        """Get wells from a 384 well plate in 384 multi-probe head mode."""
        if self.current_well == self.current_wells:
            self.current_well = 0
            self.reset()

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


class reservoir_300:
    def __init__(
        self,
        deck,
        plate: str,
        positions: Union[list[str], list[int]] = [],
        current_well: int = 0,
    ) -> None:
        self.plate = dk.get_labware_list(deck, [plate], Reservoir300)[0]
        self._frame = pd.DataFrame(
            index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )

        if not positions:
            self.positions = [i for i in range(384)]
        else:
            self.positions = positions

        if isinstance(self.positions, list) and all(
            isinstance(i, int) for i in self.positions
        ):
            self.positions = [index_to_string_384(i) for i in self.positions]

        for position in self.positions:
            letter, number = position[0], int(position[1:])
            self._frame.loc[letter, number] = 1

        self.original = self._frame.copy()

        self.current_wells = len(positions)
        self.current_well = current_well

    def reset(self):
        self._frame = self.original.copy()

    def frame(self):
        return self._frame.fillna(0)

    def wells(self):
        return self._frame.sum().sum()

    def get_wells_2ch(self, n: int = 2) -> list[tuple[Reservoir300, int]]:
        """Get wells from a 384 well plate in 2 channel mode."""
        if self.current_well == self.current_wells:
            self.current_well = 0
            self.reset()

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
            logger.error(f"Not enough wells in {self.plate.layout_name()}.")
            exit()

        index = sort_list(default_index_384.T.loc[column, row].tolist(), 4)[:n]
        self._frame[default_index_384.isin(index)] = 0
        self.current_well += n

        wells = [(self.plate, well) for well in index]
        return wells

    def get_wells_384mph(
        self, rows: int = 1, columns: int = 1
    ) -> list[tuple[Reservoir300, int]]:
        """Get wells from a 384 well plate in 384 multi-probe head mode."""
        if self.current_well == self.current_wells:
            self.current_well = 0
            self.reset()

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


class tip_96:
    def __init__(
        self,
        deck: dict,
        rack: str,
    ) -> None:
        self.rack = dk.get_labware_list(deck, [rack], Tip96)[0]
        self.default_tips = self.Frame(self.rack)

    def tips(
        self,
        positions: Union[list[str], list[int]] = [],
        current_tip: int = 0,
    ):
        return self.Frame(self.rack, positions, current_tip)

    class Frame:
        def __init__(
            self,
            rack: Tip96,
            positions: Union[list[str], list[int]] = [],
            current_tip: int = 0,
        ) -> None:
            self.rack = rack
            self.frame = pd.DataFrame(
                index=list(string.ascii_uppercase)[:8], columns=range(1, 13)
            )

            if not positions:
                self.positions = [i for i in range(96)]
            else:
                self.positions = positions

            if isinstance(self.positions, list) and all(
                isinstance(i, int) for i in self.positions
            ):
                self.positions = [index_to_string_96(i) for i in self.positions]

            for position in self.positions:
                letter, number = position[0], int(position[1:])
                self.frame.loc[letter, number] = 1

            self.original = self.frame.copy()

            self.current_tips = len(positions)
            self.current_tip = current_tip

        def reset(self):
            self.frame = self.original.copy()

        def get_frame(self):
            return self.frame.fillna(0)

        def tips(self):
            return self.frame.sum().sum()

        def get_all_tips(self) -> list[tuple[Tip96, int]]:
            tips = [(self.rack, tip) for tip in default_index_96.values.flatten()]
            return tips

        def get_tips_2ch(
            self, n: int = 2, remove: bool = True
        ) -> list[tuple[Tip96, int]]:
            """Get tips from a 96-tip rack in 2 channel mode."""
            column = default_index_96.T[self.frame.sum(axis=0) >= n].first_valid_index()

            for _ in range(2):
                try:
                    row = self.frame.T.loc[column] == 1
                except KeyError as e:
                    logger.debug(
                        f"Column with {n} tips not found in {self.plate.layout_name()},"
                        " trying again with 1 tip."
                    )
                    column = default_index_96.T[
                        self.frame.sum(axis=0) >= 1
                    ].first_valid_index()
                    continue
                else:
                    break
            else:
                logger.error(f"Not enough tips in {self.plate.layout_name()}.")
                sys.exit()

            index = sort_list(default_index_96.T.loc[column, row].tolist(), 2)[:n]  # type: ignore

            if remove:
                self.frame[default_index_96.isin(index)] = pd.NA
                self.current_tip += n

            return [(self.rack, well) for well in index]

        def get_rows_384mph(
            self, rows: int = 1, remove: bool = True
        ) -> list[tuple[Tip96, int]]:
            row = self.frame.T[self.frame.T.sum(axis=1) >= rows].last_valid_index()
            try:
                mask = self.frame.loc[:, row] == 1
            except KeyError as e:
                logger.error(f"Not enough tips in {self.rack.layout_name()}")
                exit()
            index = default_index_96.loc[:, row][mask].tolist()[-rows:]

            if remove:
                self.frame[default_index_96.isin(index)] = pd.NA

            return [(self.rack, tip) for tip in index]

        def get_columns_384mph(
            self, columns: int = 1, remove: bool = True
        ) -> list[tuple[Tip96, int]]:
            column = self.frame[self.frame.sum(axis=1) >= columns].last_valid_index()
            try:
                mask = self.frame.loc[column, :] == 1
            except KeyError as e:
                logger.error(f"Not enough tips in {self.rack.layout_name()}")
                exit()
            index = default_index_96.loc[column, :][mask].tolist()[-columns:]  # type: ignore

            if remove:
                self.frame[default_index_96.isin(index)] = pd.NA

            return [(self.rack, tip) for tip in index]


class plate_96:
    def __init__(self, deck, plate: str) -> None:
        self.plate = dk.get_labware_list(deck, [plate], Plate96)[0]
        self.default_wells = self.Frame(self.plate)

    def wells(
        self,
        positions: Union[list[str], list[int]] = [],
        current_well: int = 0,
    ):
        return self.Frame(self.plate, positions, current_well)

    class Frame:
        def __init__(
            self,
            plate: Plate96,
            positions: Union[list[str], list[int]] = [],
            current_well: int = 0,
        ) -> None:
            self.plate = plate
            self.frame = pd.DataFrame(
                index=list(string.ascii_uppercase)[:8], columns=range(1, 13)
            )
            if not positions:
                index = [i for i in range(96)]
            else:
                index = positions

            if isinstance(index, list) and all(isinstance(i, int) for i in index):
                index = [index_to_string_96(i) for i in index]  # type: ignore

            for idx in index:
                letter, number = idx[0], int(idx[1:])  # type: ignore
                self.frame.loc[letter, number] = 1

            self.original = self.frame.copy()
            self.current_wells = len(positions)
            self.current_well = current_well

        def reset(self):
            self.frame = self.original.copy()

        def get_frame(self):
            return self.frame.fillna(0)

        def total_wells(self):
            return self.frame.sum().sum()

        def get_wells_2ch(self, n: int = 2) -> list[tuple[Plate96, int]]:
            """Get wells from a 96 well plate in 2 channel mode."""
            if self.current_well == self.current_wells:
                self.current_well = 0
                self.reset()

            column = default_index_96.T[self.frame.sum(axis=0) >= n].first_valid_index()

            for _ in range(2):
                try:
                    row = self.frame.T.loc[column] == 1
                except KeyError as e:
                    logger.debug(
                        f"Column with {n} wells not found in"
                        f" {self.plate.layout_name()}, trying again with 1 well."
                    )
                    column = default_index_96.T[
                        self.frame.sum(axis=0) >= 1
                    ].first_valid_index()
                    continue
                else:
                    break
            else:
                logger.error(f"Not enough wells in {self.plate.layout_name()}.")
                exit()

            index = sort_list(default_index_96.T.loc[column, row].tolist(), 2)[:n]  # type: ignore
            self.frame[default_index_96.isin(index)] = pd.NA
            self.current_well += n

            return [(self.plate, well) for well in index]

        def get_wells_384mph(
            self, rows: int = 1, columns: int = 1, remove: bool = True
        ) -> list[tuple[Plate96, int]]:
            """Get wells from a 96 well plate in 384 multi-probe head mode."""
            if self.current_well == self.current_wells:
                self.current_well = 0
                self.reset()

            rowframe = self.frame[self.frame.sum(axis=1) >= columns].dropna(
                axis=1, how="any"
            )
            columnframe = rowframe.T[(rowframe.T.sum(axis=1) >= rows)].T
            mask = columnframe.iloc[:rows, :columns] == 1
            index = (
                default_index_96[mask]
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

            if remove:
                self.frame[default_index_96.isin(index)] = pd.NA
                self.current_well += rows * columns

            return [(self.plate, well) for well in index]

        def static_wells(self, well_list: list[str]):
            """Get specific wells from input list."""

            return [
                (self.plate, default_index_96.loc[well[0], int(well[1:])])
                for well in well_list
            ]


class carrier_24:
    def __init__(
        self,
        deck: dict,
    ) -> None:
        self.carrier = dk.get_labware_list(deck, ["C1"], EppiCarrier24)[0]
        self.default_tubes = self.Frame(self.carrier)

    def tubes(self, positions: list[str] = [], current_tube: int = 0):
        return self.Frame(self.carrier, positions, current_tube)

    class Frame:
        def __init__(
            self,
            carrier: EppiCarrier24,
            positions: list[str] = [],
            current_tube: int = 0,
        ):
            self.carrier = carrier

            self.frame = pd.DataFrame(
                index=list(string.ascii_uppercase)[:4], columns=range(1, 7)
            )

            if not positions:
                index = [i for i in range(24)]
            else:
                index = positions

            if isinstance(index, list) and all(isinstance(i, int) for i in index):
                index = [index_to_string_24(i) for i in index]  # type: ignore

            for idx in index:
                letter, number = idx[0], int(idx[1:])  # type: ignore
                self.frame.loc[letter, number] = 1

            self.original = self.frame.copy()
            self.current_tubes = len(positions)
            self.current_tube = current_tube

        def reset(self):
            self.frame = self.original.copy()

        def get_frame(self):
            return self.frame.fillna(0)

        def tubes(self):
            return self.frame.sum().sum()

        def get_tubes_2ch(self, n: int = 2) -> list[tuple[EppiCarrier24, int]]:
            """Get tubes from a 24 tube carrier in 2 channel mode."""
            if self.current_tube == self.current_tubes:
                self.current_tube = 0
                self.reset()

            column = default_index_24.T[self.frame.sum(axis=0) >= n].first_valid_index()

            for _ in range(2):
                try:
                    row = self.frame.T.loc[column] == 1
                except KeyError as e:
                    logger.debug(
                        f"Column with {n} tubes not found in"
                        f" {self.carrier.layout_name()}, trying again with 1 tube."
                    )
                    column = default_index_24.T[
                        self.frame.sum(axis=0) >= 1
                    ].first_valid_index()
                    continue
                else:
                    break
            else:
                logger.error(f"Not enough tubes in {self.carrier.layout_name()}.")
                exit()

            index = sort_list(default_index_24.T.loc[column, row].tolist(), 2)[:n]  # type: ignore
            self.frame[default_index_24.isin(index)] = pd.NA
            self.current_tube += n

            return [(self.carrier, well) for well in index]

        def static_tubes(self, tube_list: list[str]):
            """Get specific tubes from input list."""

            return [
                (self.carrier, default_index_24.loc[tube[0], int(tube[1:])])
                for tube in tube_list
            ]


class stack:
    def __init__(
        self,
        deck: dict,
        positions: str | list[str],
        labware_type,  #: Union[Plate96, Tip96, Plate384, Tip384],
        n_deck: int | list[int],
        n_labware: int = 2,
        reverse: bool = False,
    ) -> None:
        if isinstance(positions, str):
            self.deck_positions = [positions]
        elif isinstance(positions, list) and all(isinstance(i, str) for i in positions):
            self.deck_positions = positions
        else:
            logger.error("positions must be a str or list of strs.")
            exit()

        if isinstance(n_deck, int):
            self.n_deck = [n_deck]
        elif isinstance(n_deck, list) and all(isinstance(i, int) for i in n_deck):
            self.n_deck = n_deck
        else:
            logger.error("n must be an int or list of ints.")
            exit()

        self.n_labware = n_labware
        self.labware_type = labware_type
        self.reverse = reverse

        self.reset_stack()
        self.create_labware(deck)

    def create_labware(self, deck):
        l = dk.get_labware_list(
            deck,
            self.deck_positions,
            self.labware_type,
            self.n_deck,
            self.reverse,
        )

        if self.reverse:
            self.labware = l[-self.remaining_labware :]
        elif not self.reverse:
            self.labware = l[: self.remaining_labware]

    def get_labware(self):
        if self.remaining_labware > self.current_labware:
            self.current_labware += 1
            self.remaining_labware -= 1
            return self.labware[self.current_labware - 1]
        else:
            logger.error("No more labware left in stack.")
            exit()

    def reset_stack(self):
        self.current_labware = 0
        self.remaining_labware = self.n_labware

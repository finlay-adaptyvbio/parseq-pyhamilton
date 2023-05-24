import logging, itertools, string, sys
import pandas as pd

from pyhamilton import (
    Lid,
    Plate96,
    Plate384,
    Tip96,
    Tip384,
    Reservoir300,
    EppiCarrier24,
)

import deck as dk

# Class mapping

TYPES = {
    Plate384: "plate_384",
    Plate96: "plate_96",
    Tip384: "tip_384",
    Tip96: "tip_96",
    Reservoir300: "reservoir_300",
    EppiCarrier24: "carrier_24",
    Lid: "lid",
}

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Default labware indexes

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

default_index_96_r = pd.DataFrame(
    [[i for i in range(j, 96, 8)][::-1] for j in range(8)][::-1],
    index=list(string.ascii_uppercase)[:8],
    columns=range(1, 13),
)

default_index_384 = pd.DataFrame(
    [[i for i in range(j, 384, 16)] for j in range(16)],
    index=list(string.ascii_uppercase)[:16],
    columns=range(1, 25),
)


# Conversion functions


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
    x, y = int(position) % 6, int(position) // 6
    return alphabet[y] + str(x + 1)


# Labware index generators


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


# Optimized sorting for 2 channel pipettes


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


# Labware classes


def assign_labware(labware):
    labware_class = TYPES[type(labware)]
    return globals()[labware_class](labware)


class tip_384:
    def __init__(
        self,
        labware: Tip384,
    ) -> None:
        self.rack = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )
        self.og_df = self.df.copy()

    def reset(self):
        self.df = self.og_df.copy()

    def frame(self):
        return self.df.fillna(0).astype(int)

    def total(self):
        return self.df.sum().sum()

    def full(self):
        """Get all available positions."""
        return [(self.rack, i) for i in default_index_384.values.flatten()]


class plate_384:
    def __init__(self, labware: Plate384) -> None:
        self.plate = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )
        self.og_df = self.df.copy()

    def fill(self, positions: list[str]):
        self.df[self.df > 0] = pd.NA
        for pos in positions:
            try:
                row, col = pos[0], int(pos[1:])
                self.df.loc[row][col] = 1
            except (IndexError, ValueError, KeyError) as e:
                logger.error(
                    "Unable to parse positions. Make sure input is in list[str] format"
                    " (['A1', 'B02']) or use list constructor from labware module."
                )
                raise e

        self.df.infer_objects()
        self.og_df = self.df.copy()

    def reset(self):
        self.df = self.og_df.copy()

    def frame(self):
        return self.df.fillna(0).astype(int)

    def total(self):
        return self.df.sum().sum()

    def ch2(self, n: int = 2, remove: bool = True) -> list[tuple[Plate384, int]]:
        """Get wells from a plate in 2 channel mode."""

        column = default_index_384.T[self.df.sum(axis=0) >= n].first_valid_index()

        for _ in range(2):
            try:
                row = self.df.T.loc[column] == 1
            except KeyError:
                logger.debug(
                    f"Column with {n} wells not found in"
                    f" {self.plate.layout_name()}, trying again with 1"
                    " position."
                )
                column = default_index_384.T[
                    self.df.sum(axis=0) >= 1
                ].first_valid_index()
                continue
            else:
                break
        else:
            logger.error(f"Not enough wells in {self.plate.layout_name()}.")
            exit()

        index = sort_list(default_index_384.T.loc[column][row].tolist(), 4)[:n]

        if remove:
            self.df[default_index_384.isin(index)] = pd.NA

        return [(self.plate, i) for i in index]

    def mph384(
        self, rows: int = 1, columns: int = 1, remove: bool = True
    ) -> list[tuple[Plate384, int]]:
        """Get wells from a plate in 384 multi-probe head mode."""

        row_df = self.df[self.df.sum(axis=1) >= columns].dropna(axis=1, how="any")
        column_df = row_df.T[(row_df.T.sum(axis=1) >= rows)].T
        mask = column_df.iloc[:rows, :columns] == 1
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

        if remove:
            self.df[default_index_384.isin(index)] = pd.NA

        return [(self.plate, i) for i in index]

    def static(self, index: list[str]) -> list[tuple[Plate384, int]]:
        """Get specific plate wells from input list."""
        return [(self.plate, default_index_384.at[i[0], int(i[1:])]) for i in index]


class reservoir_300:
    def __init__(self, labware: Reservoir300) -> None:
        self.reservoir = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )
        self.og_df = self.df.copy()

    def fill(self, positions: list[str]):
        self.df[self.df > 0] = pd.NA
        for pos in positions:
            try:
                row, col = pos[0], int(pos[1:])
                self.df.loc[row][col] = 1
            except (IndexError, ValueError, KeyError) as e:
                logger.error(
                    "Unable to parse positions. Make sure input is in list[str] format"
                    " (['A1', 'B02']) or use list constructor from labware module."
                )
                raise e

        self.og_df = self.df.copy()

    def reset(self):
        self.df = self.og_df.copy()

    def frame(self):
        return self.df.fillna(0).astype(int)

    def total(self):
        return self.df.sum().sum()

    def ch2(self, n: int = 2) -> list[tuple[Reservoir300, int]]:
        """Get positions from a reservoir in 2 channel mode."""

        column = default_index_384.T[self.df.sum(axis=0) >= n].first_valid_index()

        for _ in range(2):
            try:
                row = self.df.T.loc[column] == 1
            except KeyError:
                logger.debug(
                    f"Column with {n} positions not found in"
                    f" {self.reservoir.layout_name()}, trying again with 1"
                    " position."
                )
                column = default_index_384.T[
                    self.df.sum(axis=0) >= 1
                ].first_valid_index()
                continue
            else:
                break
        else:
            logger.error(f"Not enough positions in {self.reservoir.layout_name()}.")
            exit()

        index = sort_list(default_index_384.T.loc[column][row].tolist(), 4)[:n]

        return [(self.reservoir, pos) for pos in index]

    def mph384(self, rows: int = 1, columns: int = 1) -> list[tuple[Reservoir300, int]]:
        """Get positions from a reservoir in 384 multi-probe head mode."""

        row_df = self.df[self.df.sum(axis=1) >= columns].dropna(axis=1, how="any")
        column_df = row_df.T[(row_df.T.sum(axis=1) >= rows)].T
        mask = column_df.iloc[:rows, :columns] == 1
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
            logger.error(f"Not enough positions in {self.reservoir.layout_name()}")
            exit()

        return [(self.reservoir, i) for i in index]

    def static(self, index: list[str]):
        """Get specific reservoir positions from input list."""
        return [(self.reservoir, default_index_384.at[i[0], int(i[1:])]) for i in index]

    def full(self):
        """Get all available positions."""
        return [(self.reservoir, i) for i in default_index_384.values.flatten()]


class tip_96:
    def __init__(self, labware: Tip96) -> None:
        self.rack = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:8], columns=range(1, 13)
        )
        self.og_df = self.df.copy()

    def fill(self, positions: list[str]):
        self.df[self.df > 0] = pd.NA
        for pos in positions:
            try:
                row, col = pos[0], int(pos[1:])
                self.df.loc[row][col] = 1
            except (IndexError, ValueError, KeyError) as e:
                logger.error(
                    "Unable to parse positions. Make sure input is in list[str] format"
                    " (['A1', 'B02']) or use list constructor from labware module."
                )
                raise e

        self.og_df = self.df.copy()

    def reset(self):
        self.df = self.og_df.copy()

    def frame(self):
        return self.df.fillna(0).astype(int)

    def total(self):
        return self.df.sum().sum()

    def ch2(self, n: int = 2, remove: bool = True) -> list[tuple[Tip96, int]]:
        """Get tips from a 96-tip rack in 2 channel mode."""
        column = default_index_96.T[self.df.sum(axis=0) >= n].first_valid_index()

        for _ in range(2):
            try:
                row = self.df.T.loc[column] == 1
            except KeyError:
                logger.debug(
                    f"Column with {n} tips not found in {self.rack.layout_name()},"
                    " trying again with 1 tip."
                )
                column = default_index_96.T[
                    self.df.sum(axis=0) >= 1
                ].first_valid_index()
                continue
            else:
                break
        else:
            logger.error(f"Not enough tips in {self.rack.layout_name()}.")
            sys.exit()

        index = sort_list(default_index_96.T.loc[column][row].tolist(), 2)[:n]

        if remove:
            self.df[default_index_96.isin(index)] = pd.NA

        return [(self.rack, i) for i in index]

    def mph384(
        self, rows: int = 1, columns: int = 1, remove: bool = True
    ) -> list[tuple[Tip96, int]]:
        """Get tips from a 96 tip rack in 384 multi-probe head mode."""
        self.df.columns = self.df.columns[::-1]
        row_df = self.df.loc[self.df.sum(axis=1) >= columns].dropna(axis=1, how="any")
        self.df.columns = self.df.columns[::-1]
        column_df = row_df.T[(row_df.T.sum(axis=1) >= rows)].T
        column_df.columns = column_df.columns[::-1]
        mask = column_df.iloc[:rows, :columns] == 1
        index = sorted(
            default_index_96_r[mask]
            .convert_dtypes()
            .dropna(axis=1, how="all")
            .dropna(axis=0, how="all")
            .values.flatten(),
        )
        try:
            index[-1]
        except IndexError as e:
            logger.error(f"Not enough wells in {self.rack.layout_name()}")
            sys.exit()

        if remove:
            self.df[default_index_96.isin(index)] = pd.NA

        return [(self.rack, i) for i in index]

    def full(self):
        """Get all available positions."""
        return [(self.rack, i) for i in default_index_96.values.flatten()]


class plate_96:
    def __init__(self, labware: Plate96) -> None:
        self.plate = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:8], columns=range(1, 13)
        )

    def fill(self, positions: list[str]):
        self.df[self.df > 0] = pd.NA
        for pos in positions:
            try:
                row, col = pos[0], int(pos[1:])
                self.df.loc[row][col] = 1
            except (IndexError, ValueError, KeyError) as e:
                logger.error(
                    "Unable to parse positions. Make sure input is in list[str] format"
                    " (['A1', 'B02']) or use list constructor from labware module."
                )
                raise e

        self.og_df = self.df.copy()

    def reset(self):
        self.df = self.og_df.copy()

    def frame(self):
        return self.df.fillna(0).astype(int)

    def total(self):
        return self.df.sum().sum()

    def ch2(self, n: int = 2, remove=True) -> list[tuple[Plate96, int]]:
        """Get wells from a 96 well plate in 2 channel mode."""
        column = default_index_96.T[self.df.sum(axis=0) >= n].first_valid_index()

        for _ in range(2):
            try:
                row = self.df.T.loc[column] == 1
            except KeyError:
                logger.debug(
                    f"Column with {n} wells not found in"
                    f" {self.plate.layout_name()}, trying again with 1 well."
                )
                column = default_index_96.T[
                    self.df.sum(axis=0) >= 1
                ].first_valid_index()
                continue
            else:
                break
        else:
            logger.error(f"Not enough wells in {self.plate.layout_name()}.")
            sys.exit()

        index = sort_list(default_index_96.T.loc[column][row].tolist(), 2)[:n]

        if remove:
            self.df[default_index_96.isin(index)] = pd.NA

        return [(self.plate, i) for i in index]

    def mph384(
        self, rows: int = 1, columns: int = 1, remove: bool = True
    ) -> list[tuple[Plate96, int]]:
        """Get wells from a 96 well plate in 384 multi-probe head mode."""
        row_df = self.df[self.df.sum(axis=1) >= columns].dropna(axis=1, how="any")
        column_df = row_df.T[(row_df.T.sum(axis=1) >= rows)].T
        mask = column_df.iloc[:rows, :columns] == 1
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
            sys.exit()

        if remove:
            self.df[default_index_96.isin(index)] = pd.NA

        return [(self.plate, i) for i in index]

    def static(self, index: list[str]) -> list[tuple[Plate96, int]]:
        """Get specific plate wells from input list."""
        return [(self.plate, default_index_96.at[i[0], int(i[1:])]) for i in index]

    def full(self):
        """Get all available positions."""
        return [(self.plate, i) for i in default_index_96.values.flatten()]


class carrier_24:
    def __init__(
        self,
        labware: EppiCarrier24,
    ) -> None:
        self.carrier = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:4], columns=range(1, 7)
        )
        self.og_df = self.df.copy()

    def fill(self, positions: list[str], current_tube: int = 0):
        self.df[self.df > 0] = pd.NA
        for pos in positions:
            try:
                row, col = pos[0], int(pos[1:])
                self.df.loc[row][col] = 1
            except (IndexError, ValueError, KeyError) as e:
                logger.error(
                    "Unable to parse positions. Make sure input is in list[str] format"
                    " (['A1', 'B02']) or use list constructor from labware module."
                )
                raise e

        self.og_df = self.df.copy()

    def reset(self):
        self.df = self.og_df.copy()

    def frame(self):
        return self.df.fillna(0).astype(int)

    def total(self):
        return self.df.sum().sum()

    def ch2(self, n: int = 2, remove=True) -> list[tuple[EppiCarrier24, int]]:
        """Get tubes from a 24 tube carrier in 2 channel mode."""

        column = default_index_24.T[self.df.sum(axis=0) >= n].first_valid_index()

        for _ in range(2):
            try:
                row = self.df.T.loc[column] == 1
            except KeyError as e:
                logger.debug(
                    f"Column with {n} tubes not found in"
                    f" {self.carrier.layout_name()}, trying again with 1 tube."
                )
                column = default_index_24.T[
                    self.df.sum(axis=0) >= 1
                ].first_valid_index()
                continue
            else:
                break
        else:
            logger.error(f"Not enough tubes in {self.carrier.layout_name()}.")
            sys.exit()

        index = sort_list(default_index_24.T.loc[column][row].tolist(), 2)[:n]

        if remove:
            self.df[default_index_24.isin(index)] = pd.NA

        return [(self.carrier, i) for i in index]

    def static(self, index: list[str]):
        """Get specific tubes from input list."""

        return [(self.carrier, default_index_24.loc[i[0], int(i[1:])]) for i in index]


class lid:
    def __init__(
        self,
        labware: Lid,
    ) -> None:
        self.lid = labware

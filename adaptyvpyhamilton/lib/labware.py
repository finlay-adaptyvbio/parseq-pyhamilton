import logging, sys, itertools, string
import pandas as pd

from pyhamilton import Plate96, Plate384, Tip96

from pyhamilton.deckresource import DeckResource

# Logging settings
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Default labware indexes (labware with all positions available)
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

# Reversed 96 format for 384 head custom pick-up
default_index_96_r = pd.DataFrame(
    [[i for i in range(j, 96, 8)][::-1] for j in range(8)][::-1],
    index=list(string.ascii_uppercase)[:8],
    columns=range(1, 13),
)


# Extract tuple from standard labeling format (A1, A01, etc.)
def pos(position: str):
    try:
        letter, number = position[0], int(position[1:]) - 1
        if letter in list(string.ascii_uppercase) and number in list(range(5)):
            return (letter, number)
        else:
            logger.error(f"Unable to parse position, was the correct format provided?")
            sys.exit()
    except Exception as e:
        logger.exception(e)
        sys.exit()


# Conversion functions between string (A1, A01, etc.) and integer (0, 1, etc.) format
def str_to_int_384(position: str) -> int:
    """Convert single 384 position from string to int format."""
    return string.ascii_uppercase[:16].index(position[0]) + (int(position[1:]) - 1) * 16


def int_to_str_384(position: int) -> str:
    """Convert single 384 position from string to int format."""
    x, y = int(position) // 16, int(position) % 16
    return string.ascii_uppercase[:16][y] + str(x + 1)


def str_to_int_96(position: str) -> int:
    """Convert single 96 position from string to int format."""
    return string.ascii_uppercase[:8].index(position[0]) + (int(position[1:]) - 1) * 8


def int_to_str_96(position: int) -> str:
    """Convert single 96 position from int to string format."""
    x, y = int(position) // 8, int(position) % 8
    return string.ascii_uppercase[:8][y] + str(x + 1)


def str_to_int_24(position: str) -> int:
    """Convert single 24 position from string to int format."""
    return string.ascii_uppercase[:4].index(position[0]) + (int(position[1:]) - 1) * 4


def int_to_str_24(position: int) -> str:
    """Convert single 24 position from int to string format."""
    x, y = int(position) % 6, int(position) // 6
    return string.ascii_uppercase[:4][y] + str(x + 1)


# Labware index generators to pass to labware classes
def pos_row_384(n: int = 384, skip: int = 0) -> list[str]:
    """
    String index for 384 positions, advance along rows then columns.
    Optionally skip n (default 0) positions in returned index.
    """
    return [
        f"{letter}{number}"
        for number in range(1, 25)
        for letter in list(string.ascii_uppercase)[:16]
    ][skip : skip + n]


def pos_col_384(n: int = 384, skip: int = 0) -> list[str]:
    """
    String index for 384 positions, advance along columns then rows.
    Optionally skip n (default 0) positions in returned index.
    """
    return [
        f"{letter}{number}"
        for letter in list(string.ascii_uppercase)[:16]
        for number in range(1, 25)
    ][skip : skip + n]


def pos_row_96(n: int = 96, skip: int = 0) -> list[str]:
    """
    String index for 96 positions, advance along rows then columns.
    Optionally skip n (default 0) positions in returned index.
    """
    return [
        f"{letter}{number}"
        for number in range(1, 13)
        for letter in list(string.ascii_uppercase)[:8]
    ][skip : skip + n]


def pos_col_96(n: int = 96, skip: int = 0) -> list[str]:
    """
    String index for 96 positions, advance along columns then rows.
    Optionally skip n (default 0) positions in returned index.
    """
    return [
        f"{letter}{number}"
        for letter in list(string.ascii_uppercase)[:8]
        for number in range(1, 13)
    ][skip : skip + n]


def pos_row_24(n: int = 24, skip: int = 0) -> list[str]:
    """
    String index for 24 positions, advance along rows then columns.
    Optionally skip n (default 0) positions in returned index.
    """
    return [
        f"{letter}{number}"
        for number in range(1, 7)
        for letter in list(string.ascii_uppercase)[:4]
    ][skip : skip + n]


def pos_col_24(n: int = 24, skip: int = 0) -> list[str]:
    """
    String index for 24 positions, advance along columns then rows.
    Optionally skip n (default 0) positions in returned index.
    """
    return [
        f"{letter}{number}"
        for letter in list(string.ascii_uppercase)[:4]
        for number in range(1, 7)
    ][skip : skip + n]


# Index generators for less common labware formats
def pos_96_in_384(q: int) -> list[int]:
    """
    Int index for 96 positions as a subset of a larger 384 position labware.
    Used with 384 head in 96-channel mode. Input argument q gives start position
    for the 96 positions: A01, B01, A02 or B02.
    """
    pos = []
    if q == 1:
        q1, q2 = 0, 0
    elif q == 2:
        q1, q2 = 0, 1
    elif q == 3:
        q1, q2 = 1, 0
    else:
        q1, q2 = 1, 1

    for i in range(0 + q1, 24 + q1, 2):
        for j in range(1 + q2, 17 + q2, 2):
            pos.append(j + i * 16 - 1)
    return pos


# Optimized sorting function for 2 channel pipettes
def sort_list(indexes: list[int], sep: int):
    """
    Sort a list of positions in int format into the best possible order for parallel pipetting.
    Input argument sep is the minimum number of positions needed between 2 channels for parallel
    pipetting. This depends on labware format (4 for 384 and 1 for 96).
    """
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


# Function to dynamically assign layout objects to their respective labware classes
def assign_labware(labware):
    labware_class = TYPES[type(labware)]
    return globals()[labware_class](labware)


# Additional PyHamilton labware classes
class Standard384(DeckResource):
    """Labware types with 384 positions that use a letter-number id scheme like `'A1'`."""

    def well_coords(self, idx):
        self._assert_idx_in_range(idx)
        return int(idx) // 16, int(idx) % 16


class Tip384(Standard384):
    def __init__(self, layout_name):
        self._layout_name = layout_name
        self._num_items = 384
        self.resource_type = DeckResource.types.TIP

    def position_id(self, idx):
        self._assert_idx_in_range(idx)
        return str(idx + 1)


class Reservoir300(Standard384):
    def __init__(self, layout_name):
        self._layout_name = layout_name
        self._num_items = 384
        self.resource_type = DeckResource.types.VESSEL

    def position_id(self, idx):
        self._assert_idx_in_range(idx)
        return str(idx + 1)


class Lid(DeckResource):
    def __init__(self, layout_name):
        self._layout_name = layout_name
        self._num_items = 1
        self.resource_type = DeckResource.types.VESSEL

    def well_coords(self, idx):
        self._assert_idx_in_range(idx)
        return int(idx) // 1, int(idx) % 1

    def position_id(self, idx):
        self._assert_idx_in_range(idx)
        return str(idx + 1)


class EppiCarrier24(DeckResource):
    def __init__(self, layout_name):
        self._layout_name = layout_name
        self._num_items = 24
        self.positions = [str(i + 1) for i in range(self._num_items)]
        self.resource_type = DeckResource.types.VESSEL

    def well_coords(self, idx):
        self._assert_idx_in_range(idx)
        return int(idx) // 24, int(idx) % 24

    def position_id(self, idx):
        return self.positions[idx]


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


# Labware classes (DataFrame wrappers)
class tip_384:
    """
    384-tip rack, methods available for accessing positions:

    full:       all positions
    """

    def __init__(
        self,
        labware: Tip384,
    ) -> None:
        self.rack = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )
        self.og_df = self.df.copy()

    def reset(self) -> None:
        """Reset DataFrame to initial state."""
        self.df = self.og_df.copy()

    def frame(self) -> pd.DataFrame:
        """Return DataFrame filled with 1s and 0s for display purposes."""
        return self.df.fillna(0).astype(int)

    def full(self) -> list[tuple[Tip384, int]]:
        """Get all available positions."""
        return [(self.rack, i) for i in default_index_384.values.flatten()]


class plate_384:
    """
    384-well plate, methods available for accessing positions:

    - ch2:        2-channel mode (max 2 positions)
    - mph384:     384-head mode (max 384 positions)
    - quadrant:   384-head in 96-channel mode (max 96 positions)
    - static:     provided positions
    - full:       all positions
    """

    def __init__(self, labware: Plate384) -> None:
        self.plate = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )
        self.og_df = self.df.copy()

    def fill(self, positions: list[str]) -> None:
        """Make provided positions available to access functions."""
        self.df[self.df > 0] = pd.NA
        for pos in positions:
            try:
                row, col = pos[0], int(pos[1:])
                self.df.loc[row][col] = 1
            except (IndexError, ValueError, KeyError) as e:
                logger.error(
                    "Unable to parse positions. Make sure input is in list[str] format"
                    " (['A1', 'B02']) or use index generator from labware module."
                )
                logger.exception(e)
                sys.exit()

        self.df.infer_objects()
        self.og_df = self.df.copy()

    def reset(self) -> None:
        self.df = self.og_df.copy()

    def frame(self) -> pd.DataFrame:
        return self.df.fillna(0).astype(int)

    def total(self) -> int:
        return int(self.df.sum().sum())

    def ch2(self, n: int = 2, remove: bool = True) -> list[tuple[Plate384, int]]:
        """Get wells from a plate in 2 channel mode."""

        # Try to get n tips, if less than n tips left try again with 1 tip
        column = default_index_384.T[self.df.sum(axis=0) >= n].first_valid_index()
        for _ in range(2):
            try:
                row = self.df.T.loc[column] == 1
            except KeyError:
                logger.debug(
                    f"Column with {n} wells not found in"
                    f" {self.plate.layout_name()}., trying again with 1"
                    " well."
                )
                column = default_index_384.T[
                    self.df.sum(axis=0) >= 1
                ].first_valid_index()
                continue
            else:
                break
        else:
            logger.error(f"Not enough wells in {self.plate.layout_name()}.")
            sys.exit()

        index = sort_list(default_index_384.T.loc[column][row].tolist(), 4)[:n]

        # Optionally remove wells from df
        if remove:
            self.df[default_index_384.isin(index)] = pd.NA

        # Check if correct number of wells was found, otherwise fetch another well
        # This happens if the number of wells left in a column is less than n
        if n != len(index) and remove:
            wells = [(self.plate, i) for i in index]
            wells.extend(self.ch2(1))
            return wells
        elif n != len(index) and not remove:
            wells = [(self.plate, i) for i in index]
            self.df[default_index_384.isin(index)] = pd.NA
            wells.extend(self.ch2(1, remove=False))
            self.df[default_index_384.isin(index)] = 1
            return wells

        return [(self.plate, i) for i in index]

    def mph384(
        self, rows: int = 1, columns: int = 1, remove: bool = True
    ) -> list[tuple[Plate384, int]]:
        """Get wells from a 384-well plate in 384-head mode."""

        # Find matrix which supports provided row and column dimensions
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

        # Check if matrix actually contains wells
        try:
            index[-1]
        except IndexError as e:
            logger.error(f"Not enough wells in {self.plate.layout_name()}.")
            logger.exception(e)
            sys.exit()

        if remove:
            self.df[default_index_384.isin(index)] = pd.NA

        return [(self.plate, i) for i in index]

    def quadrant(self, remove: bool = True) -> list[tuple[Plate384, int]]:
        """Get 96 positions from a reservoir with 384-head in 96-channel mode."""
        # Get first quadrant available
        index, quadrant_df = None, None  # required to check if quadrant is returned
        for q in range(1, 5):
            index = pos_96_in_384(q)
            mask = default_index_384.isin(index)
            quadrant_df = self.df[mask]
            if quadrant_df.sum().sum() == 96:
                break

        # Check if quadrant was found
        try:
            assert index is not None
            assert quadrant_df is not None
        except AssertionError as e:
            logger.error(f"Not enough wells in {self.plate.layout_name()}.")
            logger.exception(e)
            sys.exit()

        # Optionally remove positions from df
        if remove:
            self.df[quadrant_df == 1] = pd.NA

        return [(self.plate, i) for i in index]

    def static(self, index: list[str]) -> list[tuple[Plate384, int]]:
        """Get specific plate wells from input list."""
        return [(self.plate, default_index_384.at[i[0], int(i[1:])]) for i in index]

    def full(self) -> list[tuple[Plate384, int]]:
        """Get all available positions."""
        return [(self.plate, i) for i in default_index_384.values.flatten()]


class reservoir_300:
    """
    384-well reservoir, methods available for accessing positions:

    - ch2:        2-channel mode (max 2 positions)
    - mph384:     384-head mode (max 384 positions)
    - quadrant:   384-head in 96-channel mode (max 96 positions)
    - static:     provided positions
    - full:       all positions
    """

    def __init__(self, labware: Reservoir300) -> None:
        self.reservoir = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:16], columns=range(1, 25)
        )
        self.og_df = self.df.copy()

    def fill(self, positions: list[str]) -> None:
        """Make provided positions available to access functions."""
        self.df[self.df > 0] = pd.NA
        for pos in positions:
            try:
                row, col = pos[0], int(pos[1:])
                self.df.loc[row][col] = 1
            except (IndexError, ValueError, KeyError) as e:
                logger.error(
                    "Unable to parse positions. Make sure input is in list[str] format"
                    " (['A1', 'B02']) or use index generator from labware module."
                )
                logger.exception(e)
                sys.exit()

        self.og_df = self.df.copy()

    def reset(self) -> None:
        self.df = self.og_df.copy()

    def frame(self) -> pd.DataFrame:
        return self.df.fillna(0).astype(int)

    def total(self) -> int:
        return int(self.df.sum().sum())

    def ch2(self, n: int = 2) -> list[tuple[Reservoir300, int]]:
        """Get positions from a reservoir in 2 channel mode."""

        # Try to get n tips, if less than n tips left try again with 1 tip
        column = default_index_384.T[self.df.sum(axis=0) >= n].first_valid_index()
        for _ in range(2):
            try:
                row = self.df.T.loc[column] == 1
            except KeyError:
                logger.debug(
                    f"Column with {n} positions not found in"
                    f" {self.reservoir.layout_name()}., trying again with 1"
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
            sys.exit()

        index = sort_list(default_index_384.T.loc[column][row].tolist(), 4)[:n]

        return [(self.reservoir, pos) for pos in index]

    def mph384(self, rows: int = 1, columns: int = 1) -> list[tuple[Reservoir300, int]]:
        """Get positions from a reservoir in 384 multi-probe head mode."""

        # Find matrix which supports provided row and column dimensions
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

        # Check if matrix actually contains positions
        try:
            index[-1]
        except IndexError as e:
            logger.error(f"Not enough positions in {self.reservoir.layout_name()}.")
            exit()

        return [(self.reservoir, i) for i in index]

    def quadrant(self, remove: bool = True) -> list[tuple[Reservoir300, int]]:
        """Get 96 positions from a reservoir with 384-head in 96-channel mode."""

        # Get first quadrant available
        index, quadrant_df = None, None  # required to check if quadrant is returned
        for q in range(1, 5):
            index = pos_96_in_384(q)
            mask = default_index_384.isin(index)
            quadrant_df = self.df[mask]
            if quadrant_df.sum().sum() == 96:
                break

        # Check if quadrant was found
        try:
            assert index is not None
            assert quadrant_df is not None
        except AssertionError as e:
            logger.error(f"Not enough positions in {self.reservoir.layout_name()}.")
            logger.exception(e)
            sys.exit()

        # Optionally remove positions from df
        if remove:
            self.df[quadrant_df == 1] = pd.NA

        return [(self.reservoir, i) for i in index]

    def static(self, index: list[str]) -> list[tuple[Reservoir300, int]]:
        """Get specific reservoir positions from input list."""
        return [(self.reservoir, default_index_384.at[i[0], int(i[1:])]) for i in index]

    def full(self) -> list[tuple[Reservoir300, int]]:
        """Get all available positions."""
        return [(self.reservoir, i) for i in default_index_384.values.flatten()]


class tip_96:
    """
    96-tip rack, methods available for accessing positions:

    - ch2:        2-channel mode (max 2 positions)
    - mph384:     384-head mode (max 96 positions)
    - static:     provided positions
    - full:       all positions
    """

    def __init__(self, labware: Tip96) -> None:
        self.rack = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:8], columns=range(1, 13)
        )
        self.og_df = self.df.copy()

    def fill(self, positions: list[str]) -> None:
        """Make provided positions available to access functions."""
        self.df[self.df > 0] = pd.NA
        for pos in positions:
            try:
                row, col = pos[0], int(pos[1:])
                self.df.loc[row][col] = 1
            except (IndexError, ValueError, KeyError) as e:
                logger.error(
                    "Unable to parse positions. Make sure input is in list[str] format"
                    " (['A1', 'B02']) or use index generator from labware module."
                )
                logger.exception(e)
                sys.exit()

        self.og_df = self.df.copy()

    def reset(self) -> None:
        self.df = self.og_df.copy()

    def frame(self) -> pd.DataFrame:
        return self.df.fillna(0).astype(int)

    def total(self) -> int:
        return int(self.df.sum().sum())

    def ch2(self, n: int = 2, remove: bool = True) -> list[tuple[Tip96, int]]:
        """Get tips from a 96-tip rack in 2-channel mode."""

        # Try to get n tips, if less than n tips left try again with 1 tip
        column = default_index_96.T[self.df.sum(axis=0) >= n].first_valid_index()
        for _ in range(2):
            try:
                row = self.df.T.loc[column] == 1
            except KeyError:
                logger.debug(
                    f"Column with {n} tips not found in {self.rack.layout_name()}.,"
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

        # Optionally remove tips from df
        if remove:
            self.df[default_index_96.isin(index)] = pd.NA

        # Check if correct number of tips was found, otherwise fetch another tip
        # This happens if the number of tips left in a column is less than n
        if n != len(index) and remove:
            tips = [(self.rack, i) for i in index]
            tips.extend(self.ch2(1))
            return tips
        elif n != len(index) and not remove:
            tips = [(self.rack, i) for i in index]
            self.df[default_index_96.isin(index)] = pd.NA
            tips.extend(self.ch2(1, remove=False))
            self.df[default_index_96.isin(index)] = 1
            return tips

        return [(self.rack, i) for i in index]

    def mph384(
        self, rows: int = 1, columns: int = 1, remove: bool = True
    ) -> list[tuple[Tip96, int]]:
        """Get tips from a 96-tip rack in 384-head mode."""

        # Find matrix which supports provided row and column dimensions
        self.df.columns = self.df.columns[
            ::-1
        ]  # reverse df to allow 384-head to approach from south
        row_df = self.df.loc[self.df.sum(axis=1) >= columns].dropna(axis=1, how="any")
        self.df.columns = self.df.columns[::-1]  # and reverse again for next steps
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

        # Check if matrix actually contains wells
        try:
            index[-1]
        except IndexError as e:
            logger.error(f"Not enough wells in {self.rack.layout_name()}.")
            sys.exit()

        # Optionally remove tips from df
        if remove:
            self.df[default_index_96.isin(index)] = pd.NA

        return [(self.rack, i) for i in index]

    def static(self, index: list[str]) -> list[tuple[Tip96, int]]:
        """Get specific tips from input list."""
        return [(self.rack, default_index_96.at[i[0], int(i[1:])]) for i in index]

    def full(self) -> list[tuple[Tip96, int]]:
        """Get all available positions."""
        return [(self.rack, i) for i in default_index_96.values.flatten()]


class plate_96:
    """
    96-well plate, methods available for accessing positions:

    - ch2:        2-channel mode (max 2 positions)
    - mph384:     384-head mode (max 96 positions)
    - static:     provided positions
    - full:       all positions
    """

    def __init__(self, labware: Plate96) -> None:
        self.plate = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:8], columns=range(1, 13)
        )

    def fill(self, positions: list[str]) -> None:
        """Make provided positions available to access functions."""
        self.df[self.df > 0] = pd.NA
        for pos in positions:
            try:
                row, col = pos[0], int(pos[1:])
                self.df.loc[row][col] = 1
            except (IndexError, ValueError, KeyError) as e:
                logger.error(
                    "Unable to parse positions. Make sure input is in list[str] format"
                    " (['A1', 'B02']) or use index generator from labware module."
                )
                logger.exception(e)
                sys.exit()

        self.og_df = self.df.copy()

    def reset(self) -> None:
        self.df = self.og_df.copy()

    def frame(self) -> pd.DataFrame:
        return self.df.fillna(0).astype(int)

    def total(self) -> int:
        return int(self.df.sum().sum())

    def ch2(self, n: int = 2, remove=True) -> list[tuple[Plate96, int]]:
        """Get wells from a 96-well plate in 2-channel mode."""

        # Try to get n wells, if less than n wells left try again with 1 well
        column = default_index_96.T[self.df.sum(axis=0) >= n].first_valid_index()
        for _ in range(2):
            try:
                row = self.df.T.loc[column] == 1
            except KeyError:
                logger.debug(
                    f"Column with {n} wells not found in"
                    f" {self.plate.layout_name()}., trying again with 1 well."
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

        # Optionally remove wells from df
        if remove:
            self.df[default_index_96.isin(index)] = pd.NA

        # Check if correct number of wells was found, otherwise fetch another well
        # This happens if the number of wells left in a column is less than n
        if n != len(index) and remove:
            wells = [(self.plate, i) for i in index]
            wells.extend(self.ch2(1))
            return wells
        elif n != len(index) and not remove:
            wells = [(self.plate, i) for i in index]
            self.df[default_index_96.isin(index)] = pd.NA
            wells.extend(self.ch2(1, remove=False))
            self.df[default_index_96.isin(index)] = 1
            return wells

        return [(self.plate, i) for i in index]

    def mph384(
        self, rows: int = 1, columns: int = 1, remove: bool = True
    ) -> list[tuple[Plate96, int]]:
        """Get wells from a 96-well plate in 384-head mode."""

        # Find matrix which supports provided row and column dimensions
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

        # Check if matrix actually contains wells
        try:
            index[-1]
        except IndexError as e:
            logger.error(f"Not enough wells in {self.plate.layout_name()}.")
            sys.exit()

        # Optionally remove wells from df
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
    """
    24-tube carrier, methods available for accessing positions:

    - ch2:        2-channel mode (max 2 positions)
    - static:     provided positions
    """

    def __init__(
        self,
        labware: EppiCarrier24,
    ) -> None:
        self.carrier = labware
        self.df = pd.DataFrame(
            1, index=list(string.ascii_uppercase)[:4], columns=range(1, 7)
        )
        self.og_df = self.df.copy()

    def fill(self, positions: list[str]) -> None:
        """Make provided positions available to access functions."""
        self.df[self.df > 0] = pd.NA
        for pos in positions:
            try:
                row, col = pos[0], int(pos[1:])
                self.df.loc[row][col] = 1
            except (IndexError, ValueError, KeyError) as e:
                logger.error(
                    "Unable to parse positions. Make sure input is in list[str] format"
                    " (['A1', 'B02']) or use index generator from labware module."
                )
                logger.exception(e)
                sys.exit()

        self.og_df = self.df.copy()

    def reset(self) -> None:
        self.df = self.og_df.copy()

    def frame(self) -> pd.DataFrame:
        return self.df.fillna(0).astype(int)

    def total(self) -> int:
        return int(self.df.sum().sum())

    def ch2(self, n: int = 2, remove=True) -> list[tuple[EppiCarrier24, int]]:
        """Get tubes from a 24-tube carrier in 2-channel mode."""

        # Try to get n tubes, if less than n tubes left try again with 1 tube
        column = default_index_24.T[self.df.sum(axis=0) >= n].first_valid_index()
        for _ in range(2):
            try:
                row = self.df.T.loc[column] == 1
            except KeyError as e:
                logger.debug(
                    f"Column with {n} tubes not found in"
                    f" {self.carrier.layout_name()}., trying again with 1 tube."
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

        # Optionally remove tubes from df
        if remove:
            self.df[default_index_24.isin(index)] = pd.NA

        return [(self.carrier, i) for i in index]

    def static(self, index: list[str]) -> list[tuple[EppiCarrier24, int]]:
        """Get specific tubes from input list."""
        return [(self.carrier, default_index_24.at[i[0], int(i[1:])]) for i in index]


class lid:
    """Passthrough class for lids."""

    def __init__(
        self,
        labware: Lid,
    ) -> None:
        self.lid = labware

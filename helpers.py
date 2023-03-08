import os, csv, logging, itertools
import pandas as pd

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def prompt_file_path(message: str) -> str:
    """Prompt user for file path and check if it exists.

    Args:
        message (str): Message to prompt user.

    Returns:
        str: Path.
    """
    while True:
        path = input(f"{message}: ")
        if os.path.isfile(path):
            break
        else:
            print("File does not exist.")

    return path


def prompt_int(message: str, max: int) -> int:
    """Prompt user for integer.

    Args:
        message (str): Message to prompt user.

    Returns:
        int: Integer.
    """
    while True:
        prompt = input(f"{message}: ")
        try:
            value = int(prompt)
            if value > max:
                print(f"Please enter an integer smaller than {max}.")
                continue
            elif value < 0:
                print("Please enter a positive integer.")
                continue
            break
        except ValueError:
            print("Please enter an integer.")

    return value


def sort_384_indexes_2channel(series: pd.Series) -> pd.Series:
    """Sort 384-well indexes by searching for most well pairs with a distance of at least 4.
    First divide indexes by column, then sort by row. Find all pairs using itertools.combinations
    and check if distance is at least 4. Sort pairs by second index: most abundant index will be
    the highest in value as it will have largest difference vs other indexes. Then loop over pairs,
    extracting the first pair and removing all other pairs containing its values until no pairs are left.

    Args:
        series (pd.Series): Series with 384-well indexes for one plate.

    Returns:
        pd.Series: Sorted 384-well indexes as series with original DataFrame indexes.
    """

    sorted_cols = []
    unsorted_cols = []

    rows = "ABCDEFGHIJKLMNOP"

    unsorted_indexes = series.tolist()
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

    return pd.Series(sorted_cols + unsorted_cols, dtype=str, index=series.index)


def process_cherry_csv(csv_path: str, output_dir: str, prefix: str):
    """Get plate names from CSV file. Save as CSV file.

    Args:
        csv (str): Path to CSV file.
        output_dir (str): Path to output directory.
    """

    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        rows = [row[0].split(" ") for row in reader]
        wells = [row[0].split(".") for row in rows]

    df = pd.DataFrame(wells, columns=["source_plate", "source_well"])

    df.sort_values(by=["source_plate", "source_well"], inplace=True)

    for plate in df.source_plate.unique():
        start = df["source_well"][df.source_plate == plate].first_valid_index()
        end = df["source_well"][df.source_plate == plate].last_valid_index()

        sorted_source = sort_384_indexes_2channel(df.loc[start:end, "source_well"])
        df.loc[start:end, "source_well"] = sorted_source

    df[["source_well", "source_plate"]].to_csv(
        os.path.join(output_dir, f"{prefix}_wells.csv"), index=False, header=False
    )

    plates = pd.DataFrame([df.source_plate.unique()], index=["source"]).T

    plates.to_csv(
        os.path.join(output_dir, f"{prefix}_plates.csv"),
        index=False,
        header=False,
    )


def process_pm_csv(csv_path: str, output_dir: str, prefix: str):
    """Get plate names from CSV file. Save as CSV file.

    Args:
        csv (str): Path to CSV file.
        output_dir (str): Path to output directory.
    """

    df = pd.read_csv(
        csv_path, names=["source_well", "source_plate", "target_well", "target_plate"]
    )

    plates = pd.DataFrame(
        [df.source_plate.unique(), df.target_plate.unique()], index=["source", "target"]
    ).T

    plates.to_csv(
        os.path.join(output_dir, f"{prefix}_plate_map.csv"), index=False, header=False
    )


def place_plates(plates: list, labwares: list, type: str, done: int):
    done_plates = [1 for i in range(done)] + [0 for i in range(len(plates) - done)]
    print("-" * 80)
    print(f"Please place {type} plates in the following positions (ignore if done):")
    print("-" * 80)
    print(f"{'Plate':<10}{'Position':<10}{'Level':<8}{'Labware':<12}{'Done':<10}")

    for t in zip(plates, labwares, done_plates):
        pos, labware, level = t[1].layout_name().split("_")
        print(f"{t[0]:<10}{pos:<10}{level[-1]:<8}{labware:<12}{str(bool(t[2])):<10}")

    print("-" * 80)
    input(f"Press enter when all {type} plates are in place...")

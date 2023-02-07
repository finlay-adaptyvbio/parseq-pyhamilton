import os, csv
import pandas as pd


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

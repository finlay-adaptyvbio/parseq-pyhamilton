import logging, os, csv, requests
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
    logger.debug(f"Prompting for path: {message}")
    while True:
        path = input(f"{message}: ")
        if os.path.isfile(path):
            break
        else:
            print("File does not exist.")

    logger.debug(f"{message}: {path}")

    return path


def prompt_int(message: str, max: int) -> int:
    """Prompt user for integer.

    Args:
        message (str): Message to prompt user.

    Returns:
        int: Integer.
    """
    logger.debug(f"Prompting for integer: {message}")
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

    logger.debug(f"{message}: {value}")

    return value


def prompt_float(message: str, max: float) -> float:
    """Prompt user for foat.

    Args:
        message (str): Message to prompt user.

    Returns:
        float: Float.
    """
    logger.debug(f"Prompting for float: {message}")
    while True:
        prompt = input(f"{message}: ")
        try:
            value = float(prompt)
            if value > max:
                print(f"Please enter a float smaller than {max}.")
                continue
            elif value < 0:
                print("Please enter a positive float.")
                continue
            break
        except ValueError:
            print("Please enter a float.")

    logger.debug(f"{message}: {value}")

    return value


def process_cherry_csv(csv_path: str, output_dir: str) -> None:
    """Get plate names and wells from input CSV file. Save as CSV file.
    Sort wells by name and then plate.

    Args:
        csv_path (str): Path to CSV file.
        output_dir (str): Path to output directory.
    """
    logger.debug(f"Processing CSV at {csv_path}.")

    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        rows = [row[0].split(" ") for row in reader]
        wells = [row[0].split(".") for row in rows]

    df = pd.DataFrame(wells, columns=["source_plate", "source_well"])

    df.sort_values(by=["source_plate", "source_well"], inplace=True)

    df[["source_well", "source_plate"]].to_csv(
        os.path.join(output_dir, "cherry_wells.csv"), index=False, header=False
    )

    plates = pd.DataFrame([df.source_plate.unique()], index=["source"]).T

    plates.to_csv(
        os.path.join(output_dir, "cherry_plates.csv"),
        index=False,
        header=False,
    )

    logger.debug(f"Saved output CSVs to {output_dir}.")


def process_pm_csv(csv_path: str, output_dir: str, prefix: str):
    """Get plate names from CSV file. Save as CSV file.

    Args:
        csv_path (str): Path to CSV file.
        output_dir (str): Path to output directory.
    """
    logger.debug(f"Processing CSV at {csv_path}.")

    df = pd.read_csv(
        csv_path, names=["source_well", "source_plate", "target_well", "target_plate"]
    )

    plates = pd.DataFrame(
        [df.source_plate.unique(), df.target_plate.unique()], index=["source", "target"]
    ).T

    plates.to_csv(
        os.path.join(output_dir, f"{prefix}_plate_map.csv"), index=False, header=False
    )

    logger.debug(f"Saved output CSV to {output_dir}.")


# TODO: rewrite
def place_labware(labwares: list, type: str, names: list[str] = []):
    print("-" * 100)
    print(f"Please place labware in the following position(s) (ignore if done):\n")
    print(f"{'Name':<10}{'Position':<10}{'Level':<8}{'Labware'}")

    if not names:
        names = ["-" for _ in range(len(labwares))]

    for t in zip(labwares, names, list(range(len(labwares)))):
        assert isinstance(t, tuple)  # FIXME: hack to avoid type errors
        pos, *_ = t[0].layout_name().split("_")
        print(f"{t[1]:<10}{pos:<10}{t[2]:<8}{type}")

    input(f"\nPress enter when labware is in place...")


def notify(text) -> dict:
    """Send a notification to Slack

    Args:
        text (str): message to send

    Returns:
        dict: response from Slack API
    """
    slack_api_token = os.environ.get(
        "SLACK_API_TOKEN"
    )  # set as environment variable on Hamilton PC
    slack_channel = "#hamilton-events"  # public channel
    slack_icon_url = (  # icon downloaded from Biorender
        "https://i.ibb.co/L59D5KZ/Group-2164.png"
    )
    slack_user_name = "Hamilton"
    return requests.post(
        "https://slack.com/api/chat.postMessage",
        {
            "token": slack_api_token,
            "channel": slack_channel,
            "text": text,
            "icon_url": slack_icon_url,
            "username": slack_user_name,
            "blocks": None,
        },
    ).json()

import logging, os, csv, requests
import pandas as pd

# Logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def prompt_file_path(message: str) -> str:
    """Prompt user for file path and check if it exists.

    Args:
        - message: Message to prompt user.

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


def prompt_int(message: str, max: int, min: int = 0) -> int:
    """Prompt user for integer.

    Args:
        - message: Message to prompt user.
        - max: Maximum value.
        - min: Minimum value. Defaults to 0.

    Returns:
        - int: Integer.
    """
    logger.debug(f"Prompting for integer: {message}")
    while True:
        prompt = input(f"{message}: ")
        try:
            value = int(prompt)
            if value > max:
                print(f"Please enter an integer smaller than {max}.")
                continue
            elif value < min:
                print("Please enter a positive integer.")
                continue
            break
        except ValueError:
            print("Please enter an integer.")

    logger.debug(f"{message}: {value}")

    return value


def prompt_float(message: str, max: float, min: float = 0) -> float:
    """Prompt user for foat.

    Args:
        - message: Message to prompt user.
        - max: Maximum value.
        - min: Minimum value. Defaults to 0.

    Returns:
        - float: Float.
    """
    logger.debug(f"Prompting for float: {message}")
    while True:
        prompt = input(f"{message}: ")
        try:
            value = float(prompt)
            if value > max:
                print(f"Please enter a float smaller than {max}.")
                continue
            elif value < min:
                print("Please enter a positive float.")
                continue
            break
        except ValueError:
            print("Please enter a float.")

    logger.debug(f"{message}: {value}")

    return value


def process_cherry_csv(csv_path: str, output_dir: str):
    """Get plate names and wells from input CSV file. Save as CSV file.
    Sort wells by name and then plate.

    Args:
        - csv_path: Path to CSV file.
        - output_dir: Path to output directory.
    """
    logger.debug(f"Processing CSV at {csv_path}.")

    df = pd.read_csv(csv_path)

    l = [t for t in df.itertuples(index=False, name=None)]

    p = df["plate"].unique().tolist()

    df.to_csv(os.path.join(output_dir, "cherry.csv"), index=False, header=False)

    logger.debug(f"Saved output CSV to {output_dir}.")

    return l, p


def process_pm_csv(csv_path: str, output_dir: str, prefix: str) -> None:
    """Get plate names from CSV file. Save as CSV file.

    Args:
        - csv_path: Path to CSV file.
        - output_dir: Path to output directory.
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
def place_labware(labwares: list, type: str | int, names: list[str] = []):
    """
    Prompt user to place labware in the correct position.

    Args:
        - labwares: list of labware objects
        - type: type of labware
        - names: list of names for each labware. Defaults to [].
    """
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
        - text: message to send

    Returns:
        - dict: response from Slack API
    """
    slack_api_token = os.environ.get(
        "SLACK_API_TOKEN"
    )  # set as environment variable on Hamilton PC
    slack_channel = "#hamilton-events"  # public channel
    slack_icon_url = (  # icon downloaded from Biorender
        "https://i.ibb.co/L59D5KZ/Group-2164.png"
    )
    slack_user_name = "Hamilton"

    console = text.replace("*", "")  # remove markdown bold formatting
    print(console)

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

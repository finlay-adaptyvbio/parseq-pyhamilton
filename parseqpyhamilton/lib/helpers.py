"""
This module contains helper functions for user interaction and file processing.
"""

import logging
import os
import requests
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
    logger.debug("Prompting for path: %s", message)
    while True:
        path = input(f"{message}: ")
        if os.path.isfile(path):
            break
        else:
            print("File does not exist.")

    logger.debug("Selected path: %s", path)
    return path


def prompt_int(message: str, max_v: int, min_v: int = 0) -> int:
    """Prompt user for integer.

    Args:
        - message: Message to prompt user.
        - max: Maximum value.
        - min: Minimum value. Defaults to 0.

    Returns:
        - int: Integer.
    """
    logger.debug("Prompting for integer: %s", message)
    while True:
        prompt = input(f"{message}: ")
        try:
            value = int(prompt)
            if value > max_v:
                print(f"Please enter an integer smaller than {max}.")
                continue
            elif value < min_v:
                print("Please enter a positive integer.")
                continue
            break
        except ValueError:
            print("Please enter an integer.")

    logger.debug("%s: %s", message, value)

    return value


def prompt_float(message: str, max_v: float, min_v: float = 0) -> float:
    """Prompt user for float.

    Args:
        - message: Message to prompt user.
        - max: Maximum value.
        - min: Minimum value. Defaults to 0.

    Returns:
        - float: Float.
    """
    logger.debug("Prompting for float: %s", message)
    while True:
        prompt = input(f"{message}: ")
        try:
            value = float(prompt)
            if value > max_v:
                print(f"Please enter a float smaller than {max}.")
                continue
            elif value < min_v:
                print("Please enter a positive float.")
                continue
            break
        except ValueError:
            print("Please enter a float.")

    logger.debug("%s: %s", message, value)

    return value


def process_cherry_csv(csv_path: str, output_dir: str):
    """Get plate names and wells from input CSV file. Save as CSV file.
    Sort wells by name and then plate.

    Args:
        - csv_path: Path to CSV file.
        - output_dir: Path to output directory.
    """
    logger.debug("Processing CSV at %s.", csv_path)

    df = pd.read_csv(csv_path)

    l = [t for t in df.itertuples(index=False, name=None)]

    p = df["plate"].unique().tolist()

    df.to_csv(os.path.join(output_dir, "cherry.csv"), index=False, header=False)

    logger.debug("Saved output CSV to %s.", output_dir)

    return l, p


def process_pm_csv(csv_path: str, output_dir: str, prefix: str) -> None:
    """Get plate names from CSV file. Save as CSV file.

    Args:
        - csv_path: Path to CSV file.
        - output_dir: Path to output directory.
    """
    logger.debug("Processing CSV at %s.", csv_path)

    df = pd.read_csv(
        csv_path, names=["source_well", "source_plate", "target_well", "target_plate"]
    )

    plates = pd.DataFrame(
        [df.source_plate.unique(), df.target_plate.unique()], index=["source", "target"]
    ).T

    plates.to_csv(
        os.path.join(output_dir, f"{prefix}_plate_map.csv"), index=False, header=False
    )

    logger.debug("Saved output CSV to %s.", output_dir)


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
        timeout=10,
    ).json()

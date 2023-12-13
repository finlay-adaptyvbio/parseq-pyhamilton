"""
This module provides functionality for managing method and deck states.
"""

# Imports
import logging
import shelve
import json

# Logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# Functions
def recover_state(path) -> dict:
    """
    Recovers state from a JSON file at the provided path and allows the user to manually set values.

    Args:
        path (str): The path to the JSON file containing the state.

    Returns:
        dict: The recovered state.
    """
    logger.debug("Recovering state from: %s", path)
    state = load_state(path)

    while True:
        print_state(state)
        question = input(
            "Are there any values to set manually? (type # or 0 for none): "
        )
        try:
            answer = int(question)
            if answer in range(1, len(state.keys()) + 1):
                key = list(state.keys())[answer - 1]
                value = input(f"Enter a new value for {key}: ")
                while True:
                    try:
                        set_state(state, path, key, int(value))
                    except ValueError as e:
                        logger.exception(e)
                        continue
                    break
            elif answer == 0:
                break
            continue
        except ValueError as e:
            logger.exception(e)
            continue
    return state


def load_state(path: str) -> dict:
    """
    Loads state from a JSON file at the provided path.

    Args:
        path (str): The path to the JSON file containing the state.

    Returns:
        dict: The loaded state.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            logger.debug("Path is valid! Loading state...")
            state = json.load(file)
        return state
    except (FileNotFoundError, IsADirectoryError) as e:
        logger.exception(e)
        raise e


def save_state(state: dict, path: str) -> None:
    """
    Saves state in memory to disk.

    Args:
        state (dict): The state to be saved.
        path (str): The path to the file where the state will be saved.
    """
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(state, file, indent=4)
    except (FileNotFoundError, IsADirectoryError) as e:
        logger.exception(e)
        raise e


def set_state(state: dict, path: str, key: str, value: int) -> None:
    """
    Sets state variables from key: value pair.

    Args:
        state (dict): The state to be updated.
        path (str): The path to the file where the state will be saved.
        key (str): The key of the state variable to be updated.
        value (int): The new value of the state variable.
    """
    state[key] = value
    save_state(state, path)


def print_state(state: dict) -> None:
    """
    Formats and prints state variables.

    Args:
        state (dict): The state to be printed.
    """
    print(f"{'-' * 40}")
    print(f"{'#':<5}{'Key':<25}{'Value':<25}")
    print(f"{'-' * 40}")
    for idx, key in enumerate(state.keys()):
        print(f"{idx + 1:<5}{key:<25}{state[key]:<25}")
    print(f"{'-' * 40}")


def save_deck_state(path: str, deck: dict) -> None:
    """
    Saves deck state in memory to disk.

    Args:
        path (str): The path to the file where the deck state will be saved.
        deck (dict): The deck state to be saved.
    """
    try:
        with shelve.open(path, writeback=True) as shelf:
            shelf.update(deck)
    except (FileNotFoundError, IsADirectoryError) as e:
        logger.exception(e)
        raise e


def load_deck_state(path: str) -> shelve.Shelf:
    """
    Loads deck state from a shelve db at the provided path.

    Args:
        path (str): The path to the shelve db containing the deck state.

    Returns:
        shelve.Shelf: The loaded deck state.
    """
    try:
        logger.debug("Path is valid! Loading deck...")
        return shelve.open(path, writeback=True, flag="r")
    except (FileNotFoundError, IsADirectoryError) as e:
        logger.exception(e)
        raise e

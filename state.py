import logging, shelve, json

# Logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# Interactive prompt for state recovery
def recover_state(path) -> dict:
    logger.debug(f"Recovering state from: {path}")
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


# Load state file (json) from provided path
def load_state(path) -> dict:
    try:
        with open(path, "r") as f:
            logger.debug("Path is valid! Loading state...")
            state = json.load(f)
        return state
    except (FileNotFoundError, IsADirectoryError) as e:
        logger.exception(e)
        raise e


# Save state in memory to disk
def save_state(state, path) -> None:
    try:
        with open(path, "w") as f:
            json.dump(state, f, indent=4)
    except (FileNotFoundError, IsADirectoryError) as e:
        logger.exception(e)
        raise e


# Set state variables from key: value pair
def set_state(state, path, key, value) -> None:
    state[key] = value
    save_state(state, path)


# Format and print state variables
def print_state(state) -> None:
    print(f"{'-' * 40}")
    print(f"{'#':<5}{'Key':<25}{'Value':<25}")
    print(f"{'-' * 40}")
    for idx, key in enumerate(state.keys()):
        print(f"{idx + 1:<5}{key:<25}{state[key]:<25}")
    print(f"{'-' * 40}")


# Save deck state as shelve db
def save_deck_state(path, deck) -> None:
    try:
        with shelve.open(path) as shelf:
            shelf.update(deck)
    except (FileNotFoundError, IsADirectoryError) as e:
        logger.exception(e)
        raise e


# Load shelve db from provided path
def load_deck_state(path) -> shelve.Shelf:
    try:
        with open(path, "r") as f:
            logger.debug("Path is valid! Loading deck...")
        return shelve.open(path, writeback=True)
    except (FileNotFoundError, IsADirectoryError) as e:
        logger.exception(e)
        raise e

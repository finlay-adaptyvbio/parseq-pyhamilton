"""
This script is the main entry point for the adaptyvpyhamilton package. It imports necessary modules
and sets up logging configuration. It prompts the user to select a method and a run, and then either
creates a new run or recovers an existing one. The selected method and run are used to load the
corresponding layout and state files, and to create a deck object with labware dataframes. The deck
object is then used to execute the method and update the state file.
"""

# Imports
import os
import sys
import shelve
import importlib
import shutil
import time
import datetime
import logging
import logging.config

# Local imports
from .lib import deck as dk
from .lib import helpers as hp
from .lib import state as st

# Paths
root = os.path.dirname(os.path.abspath(__file__))
state_dir_path = os.path.join(root, "states")
layout_dir_path = os.path.join(root, "layouts")
script_dir_path = os.path.join(root, "scripts")
runs_dir_path = os.path.join(root, "runs")

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "simple",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": "DEBUG", "propagate": True},
    },
}

# Logging
logging.getLogger("parse").setLevel(logging.WARNING)
logging.config.dictConfig(LOGGING)
logger = logging.getLogger()


# Main entry point
if __name__ == "__main__":
    # Find existing methods
    methods = [
        f[:-3]
        for f in os.listdir(script_dir_path)
        if f.endswith(".py") and not f.startswith("__")
    ]

    # Display valid methods
    if len(methods) > 0:
        print(f"{'#':<5}{'method':<25}")
        print(f"{'-' * 80}")
        for i, method in enumerate(methods):
            print(f"{i + 1:<5}{method:<25}")
        print(f"{'-' * 80}")
    else:
        logger.error("No methods found!")
        sys.exit()

    # Prompt user for method
    while True:
        idx = input("Method id: ")
        try:
            method_idx = int(idx)
            method = methods[method_idx - 1]
        except (ValueError, IndexError) as e:
            logger.error("Invalid method id.")
            continue
        break

    # Find existing runs
    runs = [
        d
        for d in os.listdir(runs_dir_path)
        if os.path.isdir(os.path.join(runs_dir_path, d))
    ]

    # Display runs if any exist
    if len(runs) > 0:
        print(f"{'#':<5}{'run_id':<25}{'methods':<25}")
        print(f"{'-' * 80}")
        for i, run in enumerate(runs):
            methods = [
                f[:-5]
                for f in os.listdir(os.path.join(runs_dir_path, run))
                if f.endswith(".json")
            ]
            print(f"{i + 1:<5}{run:<25}{methods}")
        print(f"{'-' * 80}")

    # Prompt user for run
    while True:
        idx = input("Run id (0 for new): ")
        try:
            run_idx = int(idx)

            # Create new run
            if run_idx == 0:
                run_id = hex(int((time.time() % 3600e4) * 1e6))
                run_dir_path = os.path.join(runs_dir_path, run_id)
                os.makedirs(run_dir_path, exist_ok=True)

                layout_path = os.path.join(run_dir_path, f"{method}.lay")
                state_path = os.path.join(run_dir_path, f"{method}.json")
                labware_path = os.path.join(run_dir_path, f"{method}")

                shutil.copy(os.path.join(layout_dir_path, f"{method}.lay"), layout_path)

                shutil.copy(os.path.join(state_dir_path, f"{method}.json"), state_path)
                state = st.load_state(state_path)
                st.save_state(state, state_path)

                deck = dk.get_deck(layout_path)
                deck = dk.add_dataframes(deck)
                st.save_deck_state(labware_path, deck)

            # Recover or overwrite existing run
            else:
                try:
                    run_id = runs[run_idx - 1]
                    methods = [
                        f[:-5]
                        for f in os.listdir(os.path.join(runs_dir_path, run_id))
                        if f.endswith(".json")
                    ]

                    if method in methods:
                        while True:
                            recover = input(
                                f"Run {run_id} already contains {method} method."
                                " Recover this run? (y/n) "
                            )

                            if recover == "y":
                                run_dir_path = os.path.join(runs_dir_path, run_id)

                                state_path = os.path.join(
                                    run_dir_path, f"{method}.json"
                                )
                                try:
                                    with open(state_path, "rt", encoding="utf-8") as f:
                                        logger.debug("State path: %s", state_path)
                                except FileNotFoundError as e:
                                    logger.exception(e)
                                    raise ValueError(
                                        f"State file not found for {method} method. Was"
                                        " the correct method specified?"
                                    ) from e
                                state = st.recover_state(state_path)

                                layout_path = os.path.join(
                                    run_dir_path, f"{method}.lay"
                                )
                                try:
                                    with open(layout_path, "rt", encoding="utf-8") as f:
                                        logger.debug("Layout path: %s", layout_path)
                                except FileNotFoundError as e:
                                    logger.exception(e)
                                    raise ValueError(
                                        f"Layout file not found for {method} method."
                                        " Was the correct method specified?"
                                    ) from e

                                labware_path = os.path.join(run_dir_path, f"{method}")
                                try:
                                    with open(
                                        f"{labware_path}.dat", "rt", encoding="utf-8"
                                    ) as f:
                                        logger.debug("Labware path: %s", labware_path)
                                except FileNotFoundError as e:
                                    logger.exception(e)
                                    raise ValueError(
                                        f"Deck file not found for {method} method."
                                        " Was the correct method specified?"
                                    ) from e

                            elif recover == "n":
                                run_dir_path = os.path.join(runs_dir_path, run_id)
                                now = datetime.datetime.now().strftime("%y.%m.%d_%H%M")
                                backup_dir_path = os.path.join(run_dir_path, now)
                                os.makedirs(backup_dir_path, exist_ok=True)

                                method_files = [
                                    f
                                    for f in os.listdir(run_dir_path)
                                    if f.find(f"{method}") > -1
                                ]
                                for method_file in method_files:
                                    shutil.move(
                                        os.path.join(run_dir_path, method_file),
                                        os.path.join(
                                            backup_dir_path, f"{method_file}.bak"
                                        ),
                                    )

                                layout_path = os.path.join(
                                    run_dir_path, f"{method}.lay"
                                )
                                state_path = os.path.join(
                                    run_dir_path, f"{method}.json"
                                )
                                labware_path = os.path.join(run_dir_path, f"{method}")

                                shutil.copy(
                                    os.path.join(layout_dir_path, f"{method}.lay"),
                                    layout_path,
                                )

                                shutil.copy(
                                    os.path.join(state_dir_path, f"{method}.json"),
                                    state_path,
                                )
                                state = st.load_state(state_path)
                                st.save_state(state, state_path)

                                deck = dk.get_deck(layout_path)
                                deck = dk.add_dataframes(deck)
                                st.save_deck_state(labware_path, deck)

                            else:
                                logger.error("Please type y or n.")
                                continue
                            break
                    else:
                        # File paths
                        run_dir_path = os.path.join(runs_dir_path, run_id)
                        layout_path = os.path.join(run_dir_path, f"{method}.lay")
                        state_path = os.path.join(run_dir_path, f"{method}.json")
                        labware_path = os.path.join(run_dir_path, f"{method}")

                        shutil.copy(
                            os.path.join(layout_dir_path, f"{method}.lay"),
                            layout_path,
                        )

                        shutil.copy(
                            os.path.join(state_dir_path, f"{method}.json"),
                            state_path,
                        )
                        state = st.load_state(state_path)
                        st.save_state(state, state_path)

                        deck = dk.get_deck(layout_path)
                        deck = dk.add_dataframes(deck)
                        st.save_deck_state(labware_path, deck)

                except IndexError:
                    logger.error("Invalid run id.")
                    continue
        except ValueError:
            logger.error("Invalid run id.")
            continue
        break

    # Persistent logging
    f_method_handler = logging.FileHandler(os.path.join(run_dir_path, f"{method}.log"))
    f_method_handler.setLevel(logging.DEBUG)
    f__method_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    f_method_handler.setFormatter(f__method_format)
    logger.addHandler(f_method_handler)

    # Run method
    for attempt in range(3):
        script = importlib.import_module(f".{method}", "methods")
        try:
            with shelve.open(labware_path, writeback=True) as shelf:
                script.run(shelf, state, run_dir_path)
        except KeyboardInterrupt:
            logger.warning("Keyboard interrupt received. Exiting...")
            hp.notify(f"Method {method} for run {run_id} interrupted by user.")
            sys.exit()
        except ValueError as e:
            logger.exception(e)
            hp.notify(
                f"Method {method} for run {run_id} failed. Restarting"
                f" ({attempt + 1}/3)..."
            )
            continue
        else:
            hp.notify(f"Method {method} for run {run_id} completed successfully!")
            break
    else:
        hp.notify(f"Method {method} for run {run_id} failed 3 times. Exiting...")
        sys.exit()

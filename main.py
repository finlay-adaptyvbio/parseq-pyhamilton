import os, argparse, sys, shelve, importlib, shutil, time, datetime
import logging, logging.config

import deck as dk
import helpers as hp
import state as st

# Folders and paths
root = os.path.dirname(os.path.abspath(__file__))
state_dir_path = os.path.join(root, "states")
layout_dir_path = os.path.join(root, "layouts")
script_dir_path = os.path.join(root, "scripts")
runs_dir_path = os.path.join(root, "runs")

# Logging settings
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

logging.getLogger("parse").setLevel(logging.WARNING)
logging.config.dictConfig(LOGGING)
logger = logging.getLogger()


# CLI arguments for argparse
def parse_args():
    parser = argparse.ArgumentParser(
        description="Hamilton script runner",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser.add_argument(
        "method",
        metavar="method",
        type=str,
        help="(%(type)s) method to run (%(choices)s)",
        choices=[
            f[:-3]
            for f in os.listdir(script_dir_path)
            if f.endswith(".py") and not f.startswith("__")
        ],
    )
    return parser


# Main script starts here
if __name__ == "__main__":
    # Process arguments
    parser = parse_args()
    args = parser.parse_args()
    method = args.method

    # Find previous runs
    runs = [
        d
        for d in os.listdir(runs_dir_path)
        if os.path.isdir(os.path.join(runs_dir_path, d))
    ]

    # Format and print runs found
    if len(runs) > 0:
        print(f"{'#':<5}{'run_id':<25}{'methods':<25}")
        print(f"{'-' * 80}")
        for idx, run in enumerate(runs):
            methods = [
                f[:-5]
                for f in os.listdir(os.path.join(runs_dir_path, run))
                if f.endswith(".json")
            ]
            print(f"{idx + 1:<5}{run:<25}{methods}")
        print(f"{'-' * 80}")

    # Prompt for run id, possible choices are:
    # 1. New run
    # 2. Try to recover method in previous run
    # 3. Overwrite method in previous run
    while True:
        # Choose previous run or start new run
        run_idx = input("Run id (0 for new): ")
        try:
            run_idx = int(run_idx)

            # Start new run: generate new state, decck and layout from templates for this method
            if run_idx == 0:
                # Generate new run id and make required folders
                run_id = hex(int((time.time() % 3600e4) * 1e6))
                run_dir_path = os.path.join(runs_dir_path, run_id)
                os.makedirs(run_dir_path, exist_ok=True)

                # File paths
                layout_path = os.path.join(run_dir_path, f"{method}.lay")
                state_path = os.path.join(run_dir_path, f"{method}.json")
                labware_path = os.path.join(run_dir_path, f"{method}")

                # Copy template layout and state files, generate new deck from layout
                shutil.copy(os.path.join(layout_dir_path, f"{method}.lay"), layout_path)

                shutil.copy(os.path.join(state_dir_path, f"{method}.json"), state_path)
                state = st.load_state(state_path)
                st.save_state(state, state_path)

                deck = dk.get_deck(layout_path)
                deck = dk.add_dataframes(deck)
                st.save_deck_state(labware_path, deck)

            # Start method in previous run
            else:
                try:
                    # Find methods started/completed in chosen run
                    run_id = runs[run_idx - 1]
                    methods = [
                        f[:-5]
                        for f in os.listdir(os.path.join(runs_dir_path, run_id))
                        if f.endswith(".json")
                    ]

                    # Check if method exists for this run
                    if method in methods:
                        while True:
                            # Check if method should be recovered/restarted
                            recover = input(
                                f"Run {run_id} already contains {method} method."
                                " Recover this run? (y/n) "
                            )

                            # Try and recover last attempt of this method
                            if recover == "y":
                                run_dir_path = os.path.join(runs_dir_path, run_id)

                                # Load state from last attempt
                                state_path = os.path.join(
                                    run_dir_path, f"{method}.json"
                                )
                                try:
                                    with open(state_path, "r") as f:
                                        logger.debug(f"State path: {state_path}")
                                        pass
                                except FileNotFoundError as e:
                                    logger.exception(e)
                                    raise ValueError(
                                        "State file not found for {method} method. Was"
                                        " the correct method specified?"
                                    )
                                state = st.recover_state(state_path)

                                # Load layout from last attempt
                                layout_path = os.path.join(
                                    run_dir_path, f"{method}.lay"
                                )
                                try:
                                    with open(layout_path, "r") as f:
                                        logger.debug(f"Layout path: {layout_path}")
                                        pass
                                except FileNotFoundError as e:
                                    logger.exception(e)
                                    raise ValueError(
                                        "Layout file not found for {method} method. Was"
                                        " the correct method specified?"
                                    )

                                # Load deck from last attempt
                                labware_path = os.path.join(run_dir_path, f"{method}")
                                try:
                                    with open(f"{labware_path}.dat", "r") as f:
                                        logger.debug(f"Labware path: {labware_path}")
                                        pass
                                except FileNotFoundError as e:
                                    logger.exception(e)
                                    raise ValueError(
                                        "Deck file not found for {method} method."
                                        " Was the correct method specified?"
                                    )

                            # Backup files generated by previous attempt and restart method
                            elif recover == "n":
                                # Backup method files in timestamped folder
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

                                # File paths
                                layout_path = os.path.join(
                                    run_dir_path, f"{method}.lay"
                                )
                                state_path = os.path.join(
                                    run_dir_path, f"{method}.json"
                                )
                                labware_path = os.path.join(run_dir_path, f"{method}")

                                # Copy template layout and state files, generate new deck from layout
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
                    # Start method in previous run if no previous attempt was found
                    else:
                        # File paths
                        run_dir_path = os.path.join(runs_dir_path, run_id)
                        layout_path = os.path.join(run_dir_path, f"{method}.lay")
                        state_path = os.path.join(run_dir_path, f"{method}.json")
                        labware_path = os.path.join(run_dir_path, f"{method}")

                        # Copy template layout and state files, generate new deck from layout
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

    # Method logging settings for log file
    f_method_handler = logging.FileHandler(os.path.join(run_dir_path, f"{method}.log"))
    f_method_handler.setLevel(logging.DEBUG)
    f__method_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    f_method_handler.setFormatter(f__method_format)
    logger.addHandler(f_method_handler)

    # Run method, on failure notify and restart (max 3 retries)
    # If cancelled, notify and stop
    for attempt in range(3):
        script = importlib.import_module(f".{method}", "scripts")
        try:
            with shelve.open(labware_path, writeback=True) as shelf:
                script.run(shelf, state, run_dir_path)
        # Catch method cancel by Ctrl+C/Ctrl+Z
        except KeyboardInterrupt:
            logger.warning("Keyboard interrupt received. Exiting...")
            hp.notify(f"Method {method} for run {run_id} interrupted by user.")
            sys.exit()
        # Error catch-all
        except Exception as e:
            logger.exception(e)
            hp.notify(
                f"Method {method} for run {run_id} failed. Restarting"
                f" ({attempt + 1}/3)..."
            )
            continue
        # Notify on successful method completion
        else:
            hp.notify(f"Method {method} for run {run_id} completed successfully!")
            break
    else:
        hp.notify(f"Method {method} for run {run_id} failed 3 times. Exiting...")
        sys.exit()

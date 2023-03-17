#!/usr/bin/python3

import os, argparse, requests, time, datetime, shutil, traceback
import logging, logging.config

import deck as dk
import state as st
import helpers as hp

# Folders

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

# CLI arguments


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
        choices=[f[:-3] for f in os.listdir(script_dir_path) if f.endswith(".py")],
    )
    return parser


# Main script starts here

if __name__ == "__main__":
    # Process arguments

    parser = parse_args()
    args = parser.parse_args()

    logger.debug(f"Arguments: {args}")

    method = args.method

    runs = [
        d
        for d in os.listdir(runs_dir_path)
        if os.path.isdir(os.path.join(runs_dir_path, d))
    ]

    logger.info(f"Found {len(runs)} previous runs.")
    logger.debug(f"Runs: {runs}")

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

    # Prompt for run id

    while True:
        run_idx = input("Run id (0 for new): ")
        try:
            run_idx = int(run_idx)

            # Start new run

            if run_idx == 0:
                logger.info(f"Generating new run id for {method} run...")
                run_id = hex(int((time.time() % 3600e4) * 1e6))
                logger.debug(f"Run id: {run_id}")
                run_dir_path = os.path.join(runs_dir_path, run_id)
                os.makedirs(run_dir_path, exist_ok=True)

                layout_path = os.path.join(run_dir_path, f"{method}.lay")
                state_path = os.path.join(run_dir_path, f"{method}.json")

                logger.info(f"Using default layout for {method} method.")
                shutil.copy(os.path.join(layout_dir_path, f"{method}.lay"), layout_path)

                logger.info(f"Using default state for {method} method.")
                shutil.copy(os.path.join(state_dir_path, f"{method}.json"), state_path)
                state = st.load_state(state_path)

                st.save_state(state, state_path)

                get_input_files = True

                logger.info(f"Starting run {run_id}")

            # Check if method already exists and prompt to recover

            else:
                try:
                    run_id = runs[run_idx - 1]
                    methods = [
                        f[:-5]
                        for f in os.listdir(os.path.join(runs_dir_path, run_id))
                        if f.endswith(".json")
                    ]
                    logger.debug(f"Methods: {methods}")
                    if method in methods:
                        while True:
                            recover = input(
                                f"Run {run_id} already contains {method} method."
                                " Recover this run? (y/n) "
                            )
                            if recover == "y":
                                run_dir_path = os.path.join(runs_dir_path, run_id)
                                logger.info(
                                    f"Recovering state for {method} method of run"
                                    f" {run_id}..."
                                )
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

                                logger.info(
                                    f"Recovering layout for {method} method of run"
                                    f" {run_id}..."
                                )
                                layout_path = os.path.join(
                                    run_dir_path, f"{method}.lay"
                                )
                                try:
                                    with open(layout_path, "r") as f:
                                        logger.debug(f"State path: {layout_path}")
                                        pass
                                except FileNotFoundError as e:
                                    logger.exception(e)
                                    raise ValueError(
                                        "Layout file not found for {method} method. Was"
                                        " the correct method specified?"
                                    )

                                get_input_files = False

                                logger.info(f"Resuming run {run_id}")

                            elif recover == "n":
                                run_dir_path = os.path.join(runs_dir_path, run_id)
                                now = datetime.datetime.now().strftime("%y.%m.%d_%H%M")
                                backup_dir_path = os.path.join(run_dir_path, now)
                                os.makedirs(backup_dir_path, exist_ok=True)
                                logger.info(
                                    f"Backing up previous {method} run in"
                                    f" {run_id}/{now}"
                                )

                                method_files = [
                                    f
                                    for f in os.listdir(run_dir_path)
                                    if f.find(f"{method}") > -1
                                ]
                                logger.debug(f"Method files: {method_files}")
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

                                logger.info(
                                    f"Using default layout for {method} method."
                                )
                                shutil.copy(
                                    os.path.join(layout_dir_path, f"{method}.lay"),
                                    layout_path,
                                )

                                logger.info(f"Using default state for {method} method.")
                                shutil.copy(
                                    os.path.join(state_dir_path, f"{method}.json"),
                                    state_path,
                                )
                                state = st.load_state(state_path)

                                st.save_state(state, state_path)

                                get_input_files = True

                                logger.info(f"Restarting run {run_id}")

                            else:
                                logger.error("Please type y or n.")
                                continue
                            break
                    else:
                        run_dir_path = os.path.join(runs_dir_path, run_id)
                        layout_path = os.path.join(run_dir_path, f"{method}.lay")
                        state_path = os.path.join(run_dir_path, f"{method}.json")

                        logger.info(f"Using default layout for {method} method.")
                        shutil.copy(
                            os.path.join(layout_dir_path, f"{method}.lay"),
                            layout_path,
                        )

                        logger.info(f"Using default state for {method} method.")
                        shutil.copy(
                            os.path.join(state_dir_path, f"{method}.json"),
                            state_path,
                        )
                        state = st.load_state(state_path)

                        st.save_state(state, state_path)

                        get_input_files = True

                        logger.info(f" Starting run {run_id} ")
                except IndexError:
                    logger.error("Invalid run id.")
                    continue
        except ValueError:
            logger.error("Invalid run id.")
            continue
        break

    # Method logging settings

    f_method_handler = logging.FileHandler(os.path.join(run_dir_path, f"{method}.log"))
    f_method_handler.setLevel(logging.DEBUG)
    f__method_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    f_method_handler.setFormatter(f__method_format)
    logger.addHandler(f_method_handler)

    # Run script

    logger.debug(f"{'Method:':<8}{method}")
    logger.debug(f"{'State:':<8}{state_path}")
    logger.debug(f"{'Layout:':<8}{layout_path}")

    # Get necessary input files depending on method and copy to temp dir

    match method:
        case "pooling":
            from scripts import pooling as script

        case "pcr_colony":
            from scripts import pcr_colony as script

        case "pcr_barcode":
            from scripts import pcr_barcode as script

        case "pm_emptying":
            # get sorted_well_map.csv
            # if recovering run, don't need to copy sorted_well_map.csv

            from scripts import pm_emptying as script

            if get_input_files:
                well_map_path = hp.prompt_file_path(
                    "Path to sorted_well_map.csv for run {run_id}"
                )
                shutil.copy(
                    well_map_path,
                    os.path.join(run_dir_path, f"{method}_sorted_well_map.csv"),
                )
                hp.process_pm_csv(well_map_path, run_dir_path, method)

        case "pm_filling":
            # get sorted_well_map.csv
            # if recovering run, don't need to copy sorted_well_map.csv

            from scripts import pm_filling as script

            if get_input_files:
                well_map_path = hp.prompt_file_path(
                    f"Path to sorted_well_map.csv for run {run_id}"
                )
                shutil.copy(
                    well_map_path,
                    os.path.join(run_dir_path, f"{method}_sorted_well_map.csv"),
                )
                hp.process_pm_csv(well_map_path, run_dir_path, method)

        case "cherry_picking":
            # get sorted_well_list.csv
            # if recovering run, don't need to copy sorted_well_list.csv

            from scripts import cherry_picking as script

            if get_input_files:
                well_list_path = hp.prompt_file_path(
                    f"Path to cherry.csv for run {run_id}"
                )
                shutil.copy(well_list_path, os.path.join(run_dir_path, f"{method}.csv"))
                hp.process_cherry_csv(well_list_path, run_dir_path, method)

        case "plate_filling":
            from scripts import plate_filling as script

        case "purification":
            from scripts import purification as script

        case _:
            # This shoudn't be needed but avoids type error
            logger.error(f"Method {method} not found.")
            parser.error(f"Method {method} not found.")

    deck = dk.get_deck(layout_path)

    # Run method

    try:
        script.run(deck, state, state_path, run_dir_path)
        hp.notify(f"Method {method} for run {run_id} completed successfully!")
    except KeyboardInterrupt:
        logger.warn("Keyboard interrupt received. Exiting...")
        hp.notify(f"Method {method} for run {run_id} interrupted.")
    except Exception as e:
        logger.exception(e)
        # hp.notify(traceback.format_exc())
        hp.notify(f"Method {method} for run {run_id} failed.")
        raise e

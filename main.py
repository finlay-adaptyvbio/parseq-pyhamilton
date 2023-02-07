#!/usr/bin/python3

import os, sys, argparse, requests, atexit, time, datetime, shutil

import deck as dk
import state as st
import helpers as hp

# Notification settings for Slack on script exit

slack_token = "xoxb-4612406885399-4627932099202-REL8YycwsJbdBKYkGJ7qeq75"
slack_channel = "#main"
slack_icon_emoji = ":see_no_evil:"
slack_user_name = "pyhamilton"


def notify(text):
    return requests.post(
        "https://slack.com/api/chat.postMessage",
        {
            "token": slack_token,
            "channel": slack_channel,
            "text": text,
            "icon_emoji": slack_icon_emoji,
            "username": slack_user_name,
            "blocks": None,
        },
    ).json()


# atexit.register(notify, "Script complete or error.")

# Folders

root = os.path.dirname(os.path.abspath(__file__))
state_dir_path = os.path.join(root, "states")
layout_dir_path = os.path.join(root, "layouts")
script_dir_path = os.path.join(root, "scripts")
runs_dir_path = os.path.join(root, "runs")


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

    method = args.method

    runs = [
        d
        for d in os.listdir(runs_dir_path)
        if os.path.isdir(os.path.join(runs_dir_path, d))
    ]

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
                print(f"Generating new run id for {method} run...")
                run_id = hex(int((time.time() % 3600e4) * 1e6))
                run_dir_path = os.path.join(runs_dir_path, run_id)
                os.makedirs(run_dir_path, exist_ok=True)

                layout_path = os.path.join(run_dir_path, f"{method}.lay")
                state_path = os.path.join(run_dir_path, f"{method}.json")

                print(f"Using default layout for {method} method.")
                shutil.copy(os.path.join(layout_dir_path, f"{method}.lay"), layout_path)

                print(f"Using default state for {method} method.")
                shutil.copy(os.path.join(state_dir_path, f"{method}.json"), state_path)
                state = st.load_state(state_path)

                st.save_state(state, state_path)

                get_input_files = True

                print(f"\n--- Starting run {run_id} ---\n")

            # Check if method already exists and prompt to recover

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
                                print(
                                    f"Recovering state for {method} method of run"
                                    f" {run_id}..."
                                )
                                state_path = os.path.join(
                                    run_dir_path, f"{method}.json"
                                )
                                try:
                                    with open(state_path, "r") as f:
                                        pass
                                except FileNotFoundError:
                                    raise ValueError(
                                        "State file not found for {method} method. Was"
                                        " the correct method specified?"
                                    )
                                state = st.recover_state(state_path)

                                print(
                                    f"Recovering layout for {method} method of run"
                                    f" {run_id}..."
                                )
                                layout_path = os.path.join(
                                    run_dir_path, f"{method}.lay"
                                )
                                try:
                                    with open(layout_path, "r") as f:
                                        pass
                                except FileNotFoundError:
                                    raise ValueError(
                                        "Layout file not found for {method} method. Was"
                                        " the correct method specified?"
                                    )

                                get_input_files = False

                                print(f"\n--- Resuming run {run_id} ---\n")

                            elif recover == "n":
                                run_dir_path = os.path.join(runs_dir_path, run_id)
                                now = datetime.datetime.now().strftime("%y.%m.%d_%H%M")
                                backup_dir_path = os.path.join(run_dir_path, now)
                                print(
                                    f"Backing up previous {method} run in"
                                    f" {run_id}/{now}"
                                )

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

                                print(f"Using default layout for {method} method.")
                                shutil.copy(
                                    os.path.join(layout_dir_path, f"{method}.lay"),
                                    layout_path,
                                )

                                print(f"Using default state for {method} method.")
                                shutil.copy(
                                    os.path.join(state_dir_path, f"{method}.json"),
                                    state_path,
                                )
                                state = st.load_state(state_path)

                                st.save_state(state, state_path)

                                get_input_files = True

                                print(f"\n--- Restarting run {run_id} ---\n")

                            else:
                                print("Please type y or n.")
                                continue
                            break
                    else:
                        run_dir_path = os.path.join(runs_dir_path, run_id)
                        layout_path = os.path.join(run_dir_path, f"{method}.lay")
                        state_path = os.path.join(run_dir_path, f"{method}.json")

                        print(f"Using default layout for {method} method.")
                        shutil.copy(
                            os.path.join(layout_dir_path, f"{method}.lay"),
                            layout_path,
                        )

                        print(f"Using default state for {method} method.")
                        shutil.copy(
                            os.path.join(state_dir_path, f"{method}.json"),
                            state_path,
                        )
                        state = st.load_state(state_path)

                        st.save_state(state, state_path)

                        get_input_files = True

                        print(f"\n--- Starting run {run_id} ---\n")
                except IndexError:
                    print("Invalid run id.")
                    continue
        except ValueError:
            print("Invalid run id.")
            continue
        break

    # Run script

    print(f"{'Method:':<8}{method}")
    print(f"{'State:':<8}{state_path}")
    print(f"{'Layout:':<8}{layout_path}")

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
                    "Path to sorted_well_map.csv for run {run_id}: "
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
                    f"Path to sorted_well_map.csv for run {run_id}: "
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
                    f"Path to cherry.csv for run {run_id}: "
                )
                shutil.copy(well_list_path, os.path.join(run_dir_path, f"{method}.csv"))
                hp.process_cherry_csv(well_list_path, run_dir_path, method)

        case _:
            # This shoudn't be needed but avoids type error

            raise ValueError(f"Method {method} not found.")

    deck = dk.get_deck(layout_path)
    script.run(deck, state, state_path, run_dir_path)

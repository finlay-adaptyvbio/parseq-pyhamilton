import os, shutil, csv, logging, shelve, math

import commands as cmd
import deck as dk
import helpers as hp
import labware as lw
import state as st

from pyhamilton import HamiltonInterface

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Liquid classes
ETHANOL_ASPIRATE = "StandardVolume_EtOH_DispenseJet_Empty"
ETHANOL_DISPENSE = "StandardVolume_EtOH_DispenseJet_Part"


def run(
    shelf: shelve.Shelf[list[dict[str, list]]],
    deck: dict,
    state: dict,
    run_dir_path: str,
):
    # File paths
    state_file_path = os.path.join(run_dir_path, "pm_emptying_state.json")
    csv_path = hp.prompt_file_path("Input CSV file (sorted_well_map.csv)")

    # Get plates and well map from csv files
    hp.process_pm_csv(csv_path, run_dir_path, "emptying")
    plate_map_path = os.path.join(run_dir_path, "emptying_plate_map.csv")
    well_map_path = os.path.join(run_dir_path, "emptying_sorted_well_map.csv")
    shutil.copy(csv_path, well_map_path)

    with open(plate_map_path, "r") as f:
        reader = csv.reader(f)
        plate_map = [tuple(row) for row in reader]

    plates = [t[1] for t in plate_map if t[1] != ""]

    with open(well_map_path, "r") as f:
        reader = csv.reader(f)
        well_map = [tuple(row) for row in reader]

    wells = [(t[2], t[3]) for t in well_map]

    # Delete unused labware
    for p in ["E1", "E2", "E3", "F1", "F2", "F3"]:
        dk.delete_lids(shelf, p)

    pos = [("E1", "F1"), ("E2", "F2"), ("E3", "F3")]
    remove = len(pos) * 6 - len(plates)
    for t in pos[::-1]:
        n = min(remove, 6)
        dk.delete_unused(shelf, t[0], n)
        dk.delete_unused(shelf, t[1], n)
        remove -= n

    # Labware aliases
    bact_plates = [l for i in range(len(pos)) for l in shelf["F"][i]["frame"]]
    bact_plates_done = [l for i in range(len(pos)) for l in shelf["E"][i]["frame"]]

    active_lid, active_plate = shelf["E"][4]["frame"]
    tmp_lid = shelf["E"][3]["frame"][0]

    # Static positions
    ethanol = shelf["C"][4]["frame"][0].static(["A24", "E24"])
    waste = shelf["C"][4]["frame"][0].static(["G12", "L12"])
    ethanol_tips = shelf["F"][4]["frame"][0].static(["A1", "C1"])
    waste_tips = shelf["F"][4]["frame"][0].static(["B1", "D1"])

    # Main Hamilton method starts here
    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton
        cmd.initialize(hammy)

        # Loop over plates as long as there are plates left to empty
        while plates:
            # Get next plate if not already done
            if not state["active_plate"]:
                cmd.grip_get(hammy, bact_plates[-1].plate, gripWidth=82.0)
                cmd.grip_place(hammy, active_plate.plate)
                cmd.grip_get(
                    hammy, active_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, tmp_lid.lid, mode=1)

                # Build well list for current plate
                active_plate.fill([t[0] for t in wells if t[1] == plates[-1]])

                del plates[-1]
                dk.delete_labware(shelf, bact_plates.pop().plate)
                st.reset_state(state, state_file_path, "active_plate", 1)

            # Remove media from wells
            if not state["remove_media"]:
                cmd.tip_pick_up(hammy, waste_tips)

                # Loop through wells
                while active_plate.total() > 0:
                    # Calculate cycles to perform depending on number of wells left
                    remaining = active_plate.total()
                    cycles = min(2, math.ceil(remaining / 2))

                    # Remove media
                    for _ in range(cycles):
                        channels = min(
                            2, active_plate.total()
                        )  # Channels to use for each cycle
                        cmd.aspirate(
                            hammy,
                            active_plate.ch2(channels),
                            [140.0],
                            mixCycles=3,
                            mixVolume=50.0,
                        )

                    # Calculate how much volume needs to be dispensed based on number of aspirations
                    dispense_volume = [
                        140.0 * math.ceil(min(4, remaining) / 2),
                        140.0 * math.floor(min(4, remaining) / 2),
                    ]

                    cmd.dispense(hammy, waste, dispense_volume, dispenseMode=9)

                cmd.tip_eject(hammy, waste_tips)

                active_plate.reset()
                st.reset_state(state, state_file_path, "remove_media", 1)

            # Add ethanol to emptied wells
            if not state["add_ethanol"]:
                cmd.tip_pick_up(hammy, ethanol_tips)

                # Loop through wells
                while active_plate.total() > 0:
                    # Calculate volume to aspirate depending on remaining wells
                    remaining = min(6, active_plate.total())
                    aspirate_volume = [
                        100.0 * math.ceil(remaining / 2),
                        100.0 * math.floor(remaining / 2),
                    ]
                    cmd.aspirate(
                        hammy, ethanol, aspirate_volume, liquidClass=ETHANOL_DISPENSE
                    )

                    # Calculate number of cycles (max 3) and dispense ethanol
                    cycles = min(3, math.ceil(remaining / 2))
                    for _ in range(cycles):
                        channels = min(
                            2, active_plate.total()
                        )  # Channels to use for each cycle
                        cmd.dispense(
                            hammy,
                            active_plate.ch2(channels),
                            [100.0],
                            liquidClass=ETHANOL_DISPENSE,
                        )

                cmd.tip_eject(hammy, ethanol_tips)

                active_plate.reset()
                st.reset_state(state, state_file_path, "add_ethanol", 1)

            # Remove ethanol from cleaned wells
            if not state["remove_ethanol"]:
                cmd.tip_pick_up(hammy, waste_tips)

                # Loop through wells
                while active_plate.total() > 0:
                    # Calculate cycles to perform depending on number of wells left
                    remaining = active_plate.total()
                    cycles = min(2, math.ceil(remaining / 2))

                    # Remove ethanol
                    for _ in range(cycles):
                        channels = min(
                            2, active_plate.total()
                        )  # Channels to use for each cycle
                        cmd.aspirate(
                            hammy,
                            active_plate.ch2(channels),
                            [140.0],
                            mixCycles=3,
                            mixVolume=50.0,
                        )

                    # Calculate how much volume needs to be dispensed based on number of aspirations
                    dispense_volume = [
                        140.0 * math.ceil(min(4, remaining) / 2),
                        140.0 * math.floor(min(4, remaining) / 2),
                    ]

                    cmd.dispense(hammy, waste, dispense_volume, dispenseMode=9)

                cmd.tip_eject(hammy, waste_tips)

                st.reset_state(state, state_file_path, "remove_ethanol", 1)

            # Remove completed plate if not already done
            if state["active_plate"]:
                cmd.grip_get(hammy, tmp_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0)
                cmd.grip_place(hammy, active_lid.lid, mode=1)
                cmd.grip_get(hammy, active_plate.plate, gripWidth=82.0)
                cmd.grip_place(hammy, bact_plates_done[0].plate)

                dk.delete_labware(shelf, bact_plates_done.pop(0).plate)
                st.reset_state(state, state_file_path, "active_plate", 0)

        cmd.grip_eject(hammy)

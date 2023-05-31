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
WATER = "Tip_50ul_Water_DispenseJet_Empty"


def run(
    shelf: shelve.Shelf[list[dict[str, list]]],
    state: dict,
    run_dir_path: str,
):
    # File paths
    state_file_path = os.path.join(run_dir_path, "pm_filling_state.json")
    csv_path = hp.prompt_file_path("Input CSV file (sorted_well_map.csv)")

    # Get plates and well map from csv files
    hp.process_pm_csv(csv_path, run_dir_path, "filling")
    plate_map_path = os.path.join(run_dir_path, "filling_plate_map.csv")
    well_map_path = os.path.join(run_dir_path, "filling_sorted_well_map.csv")
    shutil.copy(csv_path, well_map_path)

    with open(plate_map_path, "r") as f:
        reader = csv.reader(f)
        plate_map = [tuple(row) for row in reader]

    source_plates = [t[0] for t in plate_map if t[0] != ""]
    target_plates = [t[1] for t in plate_map if t[1] != ""]

    with open(well_map_path, "r") as f:
        reader = csv.reader(f)
        well_map = [tuple(row) for row in reader]

    source_wells = [(t[0], t[1]) for t in well_map]
    target_wells = [(t[2], t[3]) for t in well_map]

    # Delete unused labware
    for p in ["E1", "E2", "E3", "F1", "F2", "F3"]:
        dk.delete_lids(shelf, p)

    n = 6 - len(target_plates)
    dk.delete_unused(shelf, "E1", n)
    dk.delete_unused(shelf, "F1", n)

    tgt_pos = [("E2", "F2"), ("E3", "F3")]
    remove = len(tgt_pos) * 6 - len(target_plates)
    for t in tgt_pos[::-1]:
        n = min(remove, 6)
        dk.delete_unused(shelf, t[0], n)
        dk.delete_unused(shelf, t[1], n)
        remove -= n

    # Labware aliases
    src_plates = shelf["F"][0]["frame"]
    src_plates_done = shelf["E"][0]["frame"]

    tgt_plates = [l for i in range(len(tgt_pos)) for l in shelf["F"][i]["frame"]]
    tgt_plates_done = [l for i in range(len(tgt_pos)) for l in shelf["E"][i]["frame"]]

    active_src_lid, active_src_plate = shelf["E"][4]["frame"]
    active_tgt_lid, active_tgt_plate = shelf["E"][3]["frame"]

    tmp_src_lid = shelf["C"][1]["frame"][0]
    tmp_tgt_lid = shelf["C"][2]["frame"][0]

    racks_96_300 = [l for i in range(3) for l in shelf["B"][i]["frame"]]
    active_rack_96_300, transport_rack_96_300 = shelf["F"][4]["frame"]

    # Check if there are enough tips on deck to pick all wells
    if len(source_wells) > (len(racks_96_300) + 1) * 96:
        logger.warning(
            f"Number of tips needed ({len(source_wells)}) is larger than number of"
            f" tips available ({(len(racks_96_300) + 1) * 96})."
        )
        logger.info("Script will prompt user to add more tip racks when needed.")

    # Main script starts here
    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton
        cmd.initialize(hammy)

        # Loop over plates as long as there are still plates (source or target) to process
        while source_plates and target_plates:
            # Get next source plate if not already done
            if not state["active_src_plate"]:
                cmd.grip_get(hammy, src_plates[-1].plate, gripWidth=82.0)
                cmd.grip_place(hammy, active_src_plate.plate)
                cmd.grip_get(
                    hammy, active_src_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, tmp_src_lid, mode=1)

                # Build list source wells for current plate
                active_src_plate.fill(
                    [t[0] for t in source_wells if t[1] == source_plates[-1]]
                )

                del source_plates[-1]
                del src_plates[-1]
                st.reset_state(state, state_file_path, "active_src_plate", 1)

            # Get next target plate if not already done
            if not state["active_tgt_plate"]:
                cmd.grip_get(hammy, tgt_plates[-1].plate, gripWidth=82.0)
                cmd.grip_place(hammy, active_tgt_plate.plate)
                cmd.grip_get(
                    hammy, active_tgt_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, tmp_tgt_lid.lid, mode=1)

                # Build list of target wells for current plates
                active_tgt_plate.fill(
                    [t[0] for t in target_wells if t[1] == target_plates[-1]]
                )

                del target_plates[-1]
                dk.delete_labware(shelf, tgt_plates.pop().plate)
                st.reset_state(state, state_file_path, "active_tgt_plate", 1)

            # Check if there are still wells to process in the current source plate
            # Swich to next source plate if current one is empty
            if active_src_plate.total() == 0:
                cmd.grip_get(
                    hammy, tmp_src_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, active_src_lid.lid, mode=1)
                cmd.grip_get(
                    hammy, active_src_plate.plate, gripWidth=82.0, gripHeight=9.0
                )
                cmd.grip_place(hammy, src_plates_done[0].plate)

                del src_plates_done[0]
                st.reset_state(state, state_file_path, "active_source_plate", 0)
                break

            # Check if there are still wells available in the current target plate
            # Swich to next target plate if current one is full
            if active_tgt_plate.total() == 0:
                cmd.grip_get(
                    hammy, tmp_tgt_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, active_tgt_lid.lid, mode=1)
                cmd.grip_get(
                    hammy, active_tgt_plate.plate, gripWidth=82.0, gripHeight=9.0
                )
                cmd.grip_place(hammy, tgt_plates_done[0].plate)

                dk.delete_labware(shelf, tgt_plates_done.pop(0).plate)
                st.reset_state(state, state_file_path, "active_target_plate", 0)
                break

            # Check if there are still tips in the active rack
            # Discard rack and get new one from stacked racks if current one is done
            if active_rack_96_300.total() == 0:
                cmd.grip_get_tip_rack(hammy, active_rack_96_300.rack)
                cmd.grip_place_tip_rack(hammy, active_rack_96_300.rack, waste=True)
                cmd.grip_get_tip_rack(hammy, racks_96_300[-1].rack)
                cmd.grip_place_tip_rack(hammy, transport_rack_96_300.rack)

                dk.delete_labware(shelf, racks_96_300.pop().rack)
                active_rack_96_300.reset()

            # Check how many channels to use in the next cycle using minimum of
            # source wells left, target wells left, tips left, and channels available
            channels = min(
                active_src_plate.total(),
                active_tgt_plate.total(),
                active_rack_96_300.total(),
                2,
            )

            # Transfer culture media from source wells to target wells
            cmd.tip_pick_up(hammy, active_rack_96_300.ch2(channels))
            cmd.aspirate(
                hammy,
                active_src_plate.ch2(channels),
                [100.0],
                mixCycles=3,
                mixVolume=50.0,
                liquidClass=WATER,
            )
            cmd.dispense(
                hammy,
                active_tgt_plate.ch2(channels),
                [100.0],
                dispenseMode=9,
                liquidClass=WATER,
            )
            cmd.tip_eject(hammy, waste=True)

        cmd.grip_eject(hammy)

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
    state_file_path = os.path.join(run_dir_path, "cherry_picking.json")
    csv_path = hp.prompt_file_path("Input CSV file (cherry.csv)")

    # Get plates and well map from csv files
    l, source_plates = hp.process_cherry_csv(csv_path, run_dir_path)

    well_map = [(t[2], t[5], t[1]) for t in l]

    # Delete unused labware
    for p in ["E1", "E2", "E3", "F1", "F2", "F3"]:
        dk.delete_lids(shelf, p)

    src_pos = [("E1", "F1"), ("E2", "F2")]
    remove = len(src_pos) * 6 - len(source_plates)
    for t in src_pos[::-1]:
        n = min(remove, 6)
        dk.delete_unused(shelf, t[0], n)
        dk.delete_unused(shelf, t[1], n)
        remove -= n

    n = 6 - math.ceil(len(well_map) / 384)
    dk.delete_unused(shelf, "E3", n)
    dk.delete_unused(shelf, "F3", n)

    # Labware aliases
    src_plates = [l for i in range(len(src_pos)) for l in shelf["F"][i]["frame"]]
    src_plates_done = [l for i in range(len(src_pos)) for l in shelf["E"][i]["frame"]]

    tgt_plates = shelf["E"][2]["frame"]
    tgt_plates_done = shelf["F"][2]["frame"]

    active_src_lid, active_src_plate = shelf["E"][4]["frame"]
    active_tgt_lid, active_tgt_plate = shelf["E"][3]["frame"]

    tmp_src_lid = shelf["C"][1]["frame"][0]
    tmp_tgt_lid = shelf["C"][2]["frame"][0]

    racks_96_50 = [l for i in range(3) for l in shelf["B"][i]["frame"]]
    active_rack_96_50, transport_rack_96_50 = shelf["F"][4]["frame"]

    # Check if there are enough tips on deck to pick all wells
    if len(well_map) > (len(racks_96_50) + 1) * 96:
        logger.warning(
            f"Number of tips needed ({len(well_map)}) is larger than number of"
            f" tips available ({(len(racks_96_50) + 1) * 96})."
        )
        logger.info("Script will prompt user to add more tip racks when needed.")

    # Main script starts here
    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton
        cmd.initialize(hammy)

        # Loop over plates as long as there are still source plates to process
        while source_plates:
            # Get next source plate if not already done
            if not state["active_src_plate"]:
                cmd.grip_get(hammy, src_plates[-1].plate, gripWidth=82.0)
                cmd.grip_place(hammy, active_src_plate.plate)
                cmd.grip_get(
                    hammy, active_src_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, tmp_src_lid.lid, mode=1)

                current_map = [t for t in well_map if t[2] == source_plates[-1]]

                dk.delete_labware(shelf, src_plates.pop().plate)
                st.set_state(state, state_file_path, "active_src_plate", 1)

            # Get next target plate if not already done
            if not state["active_tgt_plate"]:
                cmd.grip_get(hammy, tgt_plates[-1].plate, gripWidth=82.0)
                cmd.grip_place(hammy, active_tgt_plate.plate)
                cmd.grip_get(
                    hammy, active_tgt_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, tmp_tgt_lid.lid, mode=1)

                dk.delete_labware(shelf, tgt_plates.pop().plate)
                st.set_state(state, state_file_path, "active_tgt_plate", 1)

            # Check if there are still wells to process in the current source plate
            # Swich to next source plate if current one is empty
            if len(current_map) == 0:
                cmd.grip_get(
                    hammy, tmp_src_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, active_src_lid.lid, mode=1)
                cmd.grip_get(
                    hammy, active_src_plate.plate, gripWidth=82.0, gripHeight=9.0
                )
                cmd.grip_place(hammy, src_plates_done[0].plate)

                del source_plates[-1]

                dk.delete_labware(shelf, src_plates_done.pop(0).plate)
                st.set_state(state, state_file_path, "active_src_plate", 0)
                continue

            # Check if there are still tips in the active rack
            # Discard rack and get new one from stacked racks if current one is done
            if active_rack_96_50.total() == 0:
                cmd.grip_get_tip_rack(hammy, active_rack_96_50.rack)
                cmd.grip_place_tip_rack(hammy, active_rack_96_50.rack, waste=True)
                cmd.grip_get_tip_rack(hammy, racks_96_50[-1].rack)
                cmd.grip_place_tip_rack(hammy, transport_rack_96_50.rack)

                dk.delete_labware(shelf, racks_96_50.pop().rack)
                active_rack_96_50.reset()

            # Transfer culture media from source well to target well
            cmd.tip_pick_up(hammy, active_rack_96_50.ch2(1))
            cmd.aspirate(
                hammy,
                active_src_plate.static([current_map[0][0]]),
                [5],
                liquidHeight=0.5,
                mixCycles=3,
                mixVolume=20.0,
                liquidClass=WATER,
            )
            cmd.dispense(
                hammy,
                active_tgt_plate.static([current_map.pop(0)[1]]),
                [5],
                liquidHeight=0.5,
                dispenseMode=9,
                liquidClass=WATER,
            )
            cmd.tip_eject(hammy, waste=True)

        # Move target plate to done stack

        cmd.grip_get(hammy, tmp_tgt_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0)
        cmd.grip_place(hammy, active_tgt_lid.lid, mode=1)
        cmd.grip_get(hammy, active_tgt_plate.plate, gripWidth=82.0, gripHeight=9.0)
        cmd.grip_place(hammy, tgt_plates_done[0].plate)

        dk.delete_labware(shelf, tgt_plates_done.pop(0).plate)
        cmd.grip_eject(hammy)

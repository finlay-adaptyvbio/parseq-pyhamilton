import os, logging, shelve

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
MIXING = "50ulTip_conductive_384COREHead_Water_DispenseSurface_Empty"


def run(
    shelf: shelve.Shelf[list[dict[str, list]]],
    state: dict,
    run_dir_path: str,
):
    # File paths
    state_file_path = os.path.join(run_dir_path, "pcr_barcode.json")

    # Plate information and variables
    plates = hp.prompt_int("Plates to process", 4)

    # Delete unused labware
    n = 4 - plates
    for p in ["E1", "F1"]:
        dk.delete_lids(shelf, p)
        dk.delete_unused(shelf, p, n)

    # Labware aliases
    pcr_plates = shelf["F"][0]["frame"]
    pcr_plates_done = shelf["E"][0]["frame"]

    active_lid, active_plate = shelf["C"][0]["frame"]
    tmp_lid = shelf["C"][1]["frame"][0]

    barcodes = shelf["D"][0]["frame"][0].full()

    racks_384_50 = shelf["B"][0]["frame"]
    active_rack_384_50, transport_rack_384_50 = shelf["D"][1]["frame"]

    # Main script starts here
    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton
        cmd.initialize(hammy)

        # Loop over plates as long as there are still bact plates to process
        while pcr_plates:
            # Get next PCR plate if not already done
            if not state["active_plate"]:
                cmd.grip_get(
                    hammy, pcr_plates[-1].plate, gripWidth=81.0, gripHeight=4.0
                )
                cmd.grip_place(hammy, active_plate.plate)
                cmd.grip_get(
                    hammy, active_lid.lid, mode=1, gripWidth=85.0, gripHeight=0.5
                )
                cmd.grip_place(hammy, tmp_lid.lid, mode=1)

                del pcr_plates[-1]
                st.set_state(state, state_file_path, "active_plate", 1)
                st.set_state(state, state_file_path, "add_oligos", 0)

            # Check if there is an active rack, get a new rack if needed
            if not state["active_rack"]:
                cmd.grip_get_tip_rack(hammy, racks_384_50[-1].rack)
                cmd.grip_place_tip_rack(hammy, transport_rack_384_50.rack)

                del racks_384_50[-1]
                st.set_state(state, state_file_path, "active_rack", 1)

            # Add oligos from barcoding plate to active pcr plate
            if not state["add_oligos"]:
                cmd.tip_pick_up_384(hammy, active_rack_384_50.full())
                cmd.aspirate_384(
                    hammy,
                    barcodes,
                    1.0,
                    liquidHeight=3.0,
                    mixCycles=3,
                    mixVolume=5.0,
                    liquidClass=MIXING,
                )
                cmd.dispense_384(
                    hammy,
                    active_plate.full(),
                    1.0,
                    mixCycles=3,
                    mixVolume=5.0,
                    liquidClass=MIXING,
                )
                cmd.tip_eject_384(hammy, mode=2)

                st.set_state(state, state_file_path, "add_oligos", 1)

            # Discard current active rack to waste if not already done
            if state["active_rack"]:
                cmd.grip_get_tip_rack(hammy, active_rack_384_50.rack)
                cmd.grip_place_tip_rack(hammy, active_rack_384_50.rack, waste=True)

                st.set_state(state, state_file_path, "active_rack", 0)

            # Remove active PCR plate and place in destination stack
            if state["active_plate"]:
                cmd.grip_get(
                    hammy,
                    tmp_lid.lid,
                    mode=1,
                    gripWidth=85.0,
                    gripHeight=1.0,
                )
                cmd.grip_place(hammy, active_lid.lid, mode=1)
                cmd.grip_get(hammy, active_plate.plate, gripWidth=81.0, gripHeight=6.0)
                cmd.grip_place(hammy, pcr_plates_done[0].plate)

                del pcr_plates_done[0]
                st.set_state(state, state_file_path, "active_plate", 0)

        cmd.grip_eject(hammy)

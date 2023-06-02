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
    state_file_path = os.path.join(run_dir_path, "pcr_colony.json")

    # Plate information and variables
    plates = hp.prompt_int("Plates to process", 4)

    # Delete unused labware
    n = 4 - plates
    for p in ["E1", "E2", "F1", "F2"]:
        dk.delete_lids(shelf, p)
        dk.delete_unused(shelf, p, n)

    # Labware aliases
    bact_plates = shelf["F"][0]["frame"]
    bact_plates_done = shelf["E"][0]["frame"]
    pcr_plates = shelf["F"][1]["frame"]
    pcr_plates_done = shelf["E"][1]["frame"]
    pcr_lids = shelf["F"][2]["frame"]

    active_bact_lid, active_bact_plate = shelf["E"][4]["frame"]
    tmp_bact_lid = shelf["E"][3]["frame"][0]

    active_pcr_lid, active_pcr_plate = shelf["C"][3]["frame"]

    master_mix = shelf["C"][4]["frame"][0].full()
    master_mix_tips = shelf["B"][4]["frame"][0].full()

    racks_384_50 = shelf["B"][0]["frame"]
    active_rack_384_50, transport_rack_384_50 = shelf["D"][1]["frame"]

    # Main script starts here
    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton
        cmd.initialize(hammy)

        # Loop over plates as long as there are still plates to process
        while pcr_plates and bact_plates:
            # Get next bact plate if not already done
            if not state["active_bact_plate"]:
                cmd.grip_get(hammy, bact_plates[-1].plate, gripWidth=82.0)
                cmd.grip_place(hammy, active_bact_plate.plate)
                cmd.grip_get(
                    hammy, active_bact_lid.lid, mode=1, gripWidth=85.0, gripHeight=5.0
                )
                cmd.grip_place(hammy, tmp_bact_lid.lid, mode=1)

                dk.delete_labware(shelf, bact_plates.pop().plate)

                st.set_state(state, state_file_path, "active_bact_plate", 1)
                st.set_state(state, state_file_path, "add_bact", 0)

            # Get next pcr plates if not already done
            if not state["active_pcr_plate"]:
                cmd.grip_get(
                    hammy, pcr_plates[-1].plate, gripWidth=82.0, gripHeight=4.0
                )
                cmd.grip_place(hammy, active_pcr_plate.plate)

                dk.delete_labware(shelf, pcr_plates.pop().plate)

                st.set_state(state, state_file_path, "active_pcr_plate", 1)
                st.set_state(state, state_file_path, "add_mm", 0)

            # Add master mix to pcr plate if not already done
            if not state["add_mm"]:
                cmd.tip_pick_up_384(hammy, master_mix_tips)
                cmd.aspirate_384(hammy, master_mix, 18.5, liquidHeight=2.0)
                cmd.dispense_384(
                    hammy,
                    active_pcr_plate.full(),
                    18.5,
                    liquidHeight=8.0,
                    dispenseMode=9,
                )
                cmd.tip_eject_384(hammy, mode=1)

                st.set_state(state, state_file_path, "add_mm", 1)

            # Get new tip rack if no current active tip rack
            if not state["active_rack"]:
                cmd.grip_get_tip_rack(hammy, racks_384_50[-1].rack)
                cmd.grip_place_tip_rack(hammy, transport_rack_384_50.rack)

                dk.delete_labware(shelf, racks_384_50.pop().rack)
                st.set_state(state, state_file_path, "active_rack", 1)

            # Aspirate from active bact plate to active pcr plate
            if not state["add_bact"]:
                cmd.tip_pick_up_384(hammy, active_rack_384_50.full())
                cmd.aspirate_384(
                    hammy,
                    active_bact_plate.full(),
                    1.0,
                    liquidHeight=3.0,
                    mixCycles=3,
                    mixVolume=5.0,
                    liquidClass=MIXING,
                )
                cmd.dispense_384(
                    hammy,
                    active_pcr_plate.full(),
                    1.0,
                    mixCycles=3,
                    mixVolume=5.0,
                    liquidClass=MIXING,
                )
                cmd.tip_eject_384(hammy, mode=2)

                st.set_state(state, state_file_path, "add_bact", 1)

            # Place current active bact plate in dest bact plate stack if not already done
            if state["active_bact_plate"]:
                cmd.grip_get(
                    hammy, tmp_bact_lid.lid, mode=1, gripWidth=85.0, gripHeight=5.0
                )
                cmd.grip_place(hammy, active_bact_lid.lid, mode=1)
                cmd.grip_get(hammy, active_bact_plate.plate, gripWidth=82.0)
                cmd.grip_place(hammy, bact_plates_done[0].plate)

                dk.delete_labware(shelf, bact_plates_done.pop(0).plate)
                st.set_state(state, state_file_path, "active_bact_plate", 0)

            # Place current active pcr plate in dest pcr plate stack if not already done
            # Also get a new lid from stack
            if state["active_pcr_plate"]:
                cmd.grip_get(
                    hammy, pcr_lids[-1].lid, mode=1, gripWidth=85.0, gripHeight=1.5
                )
                cmd.grip_place(hammy, active_pcr_lid.lid, mode=1)
                cmd.grip_get(
                    hammy, active_pcr_plate.plate, gripWidth=81.0, gripHeight=6.0
                )
                cmd.grip_place(hammy, pcr_plates_done[0].plate)

                dk.delete_labware(shelf, pcr_plates_done.pop(0).plate)
                st.set_state(state, state_file_path, "active_pcr_plate", 1)

            # Discard current active rack to waste if not already done
            if state["active_rack"]:
                logger.debug("Discarding tip rack...")
                cmd.grip_get_tip_rack(hammy, active_rack_384_50.rack)
                cmd.grip_place_tip_rack(hammy, active_rack_384_50.rack, waste=True)

                st.set_state(state, state_file_path, "active_rack", 0)

        cmd.grip_eject(hammy)

import logging

import commands as cmd
import deck as dk
import state as st
import helpers as hp

from pyhamilton import (
    HamiltonInterface,
    Plate384,
    Lid,  # type: ignore
    Tip384,  # type: ignore
)

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Constants

RACKS = 9
TIPS_96 = 96
TIPS_384 = 384

CHANNELS_384 = "1" * 384
CHANNELS_384_96 = (("10" * 12) + ("0" * 24)) * 8

MIXING = "50ulTip_conductive_384COREHead_Water_DispenseSurface_Empty"


def run(shelf: shelve.Shelf, state: dict, state_file_path: str, run_dir_path: str):
    # Plate information and variables

    logger.debug("Getting number of plates from prompt...")

    plates = hp.prompt_int("Plates to process", 4)

    pcr_plates = [f"P{i}" for i in range(1, plates + 1)]

    logger.debug(f"Plates to pool: {pcr_plates}")

    # Assign labware to deck positions

    logger.info("Assigning labware...")

    source_pcr_plates = dk.get_labware_list(
        deck,
        ["E1"],
        Plate384,
        [4],
        True,
    )[0 : len(pcr_plates)]

    dest_pcr_plates = dk.get_labware_list(
        deck,
        ["E2"],
        Plate384,
        [4],
        False,
    )[0 : len(pcr_plates)]

    barcode_plate = dk.get_labware_list(deck, ["D1"], Plate384)[0]
    barcode_wells = [(barcode_plate, i) for i in range(384)]

    active_pcr_plate = dk.get_labware_list(deck, ["C1"], Plate384)[0]
    active_pcr_lid = dk.get_labware_list(deck, ["C1"], Lid)[0]
    temp_pcr_lid = dk.get_labware_list(deck, ["C2"], Lid)[0]

    racks = dk.get_labware_list(deck, ["B1", "B2", "B3"], Tip384, [3, 3, 3], True)
    rack_tips, rack_virtual = dk.get_labware_list(deck, ["D2"], Tip384, [2])
    tips = [(rack_tips, i) for i in range(384)]

    # Inform user of labware positions, ask for confirmation after placing plates

    logger.debug("Prompt user for plate placement...")

    hp.place_plates(pcr_plates, source_pcr_plates, "pcr", state["current_pcr_plate"])

    logger.info("Starting Hamilton method...")

    # Main script starts here
    # TODO: reduce loops to functions to make it more readable

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton

        cmd.initialize(hammy)

        # Loop over plates as long as there are still bact plates to process

        logger.debug(f"Current pcr plate: {state['current_pcr_plate']}")
        logger.debug(f"No. of pcr plates: {len(source_pcr_plates)}")

        while state["current_pcr_plate"] < len(source_pcr_plates):
            # Get PCR plate from source rack and place it in the active position if not already done

            if not state["active_pcr_plate"]:
                logger.debug("Getting next PCR plate...")
                cmd.grip_get(
                    hammy,
                    source_pcr_plates[state["current_pcr_plate"]],
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=4.0,
                )
                cmd.grip_place(hammy, active_pcr_plate, mode=0)

                cmd.grip_get(
                    hammy,
                    active_pcr_lid,
                    mode=1,
                    gripWidth=85.0,
                    gripHeight=0.5,
                )
                cmd.grip_place(hammy, temp_pcr_lid, mode=1)

                st.reset_state(state, state_file_path, "active_pcr_plate", 1)
                st.reset_state(state, state_file_path, "add_oligos", 0)

            if not state["active_rack"]:
                logger.debug("Getting next tip rack...")
                cmd.grip_get_tip_rack(hammy, racks[state["current_rack"]])
                cmd.grip_place_tip_rack(hammy, rack_virtual)

                st.reset_state(state, state_file_path, "active_rack", 1)

            # Aspirate from oligo plate to active pcr plate

            if not state["add_oligos"]:
                logger.info("Adding oligos to PCR plate...")
                pcr_wells = [(active_pcr_plate, i) for i in range(384)]

                cmd.tip_pick_up_384(hammy, tips)
                cmd.aspirate_384(
                    hammy,
                    barcode_wells,
                    1.0,
                    liquidHeight=3.0,
                    mixCycles=3,
                    mixVolume=5.0,
                    liquidClass=MIXING,
                )
                cmd.dispense_384(
                    hammy,
                    pcr_wells,
                    1.0,
                    mixCycles=3,
                    mixVolume=5.0,
                    liquidClass=MIXING,
                )
                cmd.tip_eject_384(hammy, tips, 2)

                st.reset_state(state, state_file_path, "add_oligos", 1)

            # Discard current active rack to waste if not already done

            if state["active_rack"]:
                logger.debug("Discarding tip rack...")
                cmd.grip_get_tip_rack(hammy, rack_tips)
                cmd.grip_place_tip_rack(hammy, rack_tips, waste=True)

                st.update_state(state, state_file_path, "current_rack", 1)
                st.reset_state(state, state_file_path, "active_rack", 0)

            # if all currently active pcr plates are processed, place them in the dest pcr plate stack

            if state["active_pcr_plate"]:
                logger.debug("Placing PCR plate in destination stack...")
                cmd.grip_get(
                    hammy,
                    temp_pcr_lid,
                    mode=1,
                    gripWidth=85.0,
                    gripHeight=1.0,
                )
                cmd.grip_place(hammy, active_pcr_lid, mode=1)

                cmd.grip_get(
                    hammy,
                    active_pcr_plate,
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=6.0,
                )
                cmd.grip_place(
                    hammy,
                    dest_pcr_plates[state["current_pcr_plate"]],
                    mode=0,
                )

                st.update_state(state, state_file_path, "current_pcr_plate", 1)
                st.reset_state(state, state_file_path, "active_pcr_plate", 0)

            st.print_state(state)

        cmd.grip_eject(hammy)

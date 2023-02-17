import logging

import commands as cmd
import deck as dk
import state as st
import helpers as hp

from pyhamilton import (
    HamiltonInterface,
    Lid,  # type: ignore
    Plate384,
    Tip384,  # type: ignore
    Reservoir300,  # type: ignore
)

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def run(deck: dict, state: dict, state_file_path: str, run_dir_path: str):
    # Plate information and variables

    logger.debug("Getting number of plates from prompt...")

    plates = hp.prompt_int("Plates to fill", 16)

    logger.debug("Getting volume to add from prompt...")

    volume = hp.prompt_int("Volume to add", 100)

    if volume > 50:
        loops = 2
    else:
        loops = 1

    volume = volume / loops

    bact_plates = [f"P{i}" for i in range(1, plates + 1)]

    logger.debug(f"Plates to fill: {bact_plates}")
    logger.debug(f"Volume to add: {volume}")

    # Assign labware to deck positions

    logger.info("Assigning labware...")

    source_bact_plates = dk.get_labware_list(
        deck,
        ["E1"],
        Plate384,
        [8],
        True,
    )[-len(bact_plates) :]

    dest_bact_plates = dk.get_labware_list(
        deck,
        ["E2"],
        Plate384,
        [8],
        False,
    )[0 : len(bact_plates)]

    media_reservoir = dk.get_labware_list(deck, ["C5"], Reservoir300)[0]
    media = [(media_reservoir, i) for i in range(384)]

    media_rack = dk.get_labware_list(deck, ["B5"], Tip384)[0]
    media_tips = [(media_rack, i) for i in range(384)]

    active_bact_plate = dk.get_labware_list(deck, ["C4"], Plate384)[0]
    active_bact_wells = [(active_bact_plate, i) for i in range(384)]
    active_bact_lid = dk.get_labware_list(deck, ["C4"], Lid)[0]
    temp_bact_lid = dk.get_labware_list(deck, ["C2"], Lid)[0]

    # Inform user of labware positions, ask for confirmation after placing plates

    logger.debug("Prompt user for plate placement...")

    hp.place_plates(
        bact_plates, source_bact_plates, "bact", state["current_bact_plate"]
    )

    logger.info("Starting Hamilton method...")

    # Main script starts here
    # TODO: reduce loops to functions to make it more readable

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton

        cmd.initialize(hammy)

        # Load tips into column holder

        logger.debug("Loading tips into column holder...")

        cmd.tip_pick_up_384(hammy, media_tips, tipMode=1)

        # Loop over plates as long as there are still pcr plates to process

        logger.debug(f"Current bact plate: {state['current_bact_plate']}")
        logger.debug(f"No. of bact plates: {len(source_bact_plates)}")

        while state["current_bact_plate"] < len(source_bact_plates):
            # Get next pcr plate from source stack if not already done

            if not state["active_bact_plate"]:
                logger.debug("Getting next bact plate from source stack...")
                cmd.grip_get(
                    hammy,
                    source_bact_plates[state["current_bact_plate"]],
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=4.0,
                )
                cmd.grip_place(hammy, active_bact_plate, mode=0)
                cmd.grip_get(
                    hammy, active_bact_lid, mode=1, gripWidth=85.0, gripHeight=0.5
                )
                cmd.grip_place(hammy, temp_bact_lid, mode=1)

                st.reset_state(state, state_file_path, "active_bact_plate", 1)
                st.reset_state(state, state_file_path, "media", 0)

            # Add media to bact plate if not already done

            if not state["media"]:
                logger.info("Adding media to bact plate...")

                for _ in range(loops):
                    cmd.aspirate_384(hammy, media, volume, liquidHeight=2.0)
                    cmd.dispense_384(
                        hammy,
                        active_bact_wells,
                        volume,
                        liquidHeight=11.0,
                        dispenseMode=9,
                    )

                st.reset_state(state, state_file_path, "media", 1)

            if state["active_bact_plate"]:
                logger.debug("Moving active bact plate to destination stack...")
                cmd.grip_get(
                    hammy,
                    temp_bact_lid,
                    mode=1,
                    gripWidth=85.0,
                    gripHeight=0.5,
                )
                cmd.grip_place(hammy, active_bact_lid, mode=1)
                cmd.grip_get(
                    hammy,
                    active_bact_plate,
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=6.0,
                )
                cmd.grip_place(
                    hammy,
                    dest_bact_plates[state["current_bact_plate"]],
                    mode=0,
                )

                st.update_state(state, state_file_path, "current_bact_plate", 1)
                st.reset_state(state, state_file_path, "active_bact_plate", 0)

            st.print_state(state)

        cmd.tip_eject_384(hammy, media_tips, 2)
        cmd.grip_eject(hammy)

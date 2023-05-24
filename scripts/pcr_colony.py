import logging

import commands as cmd
import deck as dk
import state as st
import helpers as hp

from pyhamilton import (
    HamiltonInterface,
    Reservoir300,
    Plate96,
    Plate384,
    Lid,  # type: ignore
    Tip96,
    Tip384,  # type: ignore
)

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Constants

RACKS = 12
TIPS_96 = 96
TIPS_384 = 384

CHANNELS_384 = "1" * 384
CHANNELS_384_96 = (("10" * 12) + ("0" * 24)) * 8

MIXING = "50ulTip_conductive_384COREHead_Water_DispenseSurface_Empty"


def run(shelf: shelve.Shelf, state: dict, state_file_path: str, run_dir_path: str):
    # Plate information and variables

    logger.debug("Getting number of plates from prompt...")

    plates = hp.prompt_int("Plates to process", 4)

    bact_plates = [f"P{i}" for i in range(1, plates + 1)]

    logger.debug(f"Plates to pool: {bact_plates}")

    # Assign labware to deck positions

    logger.info("Assigning labware...")

    source_bact_plates = dk.get_labware_list(
        deck,
        ["F1"],
        Plate384,
        [4],
        True,
    )[0 : len(bact_plates)]

    dest_bact_plates = dk.get_labware_list(
        deck,
        ["F2"],
        Plate384,
        [4],
        False,
    )[0 : len(bact_plates)]

    source_pcr_plates = dk.get_labware_list(
        deck,
        ["E3"],
        Plate384,
        [4],
        True,
    )[0 : len(bact_plates)]

    source_pcr_lids = dk.get_labware_list(
        deck,
        ["E2"],
        Lid,
        [4],
        True,
    )[0 : len(bact_plates)]

    dest_pcr_plates = dk.get_labware_list(
        deck,
        ["E1"],
        Plate384,
        [4],
        False,
    )[0 : len(bact_plates)]

    active_bact_plate = dk.get_labware_list(deck, ["E5"], Plate384)[0]
    active_bact_lid = dk.get_labware_list(deck, ["E5"], Lid)[0]
    temp_bact_lid = dk.get_labware_list(deck, ["E4"], Lid)[0]

    source_wells = [(active_bact_plate, i) for i in range(384)]

    active_pcr_plates = dk.get_labware_list(
        deck, ["C1", "C2", "C3", "C4"], Plate384, [1, 1, 1, 1]
    )
    active_pcr_lids = dk.get_labware_list(
        deck, ["C1", "C2", "C3", "C4"], Lid, [1, 1, 1, 1]
    )

    master_mix_reservoir = dk.get_labware_list(deck, ["C5"], Reservoir300)[0]
    master_mix = [(master_mix_reservoir, i) for i in range(384)]
    master_mix_rack = dk.get_labware_list(deck, ["B5"], Tip384)[0]
    master_mix_tips = [(master_mix_rack, i) for i in range(384)]

    racks = dk.get_labware_list(deck, ["B1", "B2"], Tip384, [2, 2], True)
    rack_tips, rack_virtual = dk.get_labware_list(deck, ["D2"], Tip384, [2])
    tips = [(rack_tips, i) for i in range(384)]

    # Inform user of labware positions, ask for confirmation after placing plates

    logger.debug("Prompt user for plate placement...")

    hp.place_plates(
        bact_plates, source_bact_plates, "bact", state["current_bact_plate"]
    )
    hp.place_plates(bact_plates, source_pcr_plates, "pcr", state["current_pcr_plate"])

    logger.info("Starting Hamilton method...")

    # Main script starts here
    # TODO: reduce loops to functions to make it more readable
    # TODO: Check if total number of tips available is enough for the protocol, add prompt when new tip racks are needed

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton

        cmd.initialize(hammy)

        # Loop over plates as long as there are still bact plates to process
        # TODO: check if the last plate is processed correctly

        logger.debug(f"Current pcr plate: {state['current_pcr_plate']}")
        logger.debug(f"No. of pcr plates: {len(source_pcr_plates)}")

        while state["current_bact_plate"] < len(source_bact_plates):
            # Get bact plate from source rack if not already in active position

            if not state["active_bact_plate"]:
                logger.info("Getting bact plate from source rack...")
                cmd.grip_get(
                    hammy,
                    source_bact_plates[state["current_bact_plate"]],
                    mode=0,
                    gripWidth=82.0,
                    gripHeight=9.0,
                )
                cmd.grip_place(hammy, active_bact_plate, mode=0)
                cmd.grip_get(
                    hammy, active_bact_lid, mode=1, gripWidth=85.0, gripHeight=5.0
                )
                cmd.grip_place(hammy, temp_bact_lid, mode=1)

                st.reset_state(state, state_file_path, "active_bact_plate", 1)
                st.reset_state(state, state_file_path, "add_bact", 0)

            # Get next pcr plates from source rack if not already in active position

            if state["current_active_pcr_plates"] == 0:
                logger.debug("Getting pcr plates from source rack...")
                # Check how mnay plates to move into active position
                # Gets the minimum of 4 (max positions) or the number of plates left to process

                pcr_plates_to_process = min(
                    4, len(source_pcr_plates[state["current_pcr_plate"] :])
                )
                logger.debug(f"Plates to process: {pcr_plates_to_process}")
                for i in range(pcr_plates_to_process):
                    cmd.grip_get(
                        hammy,
                        source_pcr_plates[state["current_pcr_plate"] + i],
                        mode=0,
                        gripWidth=82.0,
                        gripHeight=4.0,
                    )
                    cmd.grip_place(hammy, active_pcr_plates[i], mode=0)

                    st.update_state(
                        state, state_file_path, "current_active_pcr_plates", 1
                    )

            # Add master mix to pcr plates if not already done

            if not state["add_mm"]:
                logger.info("Adding master mix to pcr plates...")
                # Check how mnay plates to move into active position
                # Gets the minimum of 4 (max positions) or the number of plates left to process

                pcr_plates_to_process = min(
                    4, len(source_pcr_plates[state["current_pcr_plate"] :])
                )
                logger.debug(f"Plates to process: {pcr_plates_to_process}")
                cmd.tip_pick_up_384(hammy, master_mix_tips, tipMode=0)

                for i in range(pcr_plates_to_process):
                    pcr_wells = [(active_pcr_plates[i], j) for j in range(384)]

                    cmd.aspirate_384(hammy, master_mix, 18.5, liquidHeight=2.0)
                    cmd.dispense_384(
                        hammy, pcr_wells, 18.5, liquidHeight=8.0, dispenseMode=9
                    )

                cmd.tip_eject_384(hammy, master_mix_tips, 1)

                st.reset_state(state, state_file_path, "add_mm", 1)

            # Get new tip rack if no current active tip rack

            if not state["active_rack"]:
                logger.debug("Getting new tip rack...")
                cmd.grip_get_tip_rack(hammy, racks[state["current_rack"]])
                cmd.grip_place_tip_rack(hammy, rack_virtual)

                st.reset_state(state, state_file_path, "active_rack", 1)

            # Aspirate from active bact plate to current active pcr plate

            if not state["add_bact"]:
                logger.info("Adding bacteria to pcr plates...")
                target_wells = [
                    (active_pcr_plates[state["current_active_pcr_plate"]], i)
                    for i in range(384)
                ]

                cmd.tip_pick_up_384(hammy, tips)
                cmd.aspirate_384(
                    hammy,
                    source_wells,
                    1.0,
                    liquidHeight=3.0,
                    mixCycles=3,
                    mixVolume=5.0,
                    liquidClass=MIXING,
                )
                cmd.dispense_384(
                    hammy,
                    target_wells,
                    1.0,
                    mixCycles=3,
                    mixVolume=5.0,
                    liquidClass=MIXING,
                )
                cmd.tip_eject_384(hammy, tips, 2)

                st.update_state(state, state_file_path, "current_active_pcr_plate", 1)
                st.reset_state(state, state_file_path, "add_bact", 1)

            # Place current active bact plate in dest bact plate stack if not already done

            if state["active_bact_plate"]:
                logger.debug("Placing bact plate in dest rack...")
                cmd.grip_get(
                    hammy, temp_bact_lid, mode=1, gripWidth=85.0, gripHeight=5.0
                )
                cmd.grip_place(hammy, active_bact_lid, mode=1)
                cmd.grip_get(
                    hammy, active_bact_plate, mode=0, gripWidth=82.0, gripHeight=9.0
                )
                cmd.grip_place(
                    hammy, dest_bact_plates[state["current_bact_plate"]], mode=0
                )

                st.update_state(state, state_file_path, "current_bact_plate", 1)
                st.reset_state(state, state_file_path, "active_bact_plate", 0)

            # Discard current active rack to waste if not already done

            if state["active_rack"]:
                logger.debug("Discarding tip rack...")
                cmd.grip_get_tip_rack(hammy, rack_tips)
                cmd.grip_place_tip_rack(hammy, rack_tips, waste=True)

                st.update_state(state, state_file_path, "current_rack", 1)
                st.reset_state(state, state_file_path, "active_rack", 0)

            # If all currently active pcr plates are processed, place them in the dest pcr plate stack

            if state["current_active_pcr_plate"] == state["current_active_pcr_plates"]:
                logger.debug("Placing pcr plates in dest rack...")
                for i in range(state["current_active_pcr_plates"]):
                    cmd.grip_get(
                        hammy,
                        source_pcr_lids[state["current_pcr_plate"]],
                        mode=1,
                        gripWidth=85.0,
                        gripHeight=1.5,
                    )
                    cmd.grip_place(hammy, active_pcr_lids[i], mode=1)
                    cmd.grip_get(
                        hammy,
                        active_pcr_plates[i],
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

                # Reset current active pcr plate to 0

                st.reset_state(state, state_file_path, "current_active_pcr_plate", 0)
                st.reset_state(state, state_file_path, "current_active_pcr_plates", 0)

            st.print_state(state)

        cmd.grip_eject(hammy)

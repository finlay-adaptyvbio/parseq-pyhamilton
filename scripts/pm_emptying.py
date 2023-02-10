import os, csv, math, logging

import commands as cmd
import deck as dk
import state as st
import helpers as hp

from pyhamilton import (
    HamiltonInterface,
    Plate384,
    Lid,  # type: ignore
    Tip96,
    Reservoir300,  # type: ignore
)

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Constants

TIPS = 96

CHANNELS = 2
CHANNEL_1 = "10"
CHANNEL_2 = "01"

# We need to define separate liquid classes for ethanol dispense and aspirate steps

ETHANOL_ASPIRATE = "StandardVolume_EtOH_DispenseJet_Empty"
ETHANOL_DISPENSE = "StandardVolume_EtOH_DispenseJet_Part"


def run(deck: dict, state: dict, state_file_path: str, run_dir_path: str):
    # Plate information and variables
    # Get wells and plates to empty from csv files

    logger.info("Parsing plate map and well map...")
    logger.debug(
        f"Plate map: {os.path.join(run_dir_path, 'pm_emptying_plate_map.csv')}"
    )
    logger.debug(
        f"Well map: {os.path.join(run_dir_path, 'pm_emptying_sorted_well_map.csv')}"
    )

    plate_map_path = os.path.join(run_dir_path, "pm_emptying_plate_map.csv")

    with open(plate_map_path) as f:
        reader = csv.reader(f)
        plate_map = [tuple(row) for row in reader]

    plates = [t[1] for t in plate_map]

    well_map_path = os.path.join(run_dir_path, "pm_emptying_sorted_well_map.csv")

    with open(well_map_path) as f:
        reader = csv.reader(f)
        well_map = [tuple(row) for row in reader]

    wells_to_empty = [(t[2], t[3]) for t in well_map]

    logger.debug(f"Plates: {plates}")
    logger.debug(f"Wells to empty: {wells_to_empty}")

    # Assign labware to deck positions

    logger.info("Assigning labware...")

    source_bact_plates = dk.get_labware_list(
        deck,
        ["F1", "F2", "F3", "F4", "E1", "E2"],
        Plate384,
        [6, 6, 6, 6, 6, 6],
        True,
    )[-len(plates) :]

    dest_bact_plates = dk.get_labware_list(
        deck,
        ["E3", "F1", "F2", "F3", "F4", "E1", "E2"],
        Plate384,
        [6, 6, 6, 6, 6, 6, 6],
        False,
    )[0 : len(plates)]

    active_bact_plate = dk.get_labware_list(deck, ["E5"], Plate384)[0]
    active_bact_lid = dk.get_labware_list(deck, ["E5"], Lid)[0]
    temp_bact_lid = dk.get_labware_list(deck, ["E4"], Lid)[0]

    ethanol_reservoir = dk.get_labware_list(deck, ["C5"], Reservoir300)[0]
    waste_reservoir = dk.get_labware_list(deck, ["D1"], Reservoir300)[0]

    rack_tips = dk.get_labware_list(deck, ["F5"], Tip96)[0]
    tips_remove = [(rack_tips, i) for i in dk.pos_96_2ch(96)][0:2]
    tips_add = [(rack_tips, i) for i in dk.pos_96_2ch(96)][2:4]

    waste = [(waste_reservoir, position) for position in range(182, 187, CHANNELS * 2)]
    ethanol = [
        (ethanol_reservoir, position) for position in range(368, 373, CHANNELS * 2)
    ]

    # Inform user of labware positions, ask for confirmation after placing plates

    logger.debug("Prompt user for plate placement...")

    hp.place_plates(plates, source_bact_plates, "source", state["current_plate"])

    # Main Hamilton method starts here
    # TODO: reduce loops to functions, for example wells_to_reservoir or reservoir_to_wells

    logger.info("Starting Hamilton method...")

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton

        cmd.initialize(hammy)

        # Loop over plates as long as there are plates left to empty
        # Method goes through 3 main steps: remove media, add ethanol, remove ethanol
        # These are implemented as loops (over wells) and have some redundancies

        while state["current_plate"] < len(plates):
            # Build well list for current plate

            logger.debug("Building well list for current plate...")

            wells = [
                (active_bact_plate, dk.string_to_index_384(t[0]))
                for t in wells_to_empty
                if t[1] == plates[state["current_plate"]]
            ]

            # Get next plate from stack and move to active position if not done already

            if not state["active_plate"]:
                logger.debug("Moving next plate to active position...")
                cmd.grip_get(
                    hammy,
                    source_bact_plates[state["current_plate"]],
                    mode=0,
                    gripWidth=82.0,
                    gripHeight=9.0,
                )
                cmd.grip_place(hammy, active_bact_plate, mode=0)
                cmd.grip_get(
                    hammy, active_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, temp_bact_lid, mode=1, eject=True)

                st.reset_state(state, state_file_path, "active_plate", 1)
                st.reset_state(state, state_file_path, "current_well", 0)
                st.reset_state(state, state_file_path, "remove_media", 0)
                st.reset_state(state, state_file_path, "add_ethanol", 0)
                st.reset_state(state, state_file_path, "remove_ethanol", 0)

            # Aspirate media from active plate and dispense to waste reservoir
            # We loop through the wells in groups of 4 (2 * 2 CHANNELS) and aspirate 140 uL from each well

            logger.debug(f"Current well: {state['current_well']}")
            logger.debug(f"Number of wells: {len(wells)}")
            logger.debug(f"Remove media: {bool(state['remove_media'])}")

            if not state["remove_media"]:
                logger.info("Starting media removal...")

                # Get next 2 tips from active tip stack
                logger.debug("Getting next tips for media removal...")

                cmd.tip_pick_up(hammy, tips_remove)

                while state["current_well"] < len(wells):
                    logger.debug("Starting media removal...")

                    # In the case where there are less than 4 wells left, we only aspirate from the remaining wells
                    # Also check if there are enough tips left to pipet the remaining wells
                    # This outputs the minimum of the three values (max wells to process, wells left, tips left)

                    stop = min(2, len(wells[state["current_well"] :]))
                    logger.debug(f"Wells to pipet: {stop}")

                    # Aspirate from wells (with mixing) and dispense to waste
                    # If there is only one well left, aspirate and dispense with one channel

                    if stop == 1:
                        logger.debug("Aspirating from one well...")
                        cmd.aspirate(
                            hammy,
                            [wells[state["current_well"]]],
                            [140.0],
                            channelVariable=CHANNEL_1,
                            mixCycles=3,
                            mixVolume=50.0,
                        )
                        st.update_state(state, state_file_path, "current_well", 1)

                    else:
                        logger.debug("Aspirating from two wells...")
                        cmd.aspirate(
                            hammy,
                            wells[
                                state["current_well"] : state["current_well"] + CHANNELS
                            ],
                            [140.0],
                            mixCycles=3,
                            mixVolume=50.0,
                        )
                        st.update_state(state, state_file_path, "current_well", 2)

                    dispense_volume = [
                        140.0 * math.ceil(stop / CHANNELS),
                        140.0 * math.floor(stop / CHANNELS),
                    ]

                    cmd.dispense(hammy, waste, dispense_volume, dispenseMode=9)

                # Update state variables for next step

                st.reset_state(state, state_file_path, "remove_media", 1)
                st.reset_state(state, state_file_path, "current_well", 0)

                # Eject tips for media removal
                logger.debug("Ejecting tips for media removal...")
                cmd.tip_eject(hammy, tips_remove)

            # Dispense ethanol into emptied wells of active plate
            # This loop advances in steps of 6 (3 * 2 CHANNELS) and dispenses 100 uL into each well

            logger.debug(f"Current well: {state['current_well']}")
            logger.debug(f"Number of wells: {len(wells)}")
            logger.debug(f"Add ethanol: {bool(state['add_ethanol'])}")

            if not state["add_ethanol"]:
                logger.info("Starting ethanol addition...")

                # Get next 2 tips from active tip stack
                logger.debug("Getting new tips for ethanol addition...")
                cmd.tip_pick_up(hammy, tips_add)

                while state["current_well"] < len(wells):
                    # In the case where there are less than 6 wells left, we only aspirate from the remaining wells
                    # Also check if there are enough tips left to pipet the remaining wells
                    # This outputs the minimum of the three values (max wells to process, wells left, tips left)

                    stop = min(6, len(wells[state["current_well"] :]))

                    # Set aspirate volume depending on number of CHANNELS used and aspirate

                    aspirate_volume = [
                        100.0 * math.ceil(stop / CHANNELS),
                        100.0 * math.floor(stop / CHANNELS),
                    ]

                    cmd.aspirate(
                        hammy, ethanol, aspirate_volume, liquidClass=ETHANOL_DISPENSE
                    )

                    for i in range(0, stop, CHANNELS):
                        # Dispense into wells
                        # If there are an odd number of wells left, dispense with one channel

                        if stop - i == 1:
                            cmd.dispense(
                                hammy,
                                [wells[state["current_well"]]],
                                [100.0],
                                channelVariable=CHANNEL_1,
                                liquidClass=ETHANOL_DISPENSE,
                            )
                            st.update_state(
                                state, state_file_path, "current_well", stop - i
                            )

                        else:
                            cmd.dispense(
                                hammy,
                                wells[
                                    state["current_well"] : state["current_well"]
                                    + CHANNELS
                                ],
                                [100.0],
                                liquidClass=ETHANOL_DISPENSE,
                            )
                            st.update_state(
                                state, state_file_path, "current_well", CHANNELS
                            )

                # Update state variables for next step

                st.reset_state(state, state_file_path, "add_ethanol", 1)
                st.reset_state(state, state_file_path, "current_well", 0)

                # Eject tips for ethanol addition
                logger.debug("Ejecting tips for ethanol addition...")
                cmd.tip_eject(hammy, tips_add)

            # Aspirate ethanol from active plate and dispense to waste reservoir
            # Loop advances in steps of 4 (2 * 2 CHANNELS) and aspirates 140 uL from each well

            logger.debug(f"Current well: {state['current_well']}")
            logger.debug(f"Number of wells: {len(wells)}")
            logger.debug(f"Remove ethanol: {bool(state['remove_ethanol'])}")

            if not state["remove_ethanol"]:
                logger.info("Starting ethanol removal...")

                # Get next 2 tips from active tip stack
                logger.debug("Getting new tips for ethanol removal...")
                cmd.tip_pick_up(hammy, tips_remove)

                while state["current_well"] < len(wells):
                    # In the case where there are less than 4 wells left, we only aspirate from the remaining wells
                    # Also check if there are enough tips left to pipet the remaining wells
                    # This outputs the minimum of the three values (max wells to process, wells left, tips left)

                    stop = min(CHANNELS, len(wells[state["current_well"] :]))

                    # Aspirate from wells (with mixing)
                    # If there are an odd number of wells left, aspirate and dispense with one channel

                    if stop == 1:
                        cmd.aspirate(
                            hammy,
                            [wells[state["current_well"]]],
                            [140],
                            channelVariable=CHANNEL_1,
                            liquidClass=ETHANOL_ASPIRATE,
                            mixCycles=3,
                            mixVolume=50.0,
                        )
                        st.update_state(state, state_file_path, "current_well", stop)

                    else:
                        cmd.aspirate(
                            hammy,
                            wells[
                                state["current_well"] : state["current_well"] + CHANNELS
                            ],
                            [140],
                            liquidClass=ETHANOL_ASPIRATE,
                            mixCycles=3,
                            mixVolume=50.0,
                        )
                        st.update_state(
                            state, state_file_path, "current_well", CHANNELS
                        )

                    # Calculate dispense volume depending on number of CHANNELS used and dispense

                    dispense_volume = [
                        140.0 * math.ceil(stop / CHANNELS),
                        140.0 * math.floor(stop / CHANNELS),
                    ]

                    cmd.dispense(
                        hammy,
                        waste,
                        dispense_volume,
                        liquidClass=ETHANOL_ASPIRATE,
                        dispenseMode=9,
                    )

                # Update state variables for next step

                st.reset_state(state, state_file_path, "remove_ethanol", 1)
                st.reset_state(state, state_file_path, "current_well", 0)

                # Eject tips for ethanol removal
                logger.debug("Ejecting tips for ethanol removal...")
                cmd.tip_eject(hammy, tips_remove)

            # Move completed plate to done stack if not already done
            logger.debug(f"Active plate: {bool(state['active_plate'])}")

            if state["active_plate"]:
                logger.info("Moving plate to done stack...")

                # Eject tips to current position in active rack (should already be done)
                # No need to change tips between ethanol removal and media removal steps

                logger.debug("Ejecting tips if needed...")
                cmd.tip_eject(hammy, tips_remove)

                # Place lid on active plate and move to done stack

                cmd.grip_get(
                    hammy, temp_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, active_bact_lid, mode=1)
                cmd.grip_get(
                    hammy, active_bact_plate, mode=0, gripWidth=82.0, gripHeight=9.0
                )
                cmd.grip_place(hammy, dest_bact_plates[state["current_plate"]], mode=0)

                st.update_state(state, state_file_path, "current_plate", 1)
                st.reset_state(state, state_file_path, "active_plate", 0)

            st.print_state(state)

        cmd.grip_eject(hammy)

import logging, shelve

import commands as cmd
import deck as dk
import helpers as hp
import labware as lw
import state as st

from pyhamilton import HamiltonInterface

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Constants

RACKS = 9
TIPS_96 = 96
TIPS_384 = 384

CHANNELS_384_96_8 = "1" + ("0" * 11)


def run(shelf: shelve.Shelf, state: dict, state_file_path: str, run_dir_path: str):
    # Plate information and variables

    logger.debug("Getting number of plates from prompt...")

    plates = hp.prompt_int("Plates to pool", 8)

    pcr_plates = [f"P{i}" for i in range(1, plates + 1)]

    logger.debug(f"Plates to pool: {pcr_plates}")

    # Delete unused labware

    for t in list(zip(shelf["E"][0]["labware"], shelf["E"][0]["frame"]))[::-1]:
        if isinstance(t[1], lw.lid):
            shelf["E"][0]["labware"].remove(t[0])
            shelf["E"][0]["frame"].remove(t[1])
    for k in shelf["E"][0]:
        del shelf["E"][0][k][plates:]
    shelf["E"][0]["frame"] = shelf["E"][0]["frame"][::-1]
    for t in list(zip(shelf["E"][1]["labware"], shelf["E"][1]["frame"]))[::-1]:
        if isinstance(t[1], lw.lid):
            shelf["E"][1]["labware"].remove(t[0])
            shelf["E"][1]["frame"].remove(t[1])
    for k in shelf["E"][1]:
        del shelf["E"][1][k][plates:]
    shelf["E"][1]["frame"] = shelf["E"][1]["frame"][::-1]
    for k in shelf["F"][0]:
        del shelf["F"][0][k][plates:]
    for k in shelf["F"][1]:
        del shelf["F"][1][k][plates:]

    # labware aliases

    logger.info("Assigning labware...")

    src_pcr_plates = shelf["E"][0]["frame"]
    dest_pcr_plates = shelf["E"][1]["frame"]
    src_pooling_plates = shelf["F"][0]["frame"]
    dest_pooling_plates = shelf["F"][1]["frame"]

    edta_reservoir = shelf["C"][4]["frame"][0]
    edta_rack = shelf["B"][4]["frame"][0]

    active_pcr_plate = shelf["C"][3]["frame"][0]
    active_pcr_lid = shelf["C"][3]["frame"][1]
    temp_pcr_lid = shelf["C"][1]["frame"][0]

    active_pooling_plate = shelf["C"][2]["frame"][0]

    carrier = shelf["C"][0]["frame"][0]

    tips_384_96 = shelf["A"][2]["frame"][0]
    tips_holder_384_96 = shelf["A"][3]["frame"][0]
    tips_300 = shelf["F"][4]["frame"][0]
    racks_300 = [shelf["B"][i]["frame"] for i in range(3)]
    active_rack_300, transport_rack_300 = shelf["D"][1]["frame"]

    # Inform user of labware positions, ask for confirmation after placing plates

    logger.debug("Prompt user for plate placement...")

    logger.info("Starting Hamilton method...")

    # Main script starts here

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton

        cmd.initialize(hammy)

        # Load tips into column holder

        logger.debug("Prompt user for number of tip columns left...")
        tip_column = hp.prompt_int("Current tip column in holder (0 for new rack)", 12)

        if tip_column > 0:
            logger.debug("Skipping load step...")
            tips_holder_384_96.fill(lw.pos_row_column_96(8 * tip_column))

        elif tip_column == 0:
            logger.debug("Loading tips into column holder...")
            cmd.tip_pick_up_384(hammy, tips_384_96.full(), tipMode=1)
            cmd.tip_eject_384(hammy, tips_holder_384_96.full())

        else:
            logger.error("Invalid tip column number!")

        # Loop over plates as long as there are still pcr plates to process

        logger.debug(f"Current pcr plate: {state['current_pcr_plate']}")
        logger.debug(f"No. of pcr plates: {len(src_pcr_plates)}")

        while src_pcr_plates:
            # Get next pcr plate from source stack if not already done

            if not state["active_pcr_plate"]:
                logger.debug("Getting next pcr plate from source stack...")
                cmd.grip_get(
                    hammy,
                    source_pcr_plates[state["current_pcr_plate"]],
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=4.0,
                )
                cmd.grip_place(hammy, active_pcr_plate, mode=0)
                cmd.grip_get(
                    hammy, active_pcr_lid, mode=1, gripWidth=85.0, gripHeight=0.5
                )
                cmd.grip_place(hammy, temp_pcr_lid, mode=1)

                st.reset_state(state, state_file_path, "active_pcr_plate", 1)
                st.reset_state(state, state_file_path, "current_quadrant", 0)
                st.reset_state(state, state_file_path, "current_column", 0)
                st.reset_state(state, state_file_path, "current_well", 0)
                st.reset_state(state, state_file_path, "edta", 0)
                st.reset_state(state, state_file_path, "384_to_96", 0)
                st.reset_state(state, state_file_path, "96_to_8", 0)
                st.reset_state(state, state_file_path, "8_to_1", 0)

            # Get next pooling plate from source stack if not already done

            if not state["active_pooling_plate"]:
                logger.debug("Getting next pooling plate...")
                cmd.grip_get(
                    hammy,
                    source_pooling_plates[state["current_pooling_plate"]],
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=5.0,
                )
                cmd.grip_place(hammy, active_pooling_plate, mode=0)

                st.reset_state(state, state_file_path, "active_pooling_plate", 1)

            # # Add EDTA to pcr plate if not already done

            # if not state["edta"]:
            #     logger.info("Adding EDTA to pcr plate...")
            #     cmd.tip_pick_up_384(hammy, edta_tips)
            #     cmd.aspirate_384(hammy, edta, 20.0, liquidHeight=2.0)
            #     cmd.dispense_384(
            #         hammy, active_pcr_wells, 20.0, liquidHeight=11.0, dispenseMode=9
            #     )
            #     cmd.tip_eject_384(hammy, edta_tips, 1)

            #     st.reset_state(state, state_file_path, "edta", 1)

            # Get next 96_384-tip rack if not already done

            if not state["active_rack"]:
                logger.debug("Getting next tip rack...")
                cmd.grip_get_tip_rack(hammy, racks_96[state["current_rack"]])
                cmd.grip_place_tip_rack(hammy, rack_96_virtual)

                st.reset_state(state, state_file_path, "active_rack", 1)

            # Transfer 384 wells in pcr plate to 96 in pooling plate if not already done

            if not state["384_to_96"]:
                logger.info("Transferring 384 wells to 96...")
                cmd.tip_pick_up_384(hammy, tips_96, tipMode=1)

                for quadrant in range(state["current_quadrant"], 4):
                    pcr_wells = [
                        (active_pcr_plate, i) for i in dk.pos_96_in_384(quadrant)
                    ]

                    cmd.aspirate_384(
                        hammy,
                        pcr_wells,
                        5.0,
                        liquidHeight=3.0,
                        mixCycles=3,
                        mixVolume=20.0,
                    )
                    cmd.dispense_384(
                        hammy,
                        active_pooling_wells,
                        5.0,
                        liquidHeight=10.0,
                        dispenseMode=9,
                    )

                    st.update_state(state, state_file_path, "current_quadrant", 1)

                cmd.tip_eject_384(hammy, tips_96, 2)
                st.reset_state(state, state_file_path, "384_to_96", 1)

            # Discard current 96_384-tip rack if not already done

            # TODO: no need to reset rack after this step or only reset at end of method.
            # FIXME: don't increment in some cases

            if state["active_rack"]:
                logger.debug("Discarding current tip rack...")
                cmd.grip_get_tip_rack(hammy, rack_96_tips)
                cmd.grip_place_tip_rack(hammy, rack_96_tips, waste=True)

                st.update_state(state, state_file_path, "current_rack", 1)
                st.reset_state(state, state_file_path, "active_rack", 0)

            # Transfer columns 2-12 to column 1 in pooling plate using 8 tips on 384-head if not already done

            if not state["96_to_8"]:
                logger.info("Transferring 96 wells to 8...")
                column_tips = [(column_holder, i) for i in dk.pos_96_rev()][
                    state["current_tip_column"] * 8 :
                ]

                cmd.tip_pick_up_384(
                    hammy,
                    column_tips,
                    tipMode=1,
                    reducedPatternMode=4,
                    headPatternAsVariable=1,
                    headPatternVariable=CHANNELS_384_96_8,
                )

                for column in range(state["current_column"], 12):
                    cmd.aspirate_384(
                        hammy,
                        active_pooling_wells[8 * column : 8 * (column + 1)],
                        16.0,
                        liquidHeight=0.5,
                    )
                    cmd.dispense_384(
                        hammy,
                        active_pooling_wells_8ch,
                        16.0,
                        dispenseMode=9,
                        liquidHeight=10.0,
                    )

                    st.update_state(state, state_file_path, "current_column", 1)

                cmd.tip_eject_384(hammy, column_tips, 2)

                st.update_state(state, state_file_path, "current_tip_column", 1)
                st.reset_state(state, state_file_path, "96_to_8", 1)

            # Transfer column 1 in pooling plate to next eppendorf tube using 2 channels if not already done

            if not state["8_to_1"]:
                logger.info("Transferring 8 wells to 1...")
                cmd.tip_pick_up(
                    hammy, tips_300[state["current_tip"] : state["current_tip"] + 2]
                )

                for well in range(state["current_well"], 8, 2):
                    cmd.aspirate(
                        hammy,
                        active_pooling_wells_2ch[well : well + 2],
                        [192],
                        liquidHeight=0.5,
                    )
                    cmd.dispense(
                        hammy,
                        [
                            eppies[state["current_pcr_plate"]],
                            eppies[state["current_pcr_plate"]],
                        ],
                        [192],
                        dispenseMode=9,
                        liquidHeight=35.0,
                    )

                    st.update_state(state, state_file_path, "current_well", 2)

                cmd.tip_eject(
                    hammy,
                    tips_300[state["current_tip"] : state["current_tip"] + 2],
                    waste=True,
                )

                st.update_state(state, state_file_path, "current_tip", 2)
                st.update_state(state, state_file_path, "current_eppi", 1)
                st.reset_state(state, state_file_path, "8_to_1", 1)

            # Move active pcr plate to destination stack if not already done

            if state["active_pcr_plate"]:
                logger.debug("Moving active pcr plate to destination stack...")
                cmd.grip_get(
                    hammy,
                    temp_pcr_lid,
                    mode=1,
                    gripWidth=85.0,
                    gripHeight=0.5,
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

            # Move active pooling plate to destination stack if not already done

            if state["active_pooling_plate"]:
                logger.debug("Moving active pooling plate to destination stack...")
                cmd.grip_get(
                    hammy,
                    active_pooling_plate,
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=9.0,
                )
                cmd.grip_place(
                    hammy, dest_pooling_plates[state["current_pooling_plate"]], mode=0
                )

                st.update_state(state, state_file_path, "current_pooling_plate", 1)
                st.reset_state(state, state_file_path, "active_pooling_plate", 0)

            st.print_state(state)

        cmd.grip_eject(hammy)

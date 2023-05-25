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


def run(
    shelf: shelve.Shelf[list[dict[str, list]]],
    state: dict,
    state_file_path: str,
    run_dir_path: str,
):
    # Plate information and variables
    plates = hp.prompt_int("Plates to pool", 8)
    pcr_plates = [f"P{i}" for i in range(1, plates + 1)]

    # Delete unused labware
    for t in list(zip(shelf["E"][0]["labware"], shelf["E"][0]["frame"]))[::-1]:
        if isinstance(t[1], lw.lid):
            shelf["E"][0]["labware"].remove(t[0])
            shelf["E"][0]["frame"].remove(t[1])
    for k in shelf["E"][0]:
        del shelf["E"][0][k][plates:]
    for t in list(zip(shelf["E"][1]["labware"], shelf["E"][1]["frame"]))[::-1]:
        if isinstance(t[1], lw.lid):
            shelf["E"][1]["labware"].remove(t[0])
            shelf["E"][1]["frame"].remove(t[1])
    for k in shelf["E"][1]:
        del shelf["E"][1][k][plates:]
    for k in shelf["F"][0]:
        del shelf["F"][0][k][plates:]
    for k in shelf["F"][1]:
        del shelf["F"][1][k][plates:]

    # labware aliases
    src_pcr_plates = shelf["E"][0]["frame"]
    dest_pcr_plates = shelf["E"][1]["frame"]
    src_pooling_plates = shelf["F"][0]["frame"]
    dest_pooling_plates = shelf["F"][1]["frame"]

    edta_reservoir = shelf["C"][4]["frame"][0]
    edta_rack = shelf["B"][4]["frame"][0]

    active_pcr_lid, active_pcr_plate = shelf["C"][3]["frame"]
    temp_pcr_lid = shelf["C"][1]["frame"][0]

    active_pooling_plate = shelf["C"][2]["frame"][0]

    carrier = shelf["C"][0]["frame"][0]

    tips_384_96 = shelf["A"][2]["frame"][0]
    tips_holder_384_96 = shelf["A"][3]["frame"][0]
    tips_300 = shelf["F"][4]["frame"][0]
    racks_50 = [shelf["B"][i]["frame"] for i in range(2)]
    active_rack_50, transport_rack_50 = shelf["D"][1]["frame"]

    # Inform user of labware positions, ask for confirmation after placing plates

    # Main script starts here
    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton
        cmd.initialize(hammy)

        # Load tips into column holder
        tip_column = hp.prompt_int("Current tip column in holder (0 for new rack)", 12)

        if tip_column > 0:
            tips_holder_384_96.fill(lw.pos_row_column_96(8 * tip_column))
        elif tip_column == 0:
            cmd.tip_pick_up_384(hammy, tips_384_96.full())
            cmd.tip_eject_384(hammy, tips_holder_384_96.full())
        else:
            logger.warning("Invalid tip column number!")

        # Loop over plates as long as there are still pcr plates to process
        while src_pcr_plates:
            # Get next pcr plate from source stack if not already done
            if not state["active_pcr_plate"]:
                src_pcr_plate = src_pcr_plates[-1].plate
                cmd.grip_get(
                    hammy,
                    src_pcr_plate,
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=4.0,
                )
                cmd.grip_place(hammy, active_pcr_plate.plate, mode=0)
                cmd.grip_get(
                    hammy, active_pcr_lid.lid, mode=1, gripWidth=85.0, gripHeight=0.5
                )
                cmd.grip_place(hammy, temp_pcr_lid.lid, mode=1)
                src_pcr_plates.pop()

                st.reset_state(state, state_file_path, "get_pcr_plate", 1)

                st.reset_state(state, state_file_path, "add_edta", 0)
                st.reset_state(state, state_file_path, "384_to_96", 0)
                st.reset_state(state, state_file_path, "96_to_8", 0)
                st.reset_state(state, state_file_path, "8_to_1", 0)

            # Get next pooling plate from source stack if not already done
            if not state["active_pooling_plate"]:
                src_pooling_plate = src_pooling_plates[-1].plate
                cmd.grip_get(
                    hammy,
                    src_pooling_plate,
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=5.0,
                )
                cmd.grip_place(hammy, active_pooling_plate.plate)
                src_pooling_plates.pop()

                st.reset_state(state, state_file_path, "active_pooling_plate", 1)

            # Add EDTA to pcr plate if not already done
            if not state["add_edta"]:
                cmd.tip_pick_up_384(hammy, edta_rack.full())
                cmd.aspirate_384(hammy, edta_reservoir.full(), 20.0, liquidHeight=2.0)
                cmd.dispense_384(
                    hammy,
                    active_pcr_plate.full(),
                    20.0,
                    liquidHeight=11.0,
                    dispenseMode=9,
                )
                cmd.tip_eject_384(hammy, mode=1)

                st.reset_state(state, state_file_path, "add_edta", 1)

            # Get next 96_384-tip rack of 50 uL tips if not already done
            if not state["active_rack"]:
                rack, n = None, None
                for i in range(2):
                    try:
                        rack = racks_50[i][-1]
                    except IndexError:
                        continue
                    else:
                        n = i
                        break
                assert rack is not None
                assert n is not None

                cmd.grip_get_tip_rack(hammy, rack.rack)
                cmd.grip_place_tip_rack(hammy, transport_rack_50.rack)
                racks_50[n].pop()

            # Transfer 384 wells in pcr plate to 96 in pooling plate if not already done
            if not state["384_to_96"]:
                cmd.tip_pick_up_384(hammy, active_rack_50.full())

                for _ in range(4):
                    cmd.aspirate_384(
                        hammy,
                        active_pcr_plate.quadrant(),
                        5.0,
                        liquidHeight=3.0,
                        mixCycles=3,
                        mixVolume=20.0,
                    )
                    cmd.dispense_384(
                        hammy,
                        active_pooling_plate.full(),
                        5.0,
                        liquidHeight=10.0,
                        dispenseMode=9,
                    )
                active_pcr_plate.reset()

                cmd.tip_eject_384(hammy, mode=2)
                st.reset_state(state, state_file_path, "384_to_96", 1)

            # Discard current 96_384-tip rack if not already done
            if state["active_rack"]:
                cmd.grip_get_tip_rack(hammy, active_rack_50.rack)
                cmd.grip_place_tip_rack(hammy, active_rack_50.rack, waste=True)

                st.reset_state(state, state_file_path, "active_rack", 0)

            # Transfer columns 2-12 to column 1 in pooling plate using 8 tips on 384-head if not already done
            if not state["96_to_8"]:
                cmd.tip_pick_up_384(hammy, tips_holder_384_96.mph384(8, 1))
                active_pooling_plate.fill(lw.pos_row_column_96(88, 8))
                while active_pooling_plate.total() > 0:
                    cmd.aspirate_384(
                        hammy,
                        active_pooling_plate.mph384(8, 1),
                        16.0,
                        liquidHeight=0.5,
                    )
                    cmd.dispense_384(
                        hammy,
                        active_pooling_plate.static(lw.pos_row_column_96(8, 8)),
                        16.0,
                        dispenseMode=9,
                        liquidHeight=10.0,
                    )
                active_pooling_plate.reset()
                cmd.tip_eject_384(hammy, mode=2)

                st.reset_state(state, state_file_path, "96_to_8", 1)

            # Transfer column 1 in pooling plate to next eppendorf tube using 2 channels if not already done
            if not state["8_to_1"]:
                cmd.tip_pick_up(hammy, tips_300.ch2(2))
                active_pooling_plate.fill(lw.pos_row_column_96(8))
                carrier.fill(lw.pos_row_column_24(plates))

                while active_pooling_plate.total() > 0:
                    cmd.aspirate(
                        hammy,
                        active_pooling_plate.ch2(2),
                        [192],
                        liquidHeight=0.5,
                    )
                    cmd.dispense(
                        hammy,
                        carrier.ch2(1) * 2,
                        [192],
                        dispenseMode=9,
                        liquidHeight=35.0,
                    )

                cmd.tip_eject(hammy, waste=True)

                st.reset_state(state, state_file_path, "8_to_1", 1)

            # Move active pcr plate to destination stack if not already done
            if state["active_pcr_plate"]:
                cmd.grip_get(
                    hammy,
                    temp_pcr_lid.lid,
                    mode=1,
                    gripWidth=85.0,
                    gripHeight=0.5,
                )
                cmd.grip_place(hammy, active_pcr_lid.lid, mode=1)
                cmd.grip_get(
                    hammy,
                    active_pcr_plate.plate,
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=6.0,
                )
                cmd.grip_place(
                    hammy,
                    dest_pcr_plates[0].plate,
                    mode=0,
                )
                dest_pcr_plates.pop(0)

                st.reset_state(state, state_file_path, "active_pcr_plate", 0)

            # Move active pooling plate to destination stack if not already done

            if state["active_pooling_plate"]:
                cmd.grip_get(
                    hammy,
                    active_pooling_plate.plate,
                    mode=0,
                    gripWidth=81.0,
                    gripHeight=9.0,
                )
                cmd.grip_place(hammy, dest_pooling_plates[0].plate, mode=0)
                dest_pooling_plates.pop(0)

                st.reset_state(state, state_file_path, "active_pooling_plate", 0)

            st.print_state(state)

        cmd.grip_eject(hammy)

import os, csv, logging

import commands as cmd
import deck as dk
import state as st
import helpers as hp

from pyhamilton import (
    HamiltonInterface,
    Plate384,
    Lid,  # type: ignore
    Tip96,
)

# Logging

logger = logging.getLogger(__name__)

# Constants

RACKS = 12
TIPS = 96

CHANNELS = 2
CHANNEL_1 = "10"
CHANNEL_2 = "01"

LIQUID_CLASS = "Tip_50ul_Water_DispenseJet_Empty"


def run(deck: dict, state: dict, state_file_path: str, run_dir_path: str):
    # Get plates and well map from csv files

    plates_path = os.path.join(run_dir_path, "cherry_picking_plates.csv")

    with open(plates_path, "r") as f:
        reader = csv.reader(f)
        plates = [row[0] for row in reader]

    source_plates = [p for p in plates]

    wells_path = os.path.join(run_dir_path, "cherry_picking_wells.csv")

    with open(wells_path, "r") as f:
        reader = csv.reader(f)
        wells = [tuple(row) for row in reader]

    wells_to_empty = [(t[0], t[1]) for t in wells]

    target_plates = [f"P{i}" for i in range(1, len(wells) // 384 + 2)]
    wells_to_fill = [
        (w, p) for w in dk.pos_384_2ch(384) for p in target_plates[:-1]
    ] + [(w, target_plates[-1]) for w in dk.pos_384_2ch(len(wells) % 384)]

    # Assign labware to deck positions

    target_bact_plates = dk.get_labware_list(
        deck,
        ["F1", "F2"],
        Plate384,
        [6, 6],
        True,
    )[-len(target_plates) :]

    source_bact_plates = dk.get_labware_list(
        deck,
        ["E1", "E2", "E3"],
        Plate384,
        [6, 6, 6],
        True,
    )[-len(source_plates) :]

    dest_target_bact_plates = dk.get_labware_list(
        deck,
        ["F3", "F1", "F2"],
        Plate384,
        [6, 6, 6],
        False,
    )[0 : len(target_plates)]

    dest_source_bact_plates = dk.get_labware_list(
        deck,
        ["F4", "E1", "E2", "E3"],
        Plate384,
        [6, 6, 6, 6],
        False,
    )[0 : len(source_plates)]

    active_source_bact_plate = dk.get_labware_list(deck, ["E5"], Plate384)[0]
    active_source_bact_lid = dk.get_labware_list(deck, ["E5"], Lid)[0]
    temp_source_bact_lid = dk.get_labware_list(deck, ["C3"], Lid)[0]

    active_target_bact_plate = dk.get_labware_list(deck, ["E4"], Plate384)[0]
    active_target_bact_lid = dk.get_labware_list(deck, ["E4"], Lid)[0]
    temp_target_bact_lid = dk.get_labware_list(deck, ["C2"], Lid)[0]

    racks = dk.get_labware_list(deck, ["B1", "B2", "B3"], Tip96, [4, 4, 4], True)
    rack_tips, rack_virtual = dk.get_labware_list(deck, ["F5"], Tip96, [2])
    tips = [(rack_tips, i) for i in dk.pos_96_2ch(96)]

    # HACK: get rid of type errors due to state not being initialized

    source_wells = []
    target_wells = []

    # Inform user of labware positions, ask for confirmation after placing plates

    hp.place_plates(
        source_plates, source_bact_plates, "source", state["current_source_plate"]
    )
    hp.place_plates(
        target_plates, target_bact_plates, "target", state["current_target_plate"]
    )

    # Main script starts here
    # TODO: reduce loops to functions to make it more readable
    # TODO: Check if total number of tips available is enough for the protocol, add prompt when new tip racks are needed

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton

        cmd.initialize(hammy)

        # Loop over plates as long as there are still source plates to process

        while state["current_source_plate"] < len(source_plates) - 1:
            # Get next target plate if not already done

            if not state["active_target_plate"]:
                cmd.grip_get(
                    hammy,
                    target_bact_plates[state["current_target_plate"]],
                    mode=0,
                    gripWidth=82.0,
                )
                cmd.grip_place(hammy, active_target_bact_plate, mode=0)
                cmd.grip_get(
                    hammy,
                    active_target_bact_lid,
                    mode=1,
                    gripWidth=85.2,
                    gripHeight=5.0,
                )
                cmd.grip_place(hammy, temp_target_bact_lid, mode=1)

                st.reset_state(state, state_file_path, "active_target_plate", 1)

                # Build list of target wells for current plate

                target_wells = [
                    (active_target_bact_plate, t[0])
                    for t in wells_to_fill
                    if t[1] == target_plates[state["current_target_plate"]]
                ]

                st.reset_state(state, state_file_path, "current_target_well", 0)

            # Get next source plate if not already done

            if not state["active_source_plate"]:
                cmd.grip_get(
                    hammy,
                    source_bact_plates[state["current_source_plate"]],
                    mode=0,
                    gripWidth=82.0,
                )
                cmd.grip_place(hammy, active_source_bact_plate, mode=0)
                cmd.grip_get(
                    hammy,
                    active_source_bact_lid,
                    mode=1,
                    gripWidth=85.2,
                    gripHeight=5.0,
                )
                cmd.grip_place(hammy, temp_source_bact_lid, mode=1)

                st.reset_state(state, state_file_path, "active_source_plate", 1)

                # Build list of source wells for current plate

                source_wells = [
                    (active_source_bact_plate, dk.string_to_index_384(t[0]))
                    for t in wells_to_empty
                    if t[1] == source_plates[state["current_source_plate"]]
                ]

                st.reset_state(state, state_file_path, "current_source_well", 0)

            # Check if there are still wells to process in the current source plate
            # Swich to next source plate if current one is done

            if state["current_source_well"] >= len(source_wells):
                cmd.grip_get(
                    hammy, temp_source_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, active_source_bact_lid, mode=1)
                cmd.grip_get(
                    hammy,
                    active_source_bact_plate,
                    mode=0,
                    gripWidth=82.0,
                    gripHeight=9.0,
                )
                cmd.grip_place(
                    hammy,
                    dest_source_bact_plates[state["current_source_plate"]],
                    mode=0,
                )

                st.update_state(state, state_file_path, "current_source_plate", 1)
                st.reset_state(state, state_file_path, "active_source_plate", 0)

            # Check if there are still wells to process in the current target plate
            # Swich to next target plate if current one is done

            if state["current_target_well"] >= len(target_wells):
                cmd.grip_get(
                    hammy, temp_target_bact_lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, active_target_bact_lid, mode=1)
                cmd.grip_get(
                    hammy,
                    active_target_bact_plate,
                    mode=0,
                    gripWidth=82.0,
                    gripHeight=9.0,
                )
                cmd.grip_place(
                    hammy,
                    dest_target_bact_plates[state["current_target_plate"]],
                    mode=0,
                )

                st.update_state(state, state_file_path, "current_target_plate", 1)
                st.reset_state(state, state_file_path, "active_target_plate", 0)

            # Check if there are still tips in the active rack
            # Discard rack and get new one from stacked racks if current one is done

            if state["current_tip"] >= TIPS:
                cmd.grip_get_tip_rack(hammy, rack_tips)
                cmd.grip_place_tip_rack(hammy, rack_tips, waste=True)
                cmd.grip_get_tip_rack(hammy, racks[state["current_rack"]])
                cmd.grip_place_tip_rack(hammy, rack_virtual)

                st.update_state(state, state_file_path, "current_rack", 1)
                st.reset_state(state, state_file_path, "current_tip", 0)

            # Check how many wells are left to pipet in the current source and target plate
            # Also check if there are enough tips left to pipet the remaining wells

            # This outputs the minimum of the three values (wells left, tips left, channels)

            source_well_stop = min(
                CHANNELS,
                len(source_wells[state["current_source_well"] :]),
                (TIPS - state["current_tip"]),
            )
            target_well_stop = min(
                CHANNELS,
                len(target_wells[state["current_target_well"] :]),
                (TIPS - state["current_tip"]),
            )

            # In the case that there is only one well left to pipet, use only one channel

            if source_well_stop == 1 or target_well_stop == 1:
                cmd.tip_pick_up(
                    hammy, [tips[state["current_tip"]]], channelVariable=CHANNEL_1
                )
                cmd.aspirate(
                    hammy,
                    [source_wells[state["current_source_well"]]],
                    [5],
                    channelVariable=CHANNEL_1,
                    mixCycles=3,
                    mixVolume=50.0,
                    liquidClass=LIQUID_CLASS,
                )
                cmd.dispense(
                    hammy,
                    [target_wells[state["current_target_well"]]],
                    [5],
                    channelVariable=CHANNEL_1,
                    dispenseMode=9,
                    liquidClass=LIQUID_CLASS,
                )
                cmd.tip_eject(hammy, [tips[state["current_tip"]]], waste=True)

                st.update_state(state, state_file_path, "current_source_well", 1)
                st.update_state(state, state_file_path, "current_target_well", 1)
                st.update_state(state, state_file_path, "current_tip", 1)

            # Otherwise, use all channels (as long as pipetting steps are equal between source and target)

            elif source_well_stop == CHANNELS and target_well_stop == CHANNELS:
                cmd.tip_pick_up(
                    hammy,
                    tips[state["current_tip"] : state["current_tip"] + CHANNELS],
                )
                cmd.aspirate(
                    hammy,
                    source_wells[
                        state["current_source_well"] : state["current_source_well"]
                        + CHANNELS
                    ],
                    [5.0],
                    mixCycles=3,
                    mixVolume=50.0,
                    liquidClass=LIQUID_CLASS,
                )
                cmd.dispense(
                    hammy,
                    target_wells[
                        state["current_target_well"] : state["current_target_well"]
                        + CHANNELS
                    ],
                    [5.0],
                    dispenseMode=9,
                    liquidClass=LIQUID_CLASS,
                )
                cmd.tip_eject(
                    hammy,
                    tips[state["current_tip"] : state["current_tip"] + CHANNELS],
                    waste=True,
                )

                st.update_state(state, state_file_path, "current_source_well", CHANNELS)
                st.update_state(state, state_file_path, "current_target_well", CHANNELS)
                st.update_state(state, state_file_path, "current_tip", CHANNELS)

            st.print_state(state)

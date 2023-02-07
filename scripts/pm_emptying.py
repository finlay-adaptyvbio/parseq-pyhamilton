import os, csv, math

import commands as cmd
import deck as dk
import state as st

from pyhamilton import (
    HamiltonInterface,
    Plate384,
    Lid,  # type: ignore
    Tip96,
    Reservoir300,  # type: ignore
)

# Constants

CHANNELS = 2
CHANNEL_1 = "10"
CHANNEL_2 = "01"

TIPS = 96
RACKS = 9

# We need to define separate liquid classes for ethanol dispense and aspirate steps

ETHANOL_ASPIRATE = "StandardVolume_EtOH_DispenseJet_Empty"
ETHANOL_DISPENSE = "StandardVolume_EtOH_DispenseJet_Part"


def run(deck: dict, state: dict, state_file_path: str, run_dir_path: str):
    # Plate information and variables
    # Get wells and plates to empty from csv files

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

    # Define labware from parsed layout file

    source_bact_plates = dk.get_labware_list(
        deck,
        ["F1", "F2", "F3", "F4", "E1", "E2"],
        Plate384,
        [6, 6, 6, 6, 6, 6],
        True,
    )[0 : len(plates)]

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

    racks = dk.get_labware_list(deck, ["B1", "B2", "B3"], Tip96, [4, 4, 4], True)
    rack_tips, rack_virtual = dk.get_labware_list(deck, ["F5"], Tip96, [2])
    tips = [(rack_tips, i) for i in dk.pos_96_2ch(96)]

    waste = [(waste_reservoir, position) for position in range(182, 187, CHANNELS * 2)]
    ethanol = [
        (ethanol_reservoir, position) for position in range(368, 373, CHANNELS * 2)
    ]

    # HACK: get rid of type errors due to state not being initialized

    wells = []

    # Main Hamilton method starts here
    # TODO: reduce loops to functions, for example wells_to_reservoir or reservoir_to_wells

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton

        cmd.initialize(hammy)

        # Loop over plates as long as there are plates left to empty
        # Method goes through 3 main steps: remove media, add ethanol, remove ethanol
        # These are implemented as loops (over wells) and have some redundancies

        while state["current_plate"] < len(plates):
            # Get next plate from stack and move to active position if not done already

            if not state["active_plate"]:
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

                # Build well list for current plate

                wells = [
                    (active_bact_plate, dk.string_to_index_384(t[0]))
                    for t in wells_to_empty
                    if t[1] == plates[state["current_plate"]]
                ]

                st.reset_state(state, state_file_path, "active_plate", 1)
                st.reset_state(state, state_file_path, "current_well", 0)
                st.reset_state(state, state_file_path, "remove_media", 0)
                st.reset_state(state, state_file_path, "add_ethanol", 0)
                st.reset_state(state, state_file_path, "remove_ethanol", 0)

            # Get next 2 tips from active tip stack

            cmd.tip_pick_up(
                hammy, tips[state["current_tip"] : state["current_tip"] + CHANNELS]
            )

            st.update_state(state, state_file_path, "current_tip", CHANNELS)
            st.reset_state(state, state_file_path, "channel_steps", 0)

            # Aspirate media from active plate and dispense to waste reservoir
            # We loop through the wells in groups of 4 (2 * 2 CHANNELS) and aspirate 140 uL from each well

            while state["current_well"] < len(wells) and not state["remove_media"]:
                # Check if there are still tips in the active rack
                # Discard rack and get new one from stacked racks if current one is done

                if state["current_tip"] >= TIPS:
                    cmd.grip_get_tip_rack(hammy, tips)
                    cmd.grip_place_tip_rack(hammy, tips, waste=True)
                    cmd.grip_get_tip_rack(hammy, racks[state["current_rack"]])
                    cmd.grip_place_tip_rack(hammy, rack_virtual)

                    st.update_state(state, state_file_path, "current_rack", 1)
                    st.reset_state(state, state_file_path, "current_tip", 0)

                # In the case where there are less than 4 wells left, we only aspirate from the remaining wells
                # Also check if there are enough tips left to pipet the remaining wells
                # This outputs the minimum of the three values (max wells to process, wells left, tips left)

                stop = min(
                    4,
                    len(wells[state["current_well"] :]),
                    (TIPS - state["current_tip"]),
                )

                for i in range(0, stop, CHANNELS):
                    # Currently there seems to be a bug in VENUS when aspirating > 60 times from one channel consecutively
                    # This is a workaround to reset the channel after 58 steps

                    if state["channel_steps"] >= 60:
                        cmd.tip_eject(
                            hammy,
                            tips[
                                state["current_tip"] : state["current_tip"] + CHANNELS
                            ],
                            waste=True,
                        )
                        st.update_state(state, state_file_path, "current_tip", CHANNELS)
                        cmd.tip_pick_up(
                            hammy,
                            tips[
                                state["current_tip"] : state["current_tip"] + CHANNELS
                            ],
                        )
                        st.reset_state(state, state_file_path, "channel_steps", 0)

                    # The first aspirate command must be set to aspirateMode = 0, otherwise the pipette will not aspirate blowout volume
                    # This doesn't seem to work (VENUS still outputs warning about aspiration mode)
                    # This is probably related to plunger errors encountered after 60 steps

                    if i >= 2:
                        aspirateMode = 1
                    else:
                        aspirateMode = 0

                    # Aspirate from wells (with mixing) and dispense to waste
                    # If there is only one well left, aspirate and dispense with one channel

                    if stop - i == 1:
                        cmd.aspirate(
                            hammy,
                            [wells[state["current_well"]]],
                            [140.0],
                            channelVariable=CHANNEL_1,
                            aspirateMode=aspirateMode,
                            mixCycles=3,
                            mixVolume=50.0,
                        )
                        st.update_state(state, state_file_path, "current_well", 1)

                    else:
                        cmd.aspirate(
                            hammy,
                            wells[
                                state["current_well"] : state["current_well"] + CHANNELS
                            ],
                            [140.0],
                            aspirateMode=aspirateMode,
                            mixCycles=3,
                            mixVolume=50.0,
                        )
                        st.update_state(state, state_file_path, "current_well", 2)

                    st.update_state(state, state_file_path, "channel_steps", 1)

                dispense_volume = [
                    140.0 * math.ceil(stop / CHANNELS),
                    140.0 * math.floor(stop / CHANNELS),
                ]

                cmd.dispense(hammy, waste, dispense_volume, dispenseMode=9)

            # Eject tips and pick up new ones

            cmd.tip_eject(
                hammy,
                tips[state["current_tip"] : state["current_tip"] + CHANNELS],
                waste=True,
            )
            st.update_state(state, state_file_path, "current_tip", CHANNELS)
            cmd.tip_pick_up(
                hammy,
                tips[state["current_tip"] : state["current_tip"] + CHANNELS],
            )
            st.reset_state(state, state_file_path, "channel_steps", 0)

            # Update state variables for next step

            st.reset_state(state, state_file_path, "remove_media", 1)
            st.reset_state(state, state_file_path, "current_well", 0)

            # Dispense ethanol into emptied wells of active plate
            # This loop advances in steps of 6 (3 * 2 CHANNELS) and dispenses 100 uL into each well

            while state["current_well"] < len(wells) and not state["add_ethanol"]:
                # Check if there are still tips in the active rack
                # Discard rack and get new one from stacked racks if current one is done

                if state["current_tip"] >= TIPS:
                    cmd.grip_get_tip_rack(hammy, tips)
                    cmd.grip_place_tip_rack(hammy, tips, waste=True)
                    cmd.grip_get_tip_rack(hammy, racks[state["current_rack"]])
                    cmd.grip_place_tip_rack(hammy, rack_virtual)

                    st.update_state(state, state_file_path, "current_rack", 1)
                    st.reset_state(state, state_file_path, "current_tip", 0)

                # In the case where there are less than 6 wells left, we only aspirate from the remaining wells
                # Also check if there are enough tips left to pipet the remaining wells
                # This outputs the minimum of the three values (max wells to process, wells left, tips left)

                stop = min(
                    6,
                    len(wells[state["current_well"] :]),
                    (TIPS - state["current_tip"]),
                )

                # Currently there seems to be a bug in VENUS when aspirating > 60 times from one channel consecutively
                # This is a workaround to reset the channel after 58 steps

                if state["channel_steps"] >= 60:
                    cmd.tip_eject(
                        hammy,
                        tips[state["current_tip"] : state["current_tip"] + CHANNELS],
                        waste=True,
                    )
                    st.update_state(state, state_file_path, "current_tip", CHANNELS)
                    cmd.tip_pick_up(
                        hammy,
                        tips[state["current_tip"] : state["current_tip"] + CHANNELS],
                    )
                    st.reset_state(state, state_file_path, "channel_steps", 0)

                # Set aspirate volume depending on number of CHANNELS used and aspirate

                aspirate_volume = [
                    100.0 * math.ceil(stop / CHANNELS),
                    100.0 * math.floor(stop / CHANNELS),
                ]

                cmd.aspirate(
                    hammy, ethanol, aspirate_volume, liquidClass=ETHANOL_DISPENSE
                )
                st.update_state(state, state_file_path, "channel_steps", 1)

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
                                state["current_well"] : state["current_well"] + CHANNELS
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

            # Aspirate ethanol from active plate and dispense to waste reservoir
            # Loop advances in steps of 4 (2 * 2 CHANNELS) and aspirates 140 uL from each well

            while state["current_well"] < len(wells) and not state["remove_ethanol"]:
                # Check if there are still tips in the active rack
                # Discard rack and get new one from stacked racks if current one is done

                if state["current_tip"] >= TIPS:
                    cmd.grip_get_tip_rack(hammy, tips)
                    cmd.grip_place_tip_rack(hammy, tips, waste=True)
                    cmd.grip_get_tip_rack(hammy, racks[state["current_rack"]])
                    cmd.grip_place_tip_rack(hammy, rack_virtual)

                    st.update_state(state, state_file_path, "current_rack", 1)
                    st.reset_state(state, state_file_path, "current_tip", 0)

                # In the case where there are less than 4 wells left, we only aspirate from the remaining wells
                # Also check if there are enough tips left to pipet the remaining wells
                # This outputs the minimum of the three values (max wells to process, wells left, tips left)

                stop = min(
                    4,
                    len(wells[state["current_well"] :]),
                    (TIPS - state["current_tip"]),
                )

                for i in range(0, stop, CHANNELS):
                    # Currently there seems to be a bug in VENUS when aspirating > 60 times from one channel consecutively
                    # This is a workaround to reset the channel after 60 steps

                    if state["channel_steps"] >= 60:
                        cmd.tip_eject(
                            hammy,
                            tips[
                                state["current_tip"] : state["current_tip"] + CHANNELS
                            ],
                            waste=True,
                        )
                        st.update_state(state, state_file_path, "current_tip", CHANNELS)
                        cmd.tip_pick_up(
                            hammy,
                            tips[
                                state["current_tip"] : state["current_tip"] + CHANNELS
                            ],
                        )
                        st.reset_state(state, state_file_path, "channel_steps", 0)

                    # The first aspirate command must be set to aspirateMode = 0, otherwise the pipette will not aspirate blowout volume
                    # This doesn't seem to work (VENUS still outputs warning about aspiration mode)

                    if i >= 2:
                        aspirateMode = 1
                    else:
                        aspirateMode = 0

                    # Aspirate from wells (with mixing)
                    # If there are an odd number of wells left, aspirate and dispense with one channel

                    if stop - i == 1:
                        cmd.aspirate(
                            hammy,
                            [wells[state["current_well"]]],
                            [140],
                            channelVariable=CHANNEL_1,
                            aspirateMode=aspirateMode,
                            liquidClass=ETHANOL_ASPIRATE,
                            mixCycles=3,
                            mixVolume=50.0,
                        )
                        st.update_state(
                            state, state_file_path, "current_well", stop - i
                        )

                    else:
                        cmd.aspirate(
                            hammy,
                            wells[
                                state["current_well"] : state["current_well"] + CHANNELS
                            ],
                            [140],
                            aspirateMode=aspirateMode,
                            liquidClass=ETHANOL_ASPIRATE,
                            mixCycles=3,
                            mixVolume=50.0,
                        )
                        st.update_state(
                            state, state_file_path, "current_well", CHANNELS
                        )

                    st.update_state(state, state_file_path, "channel_steps", 1)

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

            if state["active_plate"]:
                # Eject tips to current position in active rack
                # No need to change tips between ethanol removal and media removal steps

                cmd.tip_eject(
                    hammy, tips[state["current_tip"] : state["current_tip"] + CHANNELS]
                )

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

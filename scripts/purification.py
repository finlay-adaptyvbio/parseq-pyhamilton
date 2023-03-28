import logging, math, time

import commands as cmd
import deck as dk
import state as st
import helpers as hp

from pyhamilton import (
    HamiltonInterface,
    Plate96,
    Tip96,
    Reservoir300,
    EppiCarrier24,  # type: ignore
)

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Constants

CHANNELS = 2
TIPS = 96
TUBE_VOLUME = 1500

ETHANOL = "StandardVolume_EtOH_DispenseJet_Empty"


def run(deck: dict, state: dict, state_file_path: str, run_dir_path: str):
    # Pool information and variables

    pools = hp.prompt_int("Pools to purify", 24)
    eppies = [f"P{i}" for i in range(1, pools + 1)]

    ratio = hp.prompt_float("Ratio of beads to sample", 1.8)
    sample = hp.prompt_float("Sample volume (uL)", 150)
    elute_volume = hp.prompt_float("Elution volume (uL)", 50)

    # Calculate volumes required for purification

    logger.debug("Calculating volumes...")

    wash_volume = max(200, sample * (1 + ratio))
    ethanol_tubes = math.ceil(
        wash_volume * 2 * pools / (TUBE_VOLUME - wash_volume * 1.2)
    )

    bead_volume = math.ceil(ratio * sample * pools) + 50
    if bead_volume > TUBE_VOLUME:
        logger.warn(
            f"{hp.color.BOLD}{hp.color.RED}More than {TUBE_VOLUME} uL of beads"
            f" required, you will be prompted to add more beads!{hp.color.END}"
        )
    bead_sample_volume = sample * ratio

    teb_volume = math.ceil(elute_volume * pools) + 100

    # Mixing parameters

    bead_mix_volume = min(bead_volume * 0.5, 250.0)

    # Assign labware to deck positions

    logger.debug("Assigning labware...")

    eppicarrier = dk.get_labware_list(deck, ["C1"], EppiCarrier24)[0]
    source_eppies = [(eppicarrier, i) for i in dk.pos_24_2row_2ch(24)[:pools]]
    dest_eppies = [(eppicarrier, i) for i in dk.pos_24_2row_2ch(24)[:pools]]
    beads = [(eppicarrier, 17)]
    teb = [(eppicarrier, 23)]
    # ethanol = [
    #     (eppicarrier, position) for position in dk.pos_24_2row_2ch(24)[:ethanol_tubes]
    # ]
    # ethanol_tube = [ethanol[state["current_ethanol_tube"]]]

    ethanol_reservoir = dk.get_labware_list(deck, ["C5"], Reservoir300)[0]
    ethanol = [(ethanol_reservoir, i) for i in range(15, 384, 16)]

    frame_rack = dk.get_labware_list(deck, ["A3"], Tip96)[0]
    frame_rack_tips = [(frame_rack, i) for i in range(96)]

    frame_holder = dk.get_labware_list(deck, ["A4"], Tip96)[0]
    # frame_holder_tips = [(frame_holder, i) for i in range(96)]

    # frame_row_tips = [
    #     [(frame_holder, i) for i in range(j, j + 88 + 1, 8)] for j in range(0, 8)
    # ]

    frame_tips = dk.frame_96(frame_holder, [i for i in range(96)])
    frame_row_tips = dk.tip_rack(frame_holder, dk.pos_96_1row()[::-1])

    racks = dk.get_labware_list(deck, ["B1"], Tip96, [4], True)
    rack_tips, rack_virtual = dk.get_labware_list(deck, ["F5"], Tip96, [2])
    tips = [(rack_tips, i) for i in dk.pos_96_2ch(96)]

    mag_plate = dk.get_labware_list(deck, ["D3"], Plate96)[0]
    mag_pools = [(mag_plate, i) for i in dk.pos_96_2row_2ch(stop=pools)]
    mag_pools_row = [(mag_plate, i) for i in dk.pos_96_2row(stop=pools)]
    mag_ft = [(mag_plate, i) for i in dk.pos_96_2row(start=, 48)]
    mag_ft_row = [(mag_plate, i) for i in dk.pos_96_1row(24, 48)]
    mag_wash1 = [(mag_plate, i) for i in dk.pos_96_2row(48, 72)]
    mag_wash1_row = [(mag_plate, i) for i in dk.pos_96_1row(48, 72)]
    mag_wash2 = [(mag_plate, i) for i in dk.pos_96_2row(72, 96)]
    mag_wash2_row = [(mag_plate, i) for i in dk.pos_96_1row(72, 96)]

    no_mag_plate = dk.get_labware_list(deck, ["C3"], Plate96)[0]
    no_mag_pools = [(no_mag_plate, i) for i in dk.pos_96_2row(0, 24)]

    # Tip tracking

    def check_tips():
        if state["current_tip"] >= TIPS:
            logger.debug("Current tip rack is empty, getting new one...")
            cmd.grip_get_tip_rack(hammy, rack_tips)
            cmd.grip_place_tip_rack(hammy, rack_tips, waste=True)
            cmd.grip_get_tip_rack(hammy, racks[state["current_rack"]])
            cmd.grip_place_tip_rack(hammy, rack_virtual)

            st.update_state(state, state_file_path, "current_rack", 1)
            st.reset_state(state, state_file_path, "current_tip", 0)

    # Inform user of labware positions, ask for confirmation after placing labware

    logger.debug("Prompt user for labware placement...")

    hp.place_labware([no_mag_plate], "VWR 96 Well PCR Plate")
    hp.place_labware([rack_tips], "Hamilton NTR 96_300 µL Tip Rack")
    hp.place_labware(racks, "Hamilton NTR 96_300 µL Tip Rack")
    hp.place_labware([eppicarrier], "Eppendorf Carrier 24")

    logger.info(
        f"{hp.color.DARKCYAN}Make sure {hp.color.BOLD}Alpaqua Magnum"
        f" EX{hp.color.END}{hp.color.DARKCYAN} (magnetic plate) is in position"
        f" {hp.color.BOLD}D3{hp.color.END}."
    )

    input(f"Press enter to start method!")

    logger.debug("Starting Hamilton method...")

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton

        cmd.initialize(hammy)

        # Loop over pools as long as there are still pools to process

        while not state["complete"]:
            # # Add beads to 96-well plate
            # # Prompt user to add beads to eppendorf carrier
            # # Always mix beads before adding to 96-well plate

            # st.print_state(state)

            # if not state["add_beads"]:
            #     hp.notify(
            #         f"*User action required:* add {TUBE_VOLUME} uL of beads to"
            #         " eppendorf carrier. "
            #     )
            #     input(
            #         f"{hp.color.BOLD}Add 1 tube filled with {TUBE_VOLUME} uL"
            #         " beads to eppendorf carrier position 23. Press enter to continue:"
            #         f" {hp.color.END  }"
            #     )

            #     st.reset_state(state, state_file_path, "bead_volume", TUBE_VOLUME)

            #     logger.debug("Adding beads to plate...")
            #     logger.debug("Mixing beads before addition...")

            #     cmd.tip_pick_up(hammy, [tips[state["current_tip"]]])
            #     cmd.aspirate(
            #         hammy,
            #         beads,
            #         [0.0],
            #         mixCycles=10,
            #         mixVolume=bead_mix_volume,
            #         liquidHeight=1.0,
            #     )
            #     cmd.dispense(
            #         hammy,
            #         beads,
            #         [0.0],
            #         dispenseMode=9,
            #         liquidHeight=1.0,
            #     )

            #     for i in range(state["current_pool"], pools):
            #         logger.debug(f"Adding beads to well {i + 1}...")

            #         if state["bead_volume"] <= bead_sample_volume * 1.2:
            #             logger.debug("Bead volume limit reached!")
            #             hp.notify(
            #                 f"*User action required:* add {TUBE_VOLUME} uL of beads"
            #                 " to bead tube."
            #             )
            #             input(
            #                 f"{hp.color.BOLD}Refill bead tube with {TUBE_VOLUME} uL of"
            #                 f" beads. Press enter to continue: {hp.color.END}"
            #             )

            #             st.reset_state(
            #                 state, state_file_path, "bead_volume", TUBE_VOLUME
            #             )

            #         cmd.aspirate(
            #             hammy,
            #             beads,
            #             [bead_sample_volume - 10],
            #             mixCycles=5,
            #             mixVolume=bead_sample_volume,
            #             liquidHeight=0.1,
            #         )
            #         cmd.dispense(
            #             hammy,
            #             [no_mag_pools[i]],
            #             [bead_sample_volume],
            #             dispenseMode=9,
            #             liquidHeight=5.0,
            #         )

            #         st.update_state(state, state_file_path, "current_pool", 1)
            #         st.update_state(
            #             state, state_file_path, "bead_volume", -bead_sample_volume
            #         )

            #     cmd.tip_eject(
            #         hammy,
            #         [tips[state["current_tip"]]],
            #         waste=True,
            #     )
            #     st.update_state(state, state_file_path, "current_tip", 1)

            #     st.reset_state(state, state_file_path, "add_beads", 1)
            #     st.reset_state(state, state_file_path, "current_pool", 0)

            # # Add pools to 96-well plate

            if not state["eppi_to_plate"]:
                # logger.debug("Adding pools to 96-well plate...")

                # hp.notify(
                #     f"*User action required:* add {pools} pooled sample tubes to"
                #     " eppendorf carrier."
                # )
                # input(
                #     f"\n{hp.color.BOLD}Remove beads from eppendorf carrier and add"
                #     f" {pools} pooled sample tubes. Press enter to continue:"
                #     f" {hp.color.END}"
                # )

                # hp.place_eppies("2 mL Eppendorf", eppies)

                # for i in range(state["current_pool"], pools, CHANNELS):
                #     logger.debug(
                #         f"Adding pools {i + 1, i + CHANNELS} to magnetic plate..."
                #     )

                #     check_tips()

                #     cmd.tip_pick_up(
                #         hammy,
                #         tips[state["current_tip"] : state["current_tip"] + CHANNELS],
                #     )
                #     cmd.aspirate(
                #         hammy,
                #         [source_eppies[i], source_eppies[i + 1]],
                #         [sample - 10],
                #         mixCycles=3,
                #         mixVolume=200.0,
                #         liquidHeight=3.0,
                #     )
                #     cmd.dispense(
                #         hammy,
                #         [no_mag_pools[i], no_mag_pools[i + 1]],
                #         [sample],
                #         dispenseMode=9,
                #         liquidHeight=5.0,
                #     )
                #     cmd.tip_eject(
                #         hammy,
                #         tips[state["current_tip"] : state["current_tip"] + CHANNELS],
                #         waste=True,
                #     )

                #     st.update_state(state, state_file_path, "current_tip", 1)
                #     st.update_state(state, state_file_path, "current_pool", 1)

                row_frame = (math.ceil(pools / 2), math.floor(pools / 2))
                row_plate = (0, math.ceil(pools / 2))

                for i in range(2):
                    # head_pattern = "1" * row[i] + "0" * (96 - row[i])
                    head_pattern = "1" + "0" * (95)
                    cmd.tip_pick_up_384(
                        hammy,
                        frame_row_tips.get_tips(row_frame[i]),
                        tipMode=1,
                        reducedPatternMode=1,
                        headPatternAsVariable=3,
                        headPatternVariable=head_pattern,
                    )
                    cmd.aspirate_384(
                        hammy,
                        [mag_pools_row[row_plate[i]]],
                        0.0,
                        liquidHeight=0.1,
                        mixCycles=10,
                        mixVolume=50.0,
                    )
                    cmd.dispense_384(
                        hammy,
                        [mag_ft_row[i][row_plate[i]]],
                        0.0,
                        dispenseMode=9,
                        liquidHeight=0.1,
                    )
                    cmd.tip_eject_384(
                        hammy,
                        [frame_row_tips[state["current_frame_row"]][-row_frame[i]]],
                        mode=1,
                    )

                st.reset_state(state, state_file_path, "eppi_to_plate", 1)
                st.reset_state(state, state_file_path, "current_pool", 0)

            # # Incubate at RT for 5 minutes

            # time.sleep(300)

            # # Move plate to magnetic plate

            # if not state["move_for_supernatant"]:
            #     logger.debug("Moving plate to magnetic plate...")

            #     cmd.grip_get(
            #         hammy,
            #         no_mag_plate,
            #         1,
            #         gripWidth=81.0,
            #         gripHeight=9.0,
            #     )
            #     cmd.grip_place(hammy, mag_plate, 1)

            #     st.reset_state(state, state_file_path, "move_beads", 1)

            # # Wait for 1 minute to allow beads to separate

            # time.sleep(60)

            # # Remove supernatant

            # if not state["remove_supernatant"]:
            #     logger.debug("Removing supernatant...")

            #     cycles = math.ceil((sample + bead_sample_volume) / 50)

            #     for i in range(cycles):
            #         logger.debug(f"Removing supernatant from pool {i + 1}...")

            #         check_tips()

            #         cmd.tip_pick_up_384(
            #             hammy,
            #             frame_row_tips[state["current_frame_row"]],
            #         )
            #         cmd.aspirate_384(
            #             hammy,
            #             mag_pools,
            #             50.0,
            #             liquidHeight=0.1,
            #         )
            #         cmd.dispense_384(
            #             hammy,
            #             mag_ft,
            #             50.0,
            #             dispenseMode=9,
            #             liquidHeight=10.0,
            #         )
            #         cmd.tip_eject_384(
            #             hammy,
            #             frame_row_tips[state["current_frame_row"]],
            #             mode=1,
            #         )

            #         st.update_state(state, state_file_path, "current_tip", 1)
            #         st.update_state(state, state_file_path, "current_pool", 1)

            #     st.reset_state(state, state_file_path, "remove_supernatant", 1)
            #     st.reset_state(state, state_file_path, "current_pool", 0)

            # # Wash beads with 70% ethanol from eppendorf carrier
            # # Prompt user to add 70% ethanol tubes to eppendorf carrier

            # if not state["add_wash1"]:
            #     logger.debug("Adding ethanol to pools for wash 1...")

            #     hp.notify(
            #         f"*User action required:* add {ethanol_tube} tubes of 70% ethanol"
            #         " to eppendorf carrier."
            #     )
            #     input(
            #         f"{hp.color.BOLD}Add {ethanol_tubes} tube(s) filled with"
            #         f" {TUBE_VOLUME} uL 70% ethanol to eppendorf carrier. Press"
            #         f" enter to continue: {hp.color.END}"
            #     )

            #     check_tips()

            #     cmd.tip_pick_up(
            #         hammy,
            #         [tips[state["current_tip"]]],
            #     )

            #     for i in range(state["current_pool"], pools):
            #         logger.debug(f"Adding ethanol to pool {i + 1}...")

            #         if state["ethanol_volume"] <= wash_volume * 1.2:
            #             st.update_state(state, state_file_path, "ethanol_tube", 1)
            #             ethanol_tube = [ethanol[state["ethanol_tube"]]]
            #             st.reset_state(state, state_file_path, "ethanol_volume", 0)

            #         cmd.aspirate(
            #             hammy,
            #             ethanol_tube,
            #             [wash_volume],
            #             liquidHeight=1.0,
            #             liquidClass=ETHANOL,
            #         )
            #         cmd.dispense(
            #             hammy,
            #             [mag_pools[i]],
            #             [wash_volume],
            #             dispenseMode=9,
            #             liquidHeight=12.0,
            #             liquidClass=ETHANOL,
            #         )

            #         st.update_state(state, state_file_path, "current_pool", 1)
            #         st.update_state(
            #             state, state_file_path, "ethanol_volume", -wash_volume
            #         )

            #     cmd.tip_eject(
            #         hammy,
            #         [tips[state["current_tip"]]],
            #         waste=True,
            #     )
            #     st.update_state(state, state_file_path, "current_tip", 1)

            #     st.reset_state(state, state_file_path, "add_wash1", 1)
            #     st.reset_state(state, state_file_path, "current_pool", 0)

            # # FIXME: not necessary as removing from all wells > 30 s
            # # Incubate 30 seconds

            # time.sleep(30)

            # # Remove ethanol for wash 1

            # if not state["remove_wash1"]:
            #     logger.debug("Removing ethanol for wash 1...")

            #     for i in range(state["current_pool"], pools):
            #         logger.debug(f"Removing ethanol from pool {i + 1}...")

            #         check_tips()

            #         cmd.tip_pick_up(
            #             hammy,
            #             [tips[state["current_tip"]]],
            #         )
            #         cmd.aspirate(
            #             hammy,
            #             [mag_pools[i]],
            #             [wash_volume],
            #             liquidHeight=0.1,
            #             liquidClass=ETHANOL,
            #         )
            #         cmd.dispense(
            #             hammy,
            #             [mag_wash_1[i]],
            #             [wash_volume],
            #             dispenseMode=9,
            #             liquidHeight=10.0,
            #             liquidClass=ETHANOL,
            #         )
            #         cmd.tip_eject(
            #             hammy,
            #             [tips[state["current_tip"]]],
            #             waste=True,
            #         )

            #         st.update_state(state, state_file_path, "current_tip", 1)
            #         st.update_state(state, state_file_path, "current_pool", 1)

            #     st.reset_state(state, state_file_path, "remove_wash1", 1)
            #     st.reset_state(state, state_file_path, "current_pool", 0)

            # # Wash beads with 70% ethanol from eppendorf carrier

            # if not state["add_wash2"]:
            #     logger.debug("Adding ethanol to pools for wash 2...")

            #     check_tips()

            #     cmd.tip_pick_up(
            #         hammy,
            #         [tips[state["current_tip"]]],
            #     )

            #     for i in range(state["current_pool"], pools):
            #         logger.debug(f"Adding ethanol to pool {i + 1}...")

            #         if state["current_ethanol_step"] >= 8:
            #             st.update_state(
            #                 state, state_file_path, "current_ethanol_tube", 1
            #             )
            #             ethanol_tube = [ethanol[state["current_ethanol_tube"]]]
            #             st.reset_state(
            #                 state, state_file_path, "current_ethanol_step", 0
            #             )

            #         cmd.aspirate(
            #             hammy,
            #             ethanol_tube,
            #             [wash_volume],
            #             liquidHeight=1.0,
            #             liquidClass=ETHANOL,
            #         )
            #         cmd.dispense(
            #             hammy,
            #             [mag_pools[i]],
            #             [wash_volume],
            #             dispenseMode=9,
            #             liquidHeight=12.0,
            #             liquidClass=ETHANOL,
            #         )

            #         st.update_state(state, state_file_path, "current_pool", 1)
            #         st.update_state(state, state_file_path, "current_ethanol_step", 1)

            #     cmd.tip_eject(
            #         hammy,
            #         [tips[state["current_tip"]]],
            #         waste=True,
            #     )
            #     st.update_state(state, state_file_path, "current_tip", 1)

            #     st.reset_state(state, state_file_path, "add_wash2", 1)
            #     st.reset_state(state, state_file_path, "current_pool", 0)

            # # FIXME: not necessary as removing from all wells > 30 s
            # # Incubate 30 seconds

            # time.sleep(30)

            # # Remove ethanol for wash 2

            # if not state["remove_wash2"]:
            #     logger.debug("Removing ethanol for wash 2...")

            #     for i in range(state["current_pool"], pools):
            #         logger.debug(f"Removing ethanol from pool {i + 1}...")

            #         check_tips()

            #         cmd.tip_pick_up(
            #             hammy,
            #             [tips[state["current_tip"]]],
            #         )
            #         cmd.aspirate(
            #             hammy,
            #             [mag_pools[i]],
            #             [wash_volume + 50],
            #             liquidHeight=0.1,
            #             liquidClass=ETHANOL,
            #         )
            #         cmd.dispense(
            #             hammy,
            #             [mag_wash_2[i]],
            #             [wash_volume + 50],
            #             dispenseMode=9,
            #             liquidHeight=10.0,
            #             liquidClass=ETHANOL,
            #         )
            #         cmd.tip_eject(
            #             hammy,
            #             [tips[state["current_tip"]]],
            #             waste=True,
            #         )

            #         st.update_state(state, state_file_path, "current_tip", 1)
            #         st.update_state(state, state_file_path, "current_pool", 1)

            #     st.reset_state(state, state_file_path, "remove_wash2", 1)
            #     st.reset_state(state, state_file_path, "current_pool", 0)

            # # Move plate away from magnet

            # if not state["move_for_dry"]:
            #     logger.debug("Moving plate away from magnet...")

            #     cmd.grip_get(
            #         hammy,
            #         mag_plate,
            #         1,
            #         gripWidth=81.0,
            #         gripHeight=9.0,
            #     )
            #     cmd.grip_place(hammy, no_mag_plate, 1)

            #     st.reset_state(state, state_file_path, "move_pure", 1)

            # # Dry beads for 5-10 minutes

            # time.sleep(300)

            # # Add 21 uL of elution buffer to each pool
            # input(
            #     f"{hp.color.BOLD}Add 1 tube filled with {teb_volume} uL TE Buffer"
            #     " to eppendorf carrier position 24. Press enter to"
            #     f" continue: {hp.color.END  }"
            # )

            # if not state["add_buffer"]:
            #     logger.debug("Adding buffer to pools...")

            #     for i in range(state["current_pool"], pools):
            #         logger.debug(f"Adding buffer to pool {i + 1}...")

            #         check_tips()

            #         cmd.tip_pick_up(
            #             hammy,
            #             [tips[state["current_tip"]]],
            #         )
            #         cmd.aspirate(
            #             hammy,
            #             teb,
            #             [elute_volume],
            #             liquidHeight=1.0,
            #         )
            #         cmd.dispense(
            #             hammy,
            #             [no_mag_pools[i]],
            #             [elute_volume],
            #             dispenseMode=9,
            #             liquidHeight=2.0,
            #         )
            #         cmd.aspirate(
            #             hammy,
            #             [no_mag_pools[i]],
            #             [0],
            #             liquidHeight=0.1,
            #             mixCycles=10,
            #             mixVolume=elute_volume * 0.5,
            #         )

            #         cmd.tip_eject(
            #             hammy,
            #             [tips[state["current_tip"]]],
            #             waste=True,
            #         )

            #         st.update_state(state, state_file_path, "current_tip", 1)
            #         st.update_state(state, state_file_path, "current_pool", 1)

            #     st.reset_state(state, state_file_path, "add_buffer", 1)
            #     st.reset_state(state, state_file_path, "current_pool", 0)

            # # Incubate 1 minute

            # time.sleep(60)

            # # Move plate back to magnet

            # if not state["move_for_elute"]:
            #     logger.debug("Moving plate back to magnet...")

            #     cmd.grip_get(
            #         hammy,
            #         no_mag_plate,
            #         1,
            #         gripWidth=81.0,
            #         gripHeight=9.0,
            #     )
            #     cmd.grip_place(hammy, mag_plate, 1)

            #     st.reset_state(state, state_file_path, "move_to_elute", 1)

            # # Incubate 1 minute

            # time.sleep(60)

            # # Store purified samples in low volume sample tubes
            # # Prompt user to add sample tubes to eppendorf carrier

            # input(
            #     f"{hp.color.BOLD}Add {pools} sample collection tubes to eppendorf"
            #     f" carrier. Press enter to continue: {hp.color.END  }"
            # )

            # if not state["store_samples"]:
            #     logger.debug("Storing purified samples...")

            #     for i in range(state["current_pool"], pools):
            #         logger.debug(f"Storing sample {i + 1}...")

            #         check_tips()

            #         cmd.tip_pick_up(
            #             hammy,
            #             [tips[state["current_tip"]]],
            #         )
            #         cmd.aspirate(
            #             hammy,
            #             [mag_pools[i]],
            #             [elute_volume - 5],
            #             liquidHeight=0.1,
            #         )
            #         cmd.dispense(
            #             hammy,
            #             [dest_eppies[i]],
            #             [elute_volume],
            #             dispenseMode=9,
            #             liquidHeight=23.0,
            #         )
            #         cmd.tip_eject(
            #             hammy,
            #             [tips[state["current_tip"]]],
            #             waste=True,
            #         )

            #         st.update_state(state, state_file_path, "current_tip", 1)
            #         st.update_state(state, state_file_path, "current_pool", 1)

            #     st.reset_state(state, state_file_path, "store_samples", 1)
            #     st.reset_state(state, state_file_path, "current_pool", 0)

            st.reset_state(state, state_file_path, "complete", 1)

        cmd.grip_eject(hammy)

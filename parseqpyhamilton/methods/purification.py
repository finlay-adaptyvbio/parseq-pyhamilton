import os, logging, math, time, shelve

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
ETHANOL = "StandardVolume_EtOH_DispenseJet_Empty"
MIX_300 = "StandardVolume_Water_DispenseSurface_Empty"
ALIQUOT_300 = "StandardVolume_Water_DispenseJet_Part"


def run(
    shelf: shelve.Shelf[list[dict[str, list]]],
    state: dict,
    run_dir_path: str,
):
    # File paths
    state_file_path = os.path.join(run_dir_path, "purification.json")

    # Pool information and variables
    pools = hp.prompt_int("Pools to purify", 24)
    bead_ratio = 1.0  # hp.prompt_float("Ratio of beads to sample", 1.8)
    sample_volume = 75.0  # hp.prompt_float("Sample volume (uL)", 150)
    elute_volume = 20.0  # hp.prompt_float("Elution volume (uL)", 50)

    # Calculate volumes required for purification
    wash_volume = max(200, sample_volume * (1 + bead_ratio))
    teb_volume = math.ceil(elute_volume * pools) * 1.2
    bead_volume = sample_volume * bead_ratio

    # Calculate number of tips required
    tips = math.ceil((pools * 6 + 3) / 96) * 96

    # Labware aliases
    carrier = shelf["C"][0]["frame"][0]

    tips_96in384_50 = shelf["A"][2]["frame"][0]
    tips_holder_96in384_50 = shelf["A"][3]["frame"][0]
    tips_96_300 = shelf["F"][4]["frame"][0]

    racks_384_50 = shelf["B"][0]["frame"]
    racks_96_300 = shelf["B"][1]["frame"]

    magnet = shelf["D"][2]["frame"][0]
    plate = shelf["C"][2]["frame"][0]

    # Plate indexes and layout
    rows = 8
    columns = min(1, math.ceil(pools / rows))
    sample_index = [i for i in lw.pos_row_96(pools)]
    supernatant_index = [i for i in lw.pos_row_96(pools, pools)]
    wash1_index = [i for i in lw.pos_row_96(pools, pools * 2)]
    wash2_index = [i for i in lw.pos_row_96(pools, pools * 3)]
    ethanol_index = [
        lw.int_to_str_384(i) for i in lw.pos_96_in_384(1)[: rows * columns]
    ]

    # Sample tube df and static positions
    carrier.fill([i for i in lw.pos_row_24(pools)])
    plate.fill(sample_index)
    beads = carrier.static(["C6"])
    teb = carrier.static(["D6"])
    ethanol = shelf["C"][4]["frame"][0].static(ethanol_index)

    # Mixing parameters
    bead_mix_volume = min(bead_volume * 0.5, 300.0)

    # Helper functions
    def mix_beads():
        cmd.tip_pick_up(hammy, tips_96_300.ch2(1))
        cmd.aspirate(
            hammy,
            beads,
            [0.0],
            liquidClass=MIX_300,
            mixCycles=10,
            mixVolume=bead_mix_volume,
        )
        cmd.dispense(hammy, beads, [0.0], liquidClass=MIX_300)

    def check_tip_holder():
        if tips_holder_96in384_50.total() == 0:
            cmd.tip_pick_up_384(hammy, tips_96in384_50.full())
            cmd.tip_eject_384(hammy, tips_holder_96in384_50.full())
        tips_holder_96in384_50.reset()

    # Start method!
    input(f"Press enter to start method!")

    # Main script starts here
    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton
        cmd.initialize(hammy)

        # Load tips into column holder
        tip_column = hp.prompt_int("Current tip column in holder (0 for new rack)", 12)

        if tip_column > 0:
            tips_holder_96in384_50.fill(lw.pos_row_96(rows * tip_column))
        elif tip_column == 0:
            cmd.tip_pick_up_384(hammy, tips_96in384_50.full())
            cmd.tip_eject_384(hammy, tips_holder_96in384_50.full())
        else:
            logger.warning("Invalid tip column number!")

        # Loop over pools as long as there are still pools to process
        while not all(v == 1 for v in state.values()):
            # Add beads to 96-well plate
            if not state["add_beads"]:
                # Prompt user to add beads to carrier
                input(f"Add bead tube to carrier in position C6.")

                mix_beads()

                # Loop over wells, aspirating max bead volume and dispensing consecutively into plate
                while plate.total() > 0:
                    # Max amount of consecutive dispenses
                    cycles = min(math.floor(300 / (bead_volume * 1.2)), plate.total())
                    cmd.aspirate(
                        hammy,
                        beads,
                        [bead_volume * cycles * 1.2],
                        liquidClass=ALIQUOT_300,
                    )
                    for _ in range(cycles):
                        cmd.dispense(
                            hammy, plate.ch2(1), [bead_volume], liquidClass=ALIQUOT_300
                        )
                    cmd.dispense(
                        hammy, beads, [bead_volume * cycles * 0.2], dispenseMode=9
                    )
                cmd.tip_eject(hammy, waste=True)

                plate.reset()
                st.set_state(state, state_file_path, "add_beads", 1)

            # Add samples to 96-well plate
            if not state["add_samples"]:
                input(f"Add sample tubes to carrier in positions: {sample_index}.")

                while carrier.total() > 0:
                    channels = min(carrier.total(), 2)
                    cmd.tip_pick_up(hammy, tips_96_300.ch2(channels))
                    cmd.aspirate(
                        hammy,
                        carrier.ch2(channels),
                        [sample_volume],
                        mixCycles=3,
                        mixVolume=100.0,
                        liquidHeight=3.0,
                    )
                    cmd.dispense(hammy, plate.ch2(channels), [sample_volume])
                    cmd.tip_eject(hammy, waste=True)

                plate.reset()
                carrier.reset()
                st.set_state(state, state_file_path, "add_samples", 1)

            # Mix beads and samples
            if not state["mix_beads"]:
                check_tip_holder()

                cmd.tip_pick_up_384(hammy, tips_holder_96in384_50.mph384(8, columns))
                cmd.aspirate_384(
                    hammy,
                    plate.static(sample_index),
                    0.0,
                    liquidHeight=0.1,
                    mixCycles=10,
                    mixVolume=50.0,
                )
                cmd.dispense_384(
                    hammy,
                    plate.static(sample_index),
                    0.0,
                    liquidHeight=0.1,
                    dispenseMode=9,
                )
                cmd.tip_eject_384(hammy, mode=2)

                st.set_state(state, state_file_path, "mix_beads", 1)

            # Incubate at RT for 2 minutes
            time.sleep(60 * 2)

            # Move plate to magnetic plate
            if not state["move_beads"]:
                cmd.grip_get(hammy, plate.plate, gripWidth=81.0)
                cmd.grip_place(hammy, magnet.plate)

                st.set_state(state, state_file_path, "move_beads", 1)

            # Wait for 1 minute to allow beads to separate
            time.sleep(60)

            # Remove supernatant
            if not state["remove_supernatant"]:
                check_tip_holder()

                cycles = math.ceil((sample_volume + bead_volume) / 50)

                cmd.tip_pick_up_384(hammy, tips_holder_96in384_50.mph384(rows, columns))
                for _ in range(cycles):
                    cmd.aspirate_384(hammy, magnet.static(sample_index), 50.0)
                    cmd.dispense_384(hammy, magnet.static(supernatant_index), 50.0)
                cmd.tip_eject_384(hammy, mode=2)

                st.set_state(state, state_file_path, "remove_supernatant", 1)

            # Wash beads with 70% ethanol
            if not state["wash1"]:
                check_tip_holder()

                cycles = math.ceil(wash_volume / 50)

                # Add ethanol
                cmd.tip_pick_up_384(hammy, tips_holder_96in384_50.mph384(rows, columns))
                for _ in range(cycles):
                    cmd.aspirate_384(hammy, ethanol, 50.0)
                    cmd.dispense_384(hammy, magnet.static(sample_index), 50.0)

                # Incubate 30 seconds
                time.sleep(30)

                # Remove ethanol
                for _ in range(cycles):
                    cmd.aspirate_384(hammy, magnet.static(sample_index), 50.0)
                    cmd.dispense_384(hammy, magnet.static(wash1_index), 50.0)
                cmd.tip_eject_384(hammy, mode=2)

                st.set_state(state, state_file_path, "wash1", 1)

            # Wash beads with 70% ethanol
            if not state["wash2"]:
                check_tip_holder()

                cycles = math.ceil(wash_volume / 50)

                # Add ethanol
                cmd.tip_pick_up_384(hammy, tips_holder_96in384_50.mph384(rows, columns))
                for _ in range(cycles):
                    cmd.aspirate_384(hammy, ethanol, 50.0)
                    cmd.dispense_384(hammy, magnet.static(sample_index), 50.0)

                # Incubate 30 seconds
                time.sleep(30)

                # Remove ethanol
                for _ in range(cycles):
                    cmd.aspirate_384(hammy, magnet.static(sample_index), 50.0)
                    cmd.dispense_384(hammy, magnet.static(wash1_index), 50.0)
                cmd.tip_eject_384(hammy, mode=2)

                st.set_state(state, state_file_path, "wash2", 1)

            # Move plate away from magnet
            if not state["move_wash"]:
                cmd.grip_get(hammy, magnet.plate, gripWidth=81.0)
                cmd.grip_place(hammy, plate.plate, 1)

                st.set_state(state, state_file_path, "move_wash", 1)

            # Dry beads for 2 minutes
            time.sleep(60 * 2)

            # Add elution buffer to sample wells
            if not state["add_buffer"]:
                # Prompt user to add buffer to carrier
                input(f"Add buffer tube to carrier in position D6.")

                cmd.tip_pick_up(hammy, tips_96_300.ch2(1))
                # Loop over wells, aspirating max bead volume and dispensing consecutively
                while plate.total() > 0:
                    # Max amount of consecutive dispenses
                    cycles = min(math.floor(300 / (elute_volume * 1.2)), plate.total())
                    cmd.aspirate(
                        hammy,
                        teb,
                        [elute_volume * cycles * 1.2],
                        liquidClass=ALIQUOT_300,
                    )
                    for _ in range(cycles):
                        cmd.dispense(
                            hammy, teb, [elute_volume], liquidClass=ALIQUOT_300
                        )
                    cmd.dispense(
                        hammy, teb, [elute_volume * cycles * 0.2], dispenseMode=9
                    )
                cmd.tip_eject(hammy, waste=True)

                plate.reset()
                st.set_state(state, state_file_path, "add_buffer", 1)

            if not state["mix_buffer"]:
                check_tip_holder()

                cmd.tip_pick_up_384(hammy, tips_holder_96in384_50.mph384(rows, columns))
                cmd.aspirate_384(
                    hammy,
                    plate.static(sample_index),
                    0.0,
                    liquidHeight=0.1,
                    mixCycles=10,
                    mixVolume=10.0,
                )
                cmd.tip_eject_384(hammy, mode=2)

                st.set_state(state, state_file_path, "mix_buffer", 1)

            # Incubate 1 minute
            time.sleep(60)

            # Move plate back to magnet
            if not state["move_elute"]:
                cmd.grip_get(hammy, plate.plate, gripWidth=81.0)
                cmd.grip_place(hammy, magnet.plate)

                st.set_state(state, state_file_path, "move_elute", 1)

            # Incubate 1 minute
            time.sleep(60)

            # Store purified samples in low volume sample tubes
            if not state["elute_samples"]:
                # Prompt user to add sample tubes to eppendorf carrier
                input(f"Add sample tubes to carrier in positions: {sample_index}.")

                while plate.total() > 0:
                    channels = min(carrier.total(), 2)
                    cmd.tip_pick_up(hammy, tips_96_300.ch2(channels))
                    cmd.aspirate(hammy, plate.ch2(channels), [elute_volume])
                    cmd.dispense(hammy, carrier.ch2(channels), [elute_volume])
                    cmd.tip_eject(hammy, waste=True)

                st.set_state(state, state_file_path, "elute_samples", 1)

        cmd.grip_eject(hammy)

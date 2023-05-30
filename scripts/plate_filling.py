import os, logging, shelve, math

import commands as cmd
import deck as dk
import helpers as hp
import labware as lw
import state as st

from pyhamilton import HamiltonInterface

# Logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def run(
    shelf: shelve.Shelf[list[dict[str, list]]],
    state: dict,
    run_dir_path: str,
):
    # File paths
    state_file_path = os.path.join(run_dir_path, "plate_filling_state.json")

    # Get plate and volume info from prompt
    plates = hp.prompt_int("Plates to fill", 18)
    volume = hp.prompt_int("Volume to add", 100)

    cycles = min(math.ceil(volume / 50), 1)

    volume = volume / cycles
    reservoir_volume = volume * plates * 384 / 1000 * 1.2

    if reservoir_volume > 300:
        logger.warn(
            f"Required volume {reservoir_volume} mL is more than max reservoir"
            " capacity."
        )
        logger.info("Make sure to fill reservoir as method advances.")
        logger.info("Fill reservoir with at least 300 mL.")
    else:
        logger.info(f"Fill reservoir with at least {reservoir_volume} mL.")

    # Delete unused labware
    for p in ["E1", "E2", "E3", "F1", "F2", "F3"]:
        dk.delete_lids(shelf, p)

    pos = [("E1", "F1"), ("E2", "F2"), ("E3", "F3")]
    remove = len(pos) * 6 - plates
    for t in pos[::-1]:
        n = min(remove, 6)
        dk.delete_unused(shelf, t[0], n)
        dk.delete_unused(shelf, t[1], n)
        remove -= n

    # Labware aliases
    bact_plates = [l for i in range(len(pos)) for l in shelf["F"][i]["frame"]]
    bact_plates_done = [l for i in range(len(pos)) for l in shelf["E"][i]["frame"]]

    active_lid, active_plate = shelf["E"][4]["frame"]
    tmp_lid = shelf["E"][3]["frame"][0]

    reservoir = shelf["C"][4]["frame"][0].full()
    tips = shelf["B"][4]["frame"][0].full()

    # Main script starts here
    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton
        cmd.initialize(hammy)

        # Pick up tips
        cmd.tip_pick_up_384(hammy, tips)

        # Loop over plates
        while bact_plates:
            # Get next bact plate
            if not state["active_plate"]:
                cmd.grip_get(hammy, bact_plates[-1].plate, gripWidth=82.0)
                cmd.grip_place(hammy, active_plate.plate)
                cmd.grip_get(
                    hammy, active_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0
                )
                cmd.grip_place(hammy, tmp_lid.lid, mode=1)

                dk.delete_labware(shelf, bact_plates.pop().plate)
                st.reset_state(state, state_file_path, "media", 0)
                st.reset_state(state, state_file_path, "active_plate", 1)

            # Add media to bact plate
            if not state["media"]:
                for _ in range(cycles):
                    cmd.aspirate_384(hammy, reservoir, volume, liquidHeight=2.0)
                    cmd.dispense_384(
                        hammy,
                        active_plate.full(),
                        volume,
                        liquidHeight=11.0,
                        dispenseMode=9,
                    )

                st.reset_state(state, state_file_path, "media", 1)

            # Remove filled plate
            if state["active_bact_plate"]:
                cmd.grip_get(hammy, tmp_lid.lid, mode=1, gripWidth=85.2, gripHeight=5.0)
                cmd.grip_place(hammy, active_lid.lid, mode=1)
                cmd.grip_get(hammy, active_plate.plate, gripWidth=82.0)
                cmd.grip_place(hammy, bact_plates_done[0].plate)

                dk.delete_labware(shelf, bact_plates_done.pop(0).plate)
                st.reset_state(state, state_file_path, "active_bact_plate", 0)

        # Cleanup instrument
        cmd.tip_eject_384(hammy, tips, mode=2)
        cmd.grip_eject(hammy)

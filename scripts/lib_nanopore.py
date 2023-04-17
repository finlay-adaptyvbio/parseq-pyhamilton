import logging, math, time, os, csv
import pandas as pd

import commands as cmd
import deck as dk
import state as st
import helpers as hp
import labware as lw

from pyhamilton import (
    HamiltonInterface,
    Plate96,
    Tip96,
    EppiCarrier24,  # type: ignore
)

# Logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Constants

TIPS = 96
TUBE_VOLUME = 1800

ETHANOL = "StandardVolume_EtOH_DispenseJet_Empty"


def run(deck: dict, state: dict, state_file_path: str, run_dir_path: str):
    # Sample info

    fragment_size = hp.prompt_int("Fragment size (bp)", 1000)

    # Concentrations and normalization calculations

    sample_concentrations_path = os.path.join(run_dir_path, "sample_concentrations.csv")

    sample_concentrations = pd.read_csv(
        sample_concentrations_path, names=["Sample", "C [ng/uL]"]
    )
    sample_concentrations["bp"] = fragment_size
    sample_concentrations["MW [Da]"] = sample_concentrations["bp"] * 617.96 + 36.04
    sample_concentrations["C [nM]"] = (
        sample_concentrations["C [ng/uL]"] / sample_concentrations["MW [Da]"] * 1e6
    )
    sample_concentrations["moles [fmol]"] = 200  # TODO: User input
    sample_concentrations["Sample V [uL]"] = (
        sample_concentrations["moles [fmol]"] / sample_concentrations["C [nM]"]
    )
    sample_concentrations["Water V [uL]"] = (
        12.5 - sample_concentrations["Sample V [uL]"]
    )

    # Volume calculations

    n_samples = sample_concentrations["Sample"].count()
    sample_volumes = sample_concentrations["Sample V [uL]"].tolist()
    water_volumes = sample_concentrations["Water V [uL]"].tolist()
    water_volume = [float(sum(water_volumes))]
    n_ethanol_tubes = int((math.ceil(n_samples * 300 / TUBE_VOLUME) + 1) / 2.0 * 2)
    edta_volume = 2 * n_samples
    bead_volume_end_prep = 15 * n_samples
    bead_volume_barcode = 8 * n_samples
    bead_volume_ligation = 20

    # Assign labware to deck positions

    carrier = lw.carrier_24(deck)
    plate = lw.plate_96(deck, "C3")
    mag = lw.plate_96(deck, "D3")
    tips_50 = lw.tip_96(deck, "F5")
    tips_300 = lw.tip_96(deck, "B1")

    # Reagents & samples

    samples = carrier.tubes([t for t in lw.pos_column_row_24(n_samples)])
    ethanol = carrier.tubes([t for t in lw.pos_column_row_24(n_ethanol_tubes)])

    water = carrier.tubes(["A4"])
    beads = carrier.tubes(["B4"])
    edta = carrier.tubes(["C4"])
    end_prep_mm = carrier.tubes(["D4"])
    blunt_ta_ligase_mm = carrier.tubes(["A5"])
    adapter_mm = carrier.tubes(["B5"])
    quick_t4_ligase_enzyme = carrier.tubes(["C5"])
    quick_t4_ligase_buffer = carrier.tubes(["D5"])
    elution_buffer = carrier.tubes(["A6"])
    fragment_buffer = carrier.tubes(["B6"])

    # Inform user of labware positions, ask for confirmation after placing labware

    hp.place_labware([no_mag_plate], "VWR 96 Well PCR Plate")
    hp.place_labware([rack_tips], "Hamilton NTR 96_300 µL Tip Rack")
    hp.place_labware(racks, "Hamilton NTR 96_300 µL Tip Rack")
    hp.place_labware([eppicarrier], "Eppendorf Carrier 24")

    logger.info(f"Make sure Alpaqua Magnum EX (magnetic plate) is in position D3.")

    input(f"Press enter to start method!")

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton

        cmd.initialize(hammy)

        # Main loop

        while not state["complete"]:
            # Normalize samples

            if not state["normalize"]:
                while sample_volumes:
                    v = [sample_volumes.pop(0)]
                    cmd.tip_pick_up(hammy, tips_50.default_tips.get_tips_2ch(1))
                    cmd.aspirate(hammy, samples.get_tubes_2ch(1, remove=True), v)
                    cmd.dispense(
                        hammy, plate.default_wells.get_wells_2ch(1, remove=True), v
                    )
                    cmd.tip_eject(
                        hammy, tips_50.default_tips.get_tips_2ch(1), waste=True
                    )

                plate.default_wells.reset()

                cmd.tip_pick_up(hammy, tips_50.default_tips.get_tips_2ch(1))
                cmd.aspirate(hammy, water.get_tubes_2ch(1), water_volume)

                while water_volumes:
                    v = [water_volumes.pop(0)]
                    cmd.dispense(hammy, plate.default_wells.get_wells_2ch(1), v)

                cmd.tip_eject(hammy, tips_50.default_tips.get_tips_2ch(1), waste=True)

            # Remove samples from carrier & add end prep reagents

            # Add end prep master mix to samples

            # Incubate samples

            # Add beads to samples

            # Incubate samples & mix

            # Move to magnent & remove supernatant

            # Wash samples

            # Dry samples

            # Remove from magnet & add elution buffer

            # Incubate samples

            # Move to magnet & transfer samples to new wells

            # Remove end prep reagents & add barcode reagents to carrier

            # Add barcodes to samples

            # Remove barcode reagents & add remaining reagents to carrier

            # Add ligation master mix to samples

            # Incubate samples

            # Add EDTA to samples

            # Pool samples

            # User takes over from here to finish clean-up

            # Add adapter reagents to pool

            # Incubate pool

            # Add beads to pool

            # Incubate pool

            # Move to magnet & remove supernatant

            # Wash pool with fragment buffer

            # Dry pool

            # Remove from magnet & add elution buffer

            # Incubate pool

            # Move to magnet & transfer pool to final tube

        cmd.grip_eject(hammy)

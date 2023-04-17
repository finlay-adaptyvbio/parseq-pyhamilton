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
ALIQUOT_300 = "StandardVolume_Water_DispenseJet_Part"
EMPTY_50 = "Tip_50ul_Water_DispenseJet_Empty"
ALIQUOT_50 = "Tip_50ul_Water_DispenseJet_Part"
MIX_50 = "Tip_50ul_Water_DispenseSurface_Empty"


def run(deck: dict, state: dict, state_file_path: str, run_dir_path: str):
    # Sample info

    fragment_size = hp.prompt_int("Fragment size (bp)", 1000)

    # Concentrations and normalization calculations

    sample_concentrations_path = os.path.join(
        run_dir_path, "lib_nanopore_concentrations.csv"
    )

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
    n_ethanol_tubes = int((math.ceil(n_samples * 300 / TUBE_VOLUME) + 1) / 2.0 * 2)

    sample_volumes = sample_concentrations["Sample V [uL]"].tolist()
    water_volumes = sample_concentrations["Water V [uL]"].tolist()
    water_volume = [(sum(water_volumes) // 50 + 1) * 50.0]
    end_prep_mm_volumes = [2.5] * n_samples
    end_prep_mm_volume = [(sum(end_prep_mm_volumes) // 5 + 1) * 5.0]
    end_prep_bead_volumes = [15.0] * n_samples
    end_prep_bead_volume = [(sum(end_prep_bead_volumes) // 15 + 1) * 15.0]
    edta_volume = 2 * n_samples
    bead_volume_barcode = 8 * n_samples
    bead_volume_ligation = 20

    # Assign labware to deck positions

    carrier = lw.carrier_24(deck)
    c3 = lw.plate_96(deck, "C3")
    d3 = lw.plate_96(deck, "D3")
    d1 = lw.plate_96(deck, "D1")
    tips_300 = lw.tip_96(deck, "F1")
    tips_50 = lw.tip_96(deck, "F2")
    tips_384_96 = lw.tip_96(deck, "A4")

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

    logger.info(f"Make sure Alpaqua Magnum EX (magnetic plate) is in position D3.")

    input(f"Press enter to start method!")

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton

        cmd.initialize(hammy)

        # Main loop

        while not state["complete"]:
            # Add water for normalization
            if not state["normalize_water"]:
                cmd.tip_pick_up(
                    hammy, tips_300.default_tips.get_tips_2ch(1, remove=False)
                )
                cmd.aspirate(
                    hammy,
                    water.get_tubes_2ch(1),
                    water_volume,
                    liquidClass=ALIQUOT_300,
                )

                while water_volumes:
                    cmd.dispense(
                        hammy,
                        c3.default_wells.get_wells_2ch(1),
                        [water_volumes.pop(0)],
                        liquidClass=ALIQUOT_300,
                    )

                cmd.tip_eject(hammy, tips_300.default_tips.get_tips_2ch(1), waste=False)

                c3.default_wells.reset()

            # Add end prep master mix to water
            if not state["end_prep"]:
                cmd.tip_pick_up(
                    hammy, tips_50.default_tips.get_tips_2ch(1, remove=False)
                )
                cmd.aspirate(
                    hammy,
                    end_prep_mm.get_tubes_2ch(1),
                    end_prep_mm_volume,
                    liquidClass=ALIQUOT_50,
                )
                while end_prep_mm_volumes:
                    cmd.dispense(
                        hammy,
                        c3.default_wells.get_wells_2ch(1),
                        [end_prep_mm_volumes.pop(0)],
                        liquidClass=ALIQUOT_50,
                    )
                cmd.tip_eject(hammy, tips_50.default_tips.get_tips_2ch(1), waste=False)

                c3.default_wells.reset()

            # Remove end prep reagents & add sample tubes to carrier
            hp.notify(
                f"*User action required:* Remove end-prep reagents & add sample tubes"
                f" to carrier."
            )
            input(f"{hp.color.BOLD}Press enter to continue: {hp.color.END}")

            # Add samples to end prep master mix
            if not state["normalize_samples"]:
                while sample_volumes:
                    v = [sample_volumes.pop(0)]
                    cmd.tip_pick_up(
                        hammy, tips_50.default_tips.get_tips_2ch(1, remove=False)
                    )
                    cmd.aspirate(hammy, samples.get_tubes_2ch(1), v, liquidClass=MIX_50)
                    cmd.dispense(
                        hammy,
                        c3.default_wells.get_wells_2ch(1),
                        v,
                        liquidClass=MIX_50,
                        mixCycles=5,
                        mixVolume=7.5,
                    )
                    cmd.tip_eject(
                        hammy, tips_50.default_tips.get_tips_2ch(1), waste=False
                    )

                c3.default_wells.reset()

            # Incubate samples
            hp.notify(
                f"*User action required:* Incubate end-prep plate in thermocycler."
            )
            input(f"{hp.color.BOLD}Press enter to continue: {hp.color.END}")

            # Add beads to samples
            if not state["add_beads"]:
                while end_prep_bead_volumes:
                    v = [end_prep_bead_volumes.pop(0)]
                    cmd.tip_pick_up(
                        hammy, tips_50.default_tips.get_tips_2ch(1, remove=False)
                    )
                    cmd.aspirate(
                        hammy,
                        beads.get_tubes_2ch(1),
                        v,
                        liquidClass=MIX_50,
                    )
                    cmd.dispense(
                        hammy,
                        c3.default_wells.get_wells_2ch(1),
                        v,
                        liquidClass=MIX_50,
                        mixCycles=5,
                        mixVolume=15.0,
                    )
                    cmd.tip_eject(
                        hammy, tips_50.default_tips.get_tips_2ch(1), waste=False
                    )

                c3.default_wells.reset()

            # Incubate samples & mix
            cmd.grip_get(hammy, c3.plate)
            cmd.grip_place(hammy, d1.plate)
            # time.sleep(60 * 3)

            # Move to magnent & remove supernatant
            cmd.grip_get(hammy, d1.plate)
            cmd.grip_place(hammy, d3.plate)

            if not state["end_prep_cleanup_supernatant"]:
                cmd.tip_pick_up_384(
                    hammy, tips_384_96.default_tips.get_tips_384mph(8, 2)
                )
                cmd.aspirate_384(
                    hammy,
                    d3.default_wells.get_wells_384mph(8, 2),
                    30.0,
                )
                cmd.dispense_384(
                    hammy,
                    d3.default_wells.get_wells_384mph(8, 2),
                    30.0,
                )
                cmd.tip_eject_384(hammy, mode=1)

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

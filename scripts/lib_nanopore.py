import logging, math, time, os
import pandas as pd

import commands as cmd
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
CHANNELS = 2
TUBE_VOLUME = 1800

ETHANOL = "StandardVolume_EtOH_DispenseJet_Part"
ALIQUOT_300 = "StandardVolume_Water_DispenseJet_Part"
MIX_300 = "StandardVolume_Water_DispenseSurface_Empty"
EMPTY_50 = "Tip_50ul_Water_DispenseJet_Empty"
ALIQUOT_50 = "Tip_50ul_Water_DispenseJet_Part"
MIX_50 = "Tip_50ul_Water_DispenseSurface_Empty"


def run(shelf: shelve.Shelf, state: dict, state_file_path: str, run_dir_path: str):
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
    sample_concentrations["moles [fmol]"] = 200  # TODO: User # input
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

    # Assign labware to deck positions
    carrier = lw.carrier_24(deck)
    c3 = lw.plate_96(deck, "C3")
    d3 = lw.plate_96(deck, "D3")
    d1 = lw.plate_96(deck, "D1")
    waste = lw.plate_96(deck, "C5")
    tips_300 = lw.tip_96(deck, "F1")
    tips_50 = lw.tip_96(deck, "F2")
    tips_384_96 = lw.tip_96(deck, "A4")

    # Plate layout for samples
    rows = 8
    columns = math.ceil(n_samples / rows)
    rows_last_column = n_samples % rows

    if columns == 1:
        rows = rows_last_column

    # Reagent & sample positions
    samples = carrier.tubes([t for t in lw.pos_row_column_24(n_samples)])
    ethanol = carrier.tubes([t for t in lw.pos_row_column_24(n_ethanol_tubes)])

    c3_end_prep = c3.wells([t for t in lw.pos_row_column_96(rows * columns)])
    d3_end_prep = d3.wells([t for t in lw.pos_row_column_96(rows * columns)])
    c3_barcode = c3.wells(
        [t for t in lw.pos_row_column_96(rows * columns * 2)][rows * columns :]
    )
    d3_barcode = d3.wells(
        [t for t in lw.pos_row_column_96(rows * columns * 2)][rows * columns :]
    )

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
    pool = carrier.tubes(["C6"])

    # Inform user of labware positions, ask for confirmation after placing labware
    logger.info(
        f"{hp.color.PURPLE}{hp.color.BOLD}Make sure Alpaqua Magnum EX (magnetic plate)"
        f" is in position D3.{hp.color.END}"
    )

    # Helper functions
    def mix_beads():
        cmd.tip_pick_up(hammy, tips_300.ch2(1, remove=False))
        cmd.aspirate(
            hammy,
            beads.ch2(1, remove=False),
            [0.0],
            liquidClass=MIX_300,
            mixCycles=10,
            mixVolume=300.0,
        )
        cmd.dispense(hammy, beads.ch2(1, remove=False), [0.0], liquidClass=MIX_300)
        cmd.tip_eject(hammy, tips_300.default.ch2(1), waste=False)

    # Start method!
    input(f"Press enter to start method!")

    with HamiltonInterface(simulate=True) as hammy:
        # Initialize Hamilton
        cmd.initialize(hammy)

        # Add water for normalization
        if not state["end_prep_add_water"]:
            cmd.tip_pick_up(hammy, tips_300.default.ch2(1, remove=False))
            cmd.aspirate(
                hammy,
                water.ch2(1, remove=False),
                water_volume,
                liquidClass=ALIQUOT_300,
                liquidHeight=0.1,
            )

            while water_volumes:
                cmd.dispense(
                    hammy,
                    c3_end_prep.ch2(1),
                    [water_volumes.pop(0)],
                    liquidClass=ALIQUOT_300,
                )

            cmd.tip_eject(hammy, tips_300.default.ch2(1), waste=False)

            c3_end_prep.reset()
            st.update_state(state, state_file_path, "end_prep_add_water", 1)

        # Add end prep master mix to water
        if not state["end_prep_add_mm"]:
            cmd.tip_pick_up(hammy, tips_50.default.ch2(1, remove=False))
            cmd.aspirate(
                hammy,
                end_prep_mm.ch2(1),
                [2.5 * (n_samples + 1)],
                liquidClass=ALIQUOT_50,
                mixCycles=3,
                mixVolume=2.5 * n_samples / 2,
                liquidHeight=0.1,
            )
            for _ in range(n_samples):
                cmd.dispense(
                    hammy,
                    c3_end_prep.ch2(1),
                    [2.5],
                    liquidClass=ALIQUOT_50,
                )
            cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)

            c3_end_prep.reset()

        # Remove end prep reagents & add sample tubes to carrier
        hp.notify(
            f"*User action required:* Remove end-prep reagents & add sample tubes"
            f" to carrier."
        )
        input(f"{hp.color.BOLD}Press enter to continue: {hp.color.END}")

        # Add samples to end prep master mix
        if not state["end_prep_add_samples"]:
            while sample_volumes:
                v = [sample_volumes.pop(0)]
                cmd.tip_pick_up(
                    hammy, tips_50.default.ch2(1, remove=False)
                )
                cmd.aspirate(
                    hammy,
                    samples.ch2(1),
                    v,
                    liquidClass=MIX_50,
                    mixCycles=3,
                    mixVolume=10.0,
                    liquidHeight=0.1,
                )
                cmd.dispense(
                    hammy,
                    c3_end_prep.ch2(1),
                    v,
                    liquidClass=MIX_50,
                    mixCycles=5,
                    mixVolume=7.5,
                    liquidHeight=0.1,
                )
                cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)

            c3_end_prep.reset()

        # Incubate samples & add end-prep clean-up reagents
        hp.notify(
            f"*User action required:* Incubate end-prep plate in thermocycler, "
            f" remove sample tubes, and add end-prep clean-up reagents."
        )
        input(f"{hp.color.BOLD}Press enter to continue: {hp.color.END}")

        # Add beads to samples
        if not state["end_prep_add_beads"]:
            mix_beads()
            for _ in range(n_samples):
                cmd.tip_pick_up(
                    hammy, tips_50.default.ch2(1, remove=False)
                )
                cmd.aspirate(
                    hammy,
                    beads.ch2(1, remove=False),
                    [15.0],
                    liquidClass=MIX_50,
                    mixCycles=3,
                    mixVolume=50.0,
                )
                cmd.dispense(
                    hammy,
                    c3_end_prep.ch2(1),
                    [15.0],
                    liquidClass=MIX_50,
                    mixCycles=5,
                    mixVolume=15.0,
                )
                cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)

            c3_end_prep.reset()

        # Incubate samples & mix
        cmd.grip_get(hammy, c3.plate)
        cmd.grip_place(hammy, d1.plate)
        # time.sleep(60 * 3)

        # Move to magnent & remove supernatant
        cmd.grip_get(hammy, d1.plate)
        cmd.grip_place(hammy, d3.plate)

        if not state["end_prep_cleanup_supernatant"]:
            cmd.tip_pick_up_384(
                hammy, tips_384_96.default.mph384(rows, columns)
            )
            cmd.aspirate_384(
                hammy,
                d3_end_prep.mph384(rows, columns),
                30.0,
                liquidHeight=0.1,
            )
            cmd.dispense_384(
                hammy,
                waste.default_wells.mph384(rows, columns),
                30.0,
                liquidHeight=12.0,
            )
            cmd.tip_eject_384(hammy, mode=1)
            d3_end_prep.reset()

        # Wash samples
        if not state["end_prep_cleanup_wash"]:
            cmd.tip_pick_up(hammy, tips_300.default.ch2(remove=False))
            for j in range(2):
                for i in range(0, n_samples, CHANNELS * 2):
                    if i >= 12:
                        ethanol.ch2()
                    cmd.aspirate(
                        hammy,
                        ethanol.ch2(remove=False),
                        [300.0],
                        liquidClass=ETHANOL,
                    )
                    for _ in range(CHANNELS):
                        cmd.dispense(
                            hammy,
                            d3_end_prep.ch2(),
                            [150.0],
                            liquidClass=ETHANOL,
                            liquidHeight=12.0,
                        )
                d3_end_prep.reset()

                cmd.tip_pick_up_384(
                    hammy,
                    tips_384_96.default.mph384(
                        rows, columns, remove=False
                    ),
                )
                for _ in range(3):
                    cmd.aspirate_384(
                        hammy,
                        d3_end_prep.mph384(rows, columns, remove=False),
                        50.0,
                        liquidHeight=0.1,
                    )
                    cmd.dispense_384(
                        hammy,
                        waste.default_wells.mph384(
                            rows, columns, remove=False
                        ),
                        50.0,
                        liquidHeight=12.0,
                    )
                cmd.tip_eject_384(hammy, mode=j + 1)
                waste.default_wells.mph384(rows, columns)

            tips_384_96.default.mph384(rows, columns)
            cmd.tip_eject(hammy, tips_300.default.ch2(), waste=False)

        # Dry samples
        # time.sleep(30)

        # Elute samples
        if not state["end_prep_cleanup_elute"]:
            cmd.grip_get(hammy, d3.plate)
            cmd.grip_place(hammy, c3.plate)

            cmd.tip_pick_up(hammy, tips_300.default.ch2(1, remove=False))
            cmd.aspirate(
                hammy,
                water.ch2(1),
                [10.0 * (n_samples + 1)],
                liquidClass=ALIQUOT_300,
            )

            for _ in range(n_samples):
                cmd.dispense(
                    hammy,
                    c3_end_prep.ch2(1),
                    [10.0],
                    liquidClass=ALIQUOT_300,
                    liquidHeight=5.0,
                )

            cmd.tip_eject(hammy, tips_300.default.ch2(1), waste=False)

            c3_end_prep.reset()

            # Mix with 384mph
            cmd.tip_pick_up_384(
                hammy, tips_384_96.default.mph384(rows, columns)
            )
            cmd.aspirate_384(
                hammy,
                c3_end_prep.mph384(rows, columns, remove=False),
                0.0,
                mixCycles=5,
                mixVolume=8.0,
                liquidHeight=0.1,
            )
            cmd.tip_eject_384(hammy, mode=1)

            cmd.grip_get(hammy, c3.plate)
            cmd.grip_place(hammy, d3.plate)

            cmd.tip_pick_up_384(
                hammy, tips_384_96.default.mph384(rows, columns)
            )
            cmd.aspirate_384(
                hammy,
                d3_end_prep.mph384(rows, columns),
                7.5,
                liquidHeight=0.1,
            )
            cmd.dispense_384(
                hammy,
                d3_barcode.mph384(rows, columns),
                7.5,
            )
            cmd.tip_eject_384(hammy, mode=1)

            d3_barcode.reset()

        # Incubate samples
        # time.sleep(60 * 2)

        # Remove end prep reagents & add barcode reagents to carrier
        hp.notify(
            f"*User action required:* Remove end-prep clean-up reagents & add"
            f" barcodes to carrier."
        )
        input(f"{hp.color.BOLD}Press enter to continue: {hp.color.END}")

        # Add barcodes to samples
        if not state["barcode_ligation_add_barcodes"]:
            cmd.grip_get(hammy, d3.plate)
            cmd.grip_place(hammy, c3.plate)

            for _ in range(n_samples):
                cmd.tip_pick_up(
                    hammy, tips_50.default.ch2(1, remove=False)
                )
                cmd.aspirate(
                    hammy,
                    samples.ch2(1),
                    [2.5],
                    liquidClass=MIX_50,
                    liquidHeight=0.1,
                )
                cmd.dispense(
                    hammy,
                    c3_barcode.ch2(1),
                    [2.5],
                    liquidClass=MIX_50,
                    mixCycles=5,
                    mixVolume=7.5,
                )
                cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)

            c3_barcode.reset()

        # Remove barcode reagents & add remaining reagents to carrier
        hp.notify(
            f"*User action required:* Remove barcodes & add ligation reagents to"
            f" carrier."
        )
        input(f"{hp.color.BOLD}Press enter to continue: {hp.color.END}")

        # Add ligation master mix to samples
        if not state["barcode_ligation_add_mm"]:
            for _ in range(n_samples):
                cmd.tip_pick_up(
                    hammy, tips_50.default.ch2(1, remove=False)
                )
                cmd.aspirate(
                    hammy,
                    blunt_ta_ligase_mm.ch2(1),
                    [10.0],
                    liquidClass=MIX_50,
                    liquidHeight=0.1,
                )
                cmd.dispense(
                    hammy,
                    c3_barcode.ch2(1),
                    [10.0],
                    liquidClass=MIX_50,
                    mixCycles=5,
                    mixVolume=10.0,
                )
                cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)

            c3_barcode.reset()

        # Incubate samples
        cmd.grip_get(hammy, c3.plate)
        cmd.grip_place(hammy, d1.plate)
        # time.sleep(60 * 20)
        cmd.grip_get(hammy, d1.plate)
        cmd.grip_place(hammy, c3.plate)

        # Add EDTA to samples
        if not state["barcode_ligation_add_edta"]:
            for _ in range(n_samples):
                cmd.tip_pick_up(
                    hammy, tips_50.default.ch2(1, remove=False)
                )
                cmd.aspirate(
                    hammy,
                    edta.ch2(1),
                    [2.0],
                    liquidClass=MIX_50,
                    liquidHeight=0.1,
                )
                cmd.dispense(
                    hammy,
                    c3_barcode.ch2(1),
                    [2.0],
                    liquidClass=MIX_50,
                    mixCycles=5,
                    mixVolume=10.0,
                )
                cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)

            c3_barcode.reset()

        # Pool samples
        if not state["barcode_ligation_pool_samples"]:
            cmd.tip_pick_up(hammy, tips_300.default.ch2(1, remove=False))
            for i in range(n_samples):
                if i == 14:
                    cmd.dispense(
                        hammy,
                        pool.ch2(1, remove=False),
                        [i * 20.0],
                        liquidClass=ALIQUOT_300,
                    )
                cmd.aspirate(
                    hammy,
                    c3_barcode.ch2(1),
                    [10.0],
                    liquidClass=ALIQUOT_300,
                    liquidHeight=0.1,
                )
            cmd.dispense(
                hammy,
                pool.ch2(1, remove=False),
                [(n_samples if n_samples < 14 else n_samples - 14) * 10.0],
                liquidClass=ALIQUOT_300,
            )
            cmd.tip_eject(hammy, tips_300.default.ch2(1), waste=False)

        # Add beads to pool
        if not state["barcode_ligation_add_beads"]:
            mix_beads()
            cmd.tip_pick_up(hammy, tips_300.default.ch2(1, remove=False))
            cmd.aspirate(
                hammy,
                beads.ch2(1, remove=False),
                [n_samples * 8.0],
                liquidHeight=0.1,
            )
            cmd.dispense(
                hammy,
                pool.ch2(1, remove=False),
                [n_samples * 8.0],
            )
            cmd.tip_eject(hammy, tips_300.default.ch2(1), waste=False)

        # User takes over from here to finish clean-up
        hp.notify("*User action required:* Finish clean-up of barcode ligation.")
        input(f"{hp.color.BOLD}Press enter to continue: {hp.color.END}")

        # Add adapter reagents to pool
        if not state["adapter_ligation_add_reagents"]:
            cmd.tip_pick_up(hammy, tips_50.default.ch2(1, remove=False))
            cmd.aspirate(
                hammy,
                adapter_mm.ch2(1, remove=False),
                [5.0],
                liquidClass=MIX_50,
                mixCycles=3,
                mixVolume=5.0,
                liquidHeight=0.1,
            )
            cmd.dispense(
                hammy, d1.default_wells.static(["A12"]), [5.0], liquidClass=MIX_50
            )
            cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)
            cmd.tip_pick_up(hammy, tips_50.default.ch2(1, remove=False))
            cmd.aspirate(
                hammy,
                quick_t4_ligase_buffer.ch2(1, remove=False),
                [10.0],
                liquidClass=MIX_50,
                mixCycles=3,
                mixVolume=10.0,
                liquidHeight=0.1,
            )
            cmd.dispense(
                hammy, d1.default_wells.static(["A12"]), [10.0], liquidClass=MIX_50
            )
            cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)
            cmd.tip_pick_up(hammy, tips_50.default.ch2(1, remove=False))
            cmd.aspirate(
                hammy,
                quick_t4_ligase_enzyme.ch2(1, remove=False),
                [5.0],
                liquidClass=MIX_50,
                mixCycles=3,
                mixVolume=5.0,
                liquidHeight=0.1,
            )
            cmd.dispense(
                hammy,
                d1.default_wells.static(["A12"]),
                [5.0],
                liquidClass=MIX_50,
                mixCycles=3,
                mixVolume=25.0,
            )
            cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)

        # Incubate pool
        # time.sleep(60 * 20)

        # Add beads to pool
        if not state["adapter_ligation_add_beads"]:
            mix_beads()
            cmd.tip_pick_up(hammy, tips_50.default.ch2(1, remove=False))
            cmd.aspirate(
                hammy,
                beads.ch2(1, remove=False),
                [20.0],
                liquidClass=MIX_50,
                liquidHeight=0.1,
            )
            cmd.dispense(
                hammy,
                d1.default_wells.static(["A12"]),
                [20.0],
                liquidClass=MIX_50,
                mixCycles=3,
                mixVolume=50.0,
            )
            cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)

        # Incubate pool
        # time.sleep(60 * 10)

        # Move to magnet & remove supernatant
        if not state["adapter_ligation_cleanup_supernatant"]:
            cmd.grip_get(hammy, d1.plate)
            cmd.grip_place(hammy, d3.plate)
            cmd.tip_pick_up(hammy, tips_50.default.ch2(1, remove=False))
            cmd.aspirate(
                hammy,
                d3.default_wells.static(["A12"]),
                [50.0],
                liquidClass=EMPTY_50,
                liquidHeight=0.1,
            )
            cmd.dispense(
                hammy, d3.default_wells.static(["B12"]), [50.0], liquidClass=EMPTY_50
            )
            cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)

        # Wash pool with fragment buffer
        if not state["adapter_ligation_cleanup_wash"]:
            for _ in range(2):
                cmd.tip_pick_up(
                    hammy, tips_300.default.ch2(1, remove=False)
                )
                cmd.aspirate(
                    hammy,
                    fragment_buffer.ch2(1, remove=False),
                    [125.0],
                    liquidClass=MIX_300,
                    liquidHeight=0.1,
                )
                cmd.dispense(
                    hammy,
                    d3.default_wells.static(["A12"]),
                    [125.0],
                    liquidClass=MIX_300,
                    mixCycles=10,
                    mixVolume=50.0,
                )
                # time.sleep(60)
                cmd.aspirate(hammy, d3.default_wells.static(["A12"]), [150.0])
                cmd.tip_eject(hammy, tips_300.default.ch2(1), waste=False)

        # Dry pool
        # time.sleep(30)

        # Remove from magnet & add elution buffer
        if not state["adapter_ligation_cleanup_elute"]:
            cmd.grip_get(hammy, d3.plate)
            cmd.grip_place(hammy, c3.plate)
            cmd.tip_pick_up(hammy, tips_50.default.ch2(1, remove=False))
            cmd.aspirate(
                hammy,
                elution_buffer.ch2(1, remove=False),
                [15.0],
                liquidClass=MIX_50,
                liquidHeight=0.1,
            )
            cmd.dispense(
                hammy,
                c3.default_wells.static(["A12"]),
                [15.0],
                liquidClass=MIX_50,
                mixCycles=3,
                mixVolume=7.5,
                liquidHeight=0.1,
            )
            cmd.tip_eject(hammy, tips_50.default.ch2(1), waste=False)

        # User takes over from here to finish clean-up
        hp.notify("*User action required:* Finish clean-up of adapter ligation.")

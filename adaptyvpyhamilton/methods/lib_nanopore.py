import os, time, logging, shelve, math
import pandas as pd

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
ETHANOL = "50ulTip_conductive_384COREHead_EtOH_DispenseJet_Part"
ALIQUOT_300 = "StandardVolume_Water_DispenseSurface_Part"
MIX_300 = "StandardVolume_Water_DispenseSurface_Empty"
ALIQUOT_50 = "Tip_50ul_Water_DispenseSurface_Part"
MIX_50 = "Tip_50ul_Water_DispenseSurface_Empty"


def run(
    shelf: shelve.Shelf[list[dict[str, list]]],
    state: dict,
    run_dir_path: str,
):
    # File paths
    state_file_path = os.path.join(run_dir_path, "lib_nanopore.json")
    csv_path = hp.prompt_file_path("Input CSV file (lib_nanopore_concentrations.csv)")

    # Sample info
    sample_moles = hp.prompt_int("Moles per sample (fmol)", 200)

    # Concentrations and normalization calculations
    sample_c = pd.read_csv(csv_path, names=["Sample", "C [ng/uL]", "bp"])
    sample_c["MW [Da]"] = sample_c["bp"] * 617.96 + 36.04
    sample_c["C [nM]"] = sample_c["C [ng/uL]"] / sample_c["MW [Da]"] * 1e6
    sample_c["moles [fmol]"] = sample_moles  # TODO: User # input
    sample_c["Sample V [uL]"] = sample_c["moles [fmol]"] / sample_c["C [nM]"]
    sample_c["Water V [uL]"] = 12.5 - sample_c["Sample V [uL]"]

    # Volume calculations
    samples = sample_c["Sample"].count()

    sample_volumes = sample_c["Sample V [uL]"].tolist()
    water_volumes = sample_c["Water V [uL]"].tolist()
    water_volume = [(sum(water_volumes) // 50 + 1) * 50.0]

    # Assign labware to deck positions
    carrier = shelf["C"][0]["frame"][0]
    c3 = shelf["C"][2]["frame"][0]  # no magnet cooled to 4C
    d3 = shelf["D"][2]["frame"][0]  # magnet
    e4 = shelf["E"][3]["frame"][0]  # no magnet room temperature

    tips_96_300 = shelf["F"][0]["frame"][0]
    tips_96_50 = shelf["F"][1]["frame"][0]
    tips_96in384_50 = shelf["A"][2]["frame"][0]
    tips_holder_96in384_50 = shelf["A"][3]["frame"][0]

    # Plate indexes and layout
    rows = 8
    columns = max(1, math.ceil(samples / rows))
    sample_index = [i for i in lw.pos_row_24(samples)]
    end_prep_index = [i for i in lw.pos_row_96(samples)]
    barcode_index = [i for i in lw.pos_row_96(samples, rows * columns)]
    ethanol_index = [
        lw.int_to_str_384(i) for i in lw.pos_96_in_384(1)[: rows * columns]
    ]
    waste_index = [lw.int_to_str_384(i) for i in lw.pos_96_in_384(1)[: rows * columns]]

    # Initial dfs
    carrier.fill(sample_index)
    c3.fill(end_prep_index)

    # Static positions
    ethanol = shelf["C"][4]["frame"][0].static(ethanol_index)
    waste = shelf["D"][0]["frame"][0].static(waste_index)

    c3_pool = c3.static(["A12"])
    d3_pool = d3.static(["A12"])
    e4_pool = e4.static(["A12"])

    water = carrier.static(["A4"])
    beads = carrier.static(["B4"])
    edta = carrier.static(["C4"])
    end_prep_mm = carrier.static(["D4"])
    blunt_ta_ligase_mm = carrier.static(["A5"])
    adapter_mm = carrier.static(["B5"])
    quick_t4_ligase_enzyme = carrier.static(["C5"])
    quick_t4_ligase_buffer = carrier.static(["D5"])
    elution_buffer = carrier.static(["A6"])
    fragment_buffer = carrier.static(["B6"])
    pool = carrier.static(["C6"])

    # Mixing parameters
    bead_volume = (15 + 8) * samples * 1.2
    bead_mix_volume = min(bead_volume * 0.5, 300.0)

    # Helper functions
    def mix_beads():
        cmd.tip_pick_up(hammy, tips_96_300.ch2(1))
        cmd.aspirate(
            hammy,
            beads,
            [0.0],
            liquidClass=MIX_300,
            liquidHeight=5.0,
            mixCycles=10,
            mixVolume=bead_mix_volume,
        )
        cmd.tip_eject(hammy, waste=True)

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

        # Add tips to tip holder
        cmd.tip_pick_up_384(hammy, tips_96in384_50.full())
        cmd.tip_eject_384(hammy, tips_holder_96in384_50.full())
        tips_holder_96in384_50.reset()

        # Add water for normalization
        if not state["end_prep_add_water"]:
            cmd.tip_pick_up(hammy, tips_96_300.ch2(1))
            cmd.aspirate(
                hammy, water, water_volume, liquidClass=ALIQUOT_300, liquidHeight=2.0
            )

            while c3.total() > 0 and water_volumes:
                cmd.dispense(
                    hammy, c3.ch2(1), [water_volumes.pop(0)], liquidClass=ALIQUOT_300
                )

            cmd.tip_eject(hammy, waste=True)

            c3.reset()
            st.set_state(state, state_file_path, "end_prep_add_water", 1)

        # Add end prep master mix to water
        if not state["end_prep_add_mm"]:
            cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
            cmd.aspirate(
                hammy,
                end_prep_mm,
                [2.5 * samples * 1.2],
                liquidClass=ALIQUOT_50,
                mixCycles=3,
                mixVolume=2.5 * samples / 2,
                liquidHeight=4.0,
            )

            while c3.total() > 0:
                cmd.dispense(hammy, c3.ch2(1), [2.5], liquidClass=ALIQUOT_50)
            cmd.tip_eject(hammy, waste=True)

            c3.reset()
            st.set_state(state, state_file_path, "end_prep_add_mm", 1)

        # Remove end prep reagents & add sample tubes to carrier
        hp.notify(
            f"*User action required:* Remove end-prep reagents & add sample tubes"
            f" to carrier."
        )
        input(f"Press enter to continue: ")

        # Add samples to end prep master mix
        if not state["end_prep_add_samples"]:
            while carrier.total() > 0 and c3.total() > 0:
                cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
                cmd.aspirate(
                    hammy,
                    carrier.ch2(1),
                    [sample_volumes[0]],
                    liquidClass=MIX_50,
                    mixCycles=3,
                    mixVolume=10.0,
                    liquidHeight=23.0,
                )
                cmd.dispense(
                    hammy,
                    c3.ch2(1),
                    [sample_volumes[0]],
                    liquidClass=MIX_50,
                    dispenseMode=9,
                    mixCycles=5,
                    mixVolume=7.5,
                    liquidHeight=0.1,
                )
                cmd.tip_eject(hammy, waste=True)

                del sample_volumes[0]

            c3.reset()
            st.set_state(state, state_file_path, "end_prep_add_samples", 1)

        # Incubate samples & add end-prep clean-up reagents
        hp.notify(
            f"*User action required:* Incubate end-prep plate in thermocycler, "
            f" remove sample tubes, and add end-prep clean-up reagents."
        )
        input(f"Press enter to continue: ")

        # Add beads to samples
        if not state["end_prep_add_beads"]:
            mix_beads()
            while c3.total() > 0:
                cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
                cmd.aspirate(
                    hammy,
                    beads,
                    [15.0],
                    liquidClass=MIX_50,
                    liquidHeight=5.0,
                    mixCycles=3,
                    mixVolume=50.0,
                )
                cmd.dispense(
                    hammy,
                    c3.ch2(1),
                    [15.0],
                    liquidClass=MIX_50,
                    mixCycles=5,
                    mixVolume=15.0,
                )
                cmd.tip_eject(hammy, waste=True)

            c3.reset()

            cmd.grip_get(hammy, c3.plate)
            cmd.grip_place(hammy, e4.plate)

            st.set_state(state, state_file_path, "end_prep_add_beads", 1)

        # Incubate for 3 minutes at room temperature
        time.sleep(60 * 3)

        # Move to magnet & remove supernatant
        if not state["end_prep_cleanup_supernatant"]:
            cmd.grip_get(hammy, e4.plate)
            cmd.grip_place(hammy, d3.plate)

            # Incubate for 3 minutes at room temperature
            time.sleep(60 * 3)

            check_tip_holder()

            cmd.tip_pick_up_384(hammy, tips_holder_96in384_50.mph384(rows, columns))
            cmd.aspirate_384(hammy, d3.static(end_prep_index), 30.0, liquidHeight=0.1)
            cmd.dispense_384(hammy, waste, 30.0, liquidHeight=12.0)
            cmd.tip_eject_384(hammy, mode=2)

            st.set_state(state, state_file_path, "end_prep_cleanup_supernatant", 1)

        # Wash samples
        if not state["end_prep_cleanup_wash"]:
            check_tip_holder()

            for _ in range(2):
                cmd.tip_pick_up_384(hammy, tips_holder_96in384_50.mph384(rows, columns))
                for _ in range(3):
                    cmd.aspirate_384(hammy, ethanol, 50.0, liquidClass=ETHANOL)
                    cmd.dispense_384(
                        hammy,
                        d3.static(end_prep_index),
                        50.0,
                        liquidClass=ETHANOL,
                        liquidHeight=9.0,
                    )

                time.sleep(60)

                for _ in range(3):
                    cmd.aspirate_384(
                        hammy,
                        d3.static(sample_index),
                        50.0,
                        liquidClass=ETHANOL,
                        liquidHeight=0.1,
                    )
                    cmd.dispense_384(hammy, waste, 50.0, liquidClass=ETHANOL)
                cmd.tip_eject_384(hammy, mode=2)

            st.set_state(state, state_file_path, "end_prep_cleanup_wash", 1)

        # Dry samples
        time.sleep(30)

        # Elute samples
        if not state["end_prep_cleanup_elute"]:
            cmd.grip_get(hammy, d3.plate)
            cmd.grip_place(hammy, c3.plate)

            cmd.tip_pick_up(hammy, tips_96_300.ch2(1))
            cmd.aspirate(
                hammy,
                water,
                [10.0 * samples * 1.2],
                liquidClass=ALIQUOT_300,
                liquidHeight=2.0,
            )

            while c3.total() > 0:
                cmd.dispense(
                    hammy,
                    c3.ch2(1),
                    [10.0],
                    liquidClass=ALIQUOT_300,
                    liquidHeight=9.0,
                )

            cmd.tip_eject(hammy, waste=True)

            c3.reset()

            check_tip_holder()

            cmd.tip_pick_up_384(hammy, tips_holder_96in384_50.mph384(rows, columns))
            cmd.aspirate_384(
                hammy,
                c3.static(end_prep_index),
                0.0,
                mixCycles=5,
                mixVolume=8.0,
                liquidHeight=0.1,
            )
            cmd.tip_eject_384(hammy, mode=2)

            hp.notify(
                f"*User action required:* Check if elution buffer is mixed with beads."
            )
            input(f"Press enter to continue: ")

            cmd.grip_get(hammy, c3.plate)
            cmd.grip_place(hammy, d3.plate)

            # Incubate for 2 minutes at room temperature
            time.sleep(60 * 2)

            check_tip_holder()

            cmd.tip_pick_up_384(hammy, tips_holder_96in384_50.mph384(rows, columns))
            cmd.aspirate_384(hammy, d3.static(end_prep_index), 7.5, liquidHeight=0.1)
            cmd.dispense_384(hammy, d3.static(barcode_index), 7.5)
            cmd.tip_eject_384(hammy, mode=2)

            st.set_state(state, state_file_path, "end_prep_cleanup_elute", 1)

        # Remove end prep reagents & add barcode reagents to carrier
        hp.notify(
            f"*User action required:* Remove end-prep clean-up reagents & add"
            f" barcodes to carrier."
        )
        input(f"Press enter to continue: ")

        # Add barcodes to samples
        if not state["barcode_ligation_add_barcodes"]:
            c3.fill(barcode_index)

            cmd.grip_get(hammy, d3.plate)
            cmd.grip_place(hammy, c3.plate)

            while carrier.total() > 0 and c3.total() > 0:
                cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
                cmd.aspirate(
                    hammy,
                    carrier.ch2(1),
                    [2.5],
                    liquidClass=MIX_50,
                    liquidHeight=5.0,
                )
                cmd.dispense(
                    hammy,
                    c3.ch2(1),
                    [2.5],
                    liquidClass=MIX_50,
                    mixCycles=5,
                    mixVolume=7.5,
                )
                cmd.tip_eject(hammy, waste=True)

            carrier.reset()
            c3.reset()
            st.set_state(state, state_file_path, "barcode_ligation_add_barcodes", 1)

        # Remove barcode reagents & add remaining reagents to carrier
        hp.notify(
            f"*User action required:* Remove barcodes & add ligation reagents to"
            f" carrier."
        )
        input(f"Press enter to continue: ")

        # Add ligation master mix to samples
        if not state["barcode_ligation_add_mm"]:
            while c3.total() > 0:
                cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
                cmd.aspirate(
                    hammy,
                    blunt_ta_ligase_mm,
                    [10.0],
                    liquidClass=MIX_50,
                    liquidHeight=2.0,
                )
                cmd.dispense(
                    hammy,
                    c3.ch2(1),
                    [10.0],
                    liquidClass=MIX_50,
                    mixCycles=5,
                    mixVolume=10.0,
                )
                cmd.tip_eject(hammy, waste=True)

            cmd.grip_get(hammy, c3.plate)
            cmd.grip_place(hammy, e4.plate)

            c3.reset()
            st.set_state(state, state_file_path, "barcode_ligation_add_mm", 1)

        # Incubate samples for 20 minutes at room temperature
        time.sleep(60 * 20)

        # Add EDTA to samples
        if not state["barcode_ligation_add_edta"]:
            cmd.grip_get(hammy, e4.plate)
            cmd.grip_place(hammy, c3.plate)

            while c3.total() > 0:
                cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
                cmd.aspirate(hammy, edta, [2.0], liquidClass=MIX_50, liquidHeight=5.0)
                cmd.dispense(
                    hammy,
                    c3.ch2(1),
                    [2.0],
                    liquidClass=MIX_50,
                    mixCycles=5,
                    mixVolume=10.0,
                )
                cmd.tip_eject(hammy, waste=True)

            c3.reset()
            st.set_state(state, state_file_path, "barcode_ligation_add_edta", 1)

        # Pool samples
        if not state["barcode_ligation_pool_samples"]:
            cycles = math.ceil(samples / 14)

            cmd.tip_pick_up(hammy, tips_96_300.ch2(1))
            for _ in range(cycles):
                aspirations = min(14, c3.total())
                cmd.aspirate(hammy, c3.ch2(1), [20.0], liquidHeight=0.1)

                for _ in range(aspirations - 1):
                    cmd.aspirate(
                        hammy, c3.ch2(1), [20.0], liquidHeight=0.1, aspirateMode=1
                    )
                cmd.dispense(hammy, pool, [aspirations * 20.0])
            cmd.tip_eject(hammy, waste=True)

            st.set_state(state, state_file_path, "barcode_ligation_pool_samples", 1)

        # Add beads to pool
        if not state["barcode_ligation_add_beads"]:
            mix_beads()
            cmd.tip_pick_up(hammy, tips_96_300.ch2(1))
            cmd.aspirate(hammy, beads, [samples * 8.0], liquidHeight=5.0)
            cmd.dispense(hammy, pool, [samples * 8.0])
            cmd.tip_eject(hammy, waste=True)

            st.set_state(state, state_file_path, "barcode_ligation_add_beads", 1)

        # User takes over from here to finish clean-up
        hp.notify("*User action required:* Finish clean-up of barcode ligation.")
        input(f"Press enter to continue: ")

        # Add adapter reagents to pool
        if not state["adapter_ligation_add_reagents"]:
            cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
            cmd.aspirate(
                hammy,
                adapter_mm,
                [5.0],
                liquidClass=MIX_50,
                liquidHeight=4.0,
                mixCycles=3,
                mixVolume=5.0,
            )
            cmd.dispense(hammy, e4_pool, [5.0], liquidClass=MIX_50)
            cmd.tip_eject(hammy, waste=True)
            cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
            cmd.aspirate(
                hammy,
                quick_t4_ligase_buffer,
                [10.0],
                liquidClass=MIX_50,
                liquidHeight=4.0,
                mixCycles=3,
                mixVolume=10.0,
            )
            cmd.dispense(hammy, e4_pool, [10.0], liquidClass=MIX_50)
            cmd.tip_eject(hammy, waste=True)
            cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
            cmd.aspirate(
                hammy,
                quick_t4_ligase_enzyme,
                [5.0],
                liquidClass=MIX_50,
                liquidHeight=4.0,
                mixCycles=3,
                mixVolume=5.0,
            )
            cmd.dispense(
                hammy,
                e4_pool,
                [5.0],
                liquidClass=MIX_50,
                mixCycles=3,
                mixVolume=25.0,
            )
            cmd.tip_eject(hammy, waste=True)

            st.set_state(state, state_file_path, "adapter_ligation_add_reagents", 1)

        # Incubate for 20 minutes at room temperature
        time.sleep(60 * 20)

        # Add beads to library
        if not state["adapter_ligation_add_beads"]:
            mix_beads()
            cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
            cmd.aspirate(
                hammy,
                beads,
                [20.0],
                liquidClass=MIX_50,
                liquidHeight=5.0,
            )
            cmd.dispense(
                hammy,
                e4_pool,
                [20.0],
                liquidClass=MIX_50,
                mixCycles=3,
                mixVolume=50.0,
            )
            cmd.tip_eject(hammy, waste=True)

            st.set_state(state, state_file_path, "adapter_ligation_add_beads", 1)

        # Incubate for 10 minutes at room temperature
        time.sleep(60 * 10)

        # Move to magnet & remove supernatant
        if not state["adapter_ligation_cleanup_supernatant"]:
            cmd.grip_get(hammy, e4.plate)
            cmd.grip_place(hammy, d3.plate)

            cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
            cmd.aspirate(
                hammy,
                d3_pool,
                [50.0],
                liquidClass=MIX_50,
                liquidHeight=0.1,
            )
            cmd.dispense(hammy, waste, [50.0], liquidClass=MIX_50)
            cmd.tip_eject(hammy, waste=True)

            st.set_state(
                state, state_file_path, "adapter_ligation_cleanup_supernatant", 1
            )

        # Wash pool with fragment buffer
        if not state["adapter_ligation_cleanup_wash"]:
            for _ in range(2):
                cmd.tip_pick_up(hammy, tips_96_300.ch2(1))
                cmd.aspirate(
                    hammy,
                    fragment_buffer,
                    [125.0],
                    liquidClass=MIX_300,
                )
                cmd.dispense(
                    hammy,
                    d3_pool,
                    [125.0],
                    liquidClass=MIX_300,
                    mixCycles=10,
                    mixVolume=75.0,
                )

                time.sleep(60)

                cmd.aspirate(hammy, d3_pool, [150.0], liquidHeight=0.1)
                cmd.tip_eject(hammy, waste=True)

            st.set_state(state, state_file_path, "adapter_ligation_cleanup_wash", 1)

        # Dry pool
        time.sleep(30)

        # Remove from magnet & add elution buffer
        if not state["adapter_ligation_cleanup_elute"]:
            cmd.grip_get(hammy, d3.plate)
            cmd.grip_place(hammy, c3.plate)

            cmd.tip_pick_up(hammy, tips_96_50.ch2(1))
            cmd.aspirate(
                hammy,
                elution_buffer,
                [15.0],
                liquidClass=MIX_50,
                liquidHeight=5.0,
            )
            cmd.dispense(
                hammy,
                c3_pool,
                [15.0],
                liquidClass=MIX_50,
                mixCycles=3,
                mixVolume=7.5,
            )
            cmd.tip_eject(hammy, waste=True)

            st.set_state(state, state_file_path, "adapter_ligation_cleanup_elute", 1)

        # User takes over from here to finish clean-up
        hp.notify("*User action required:* Finish clean-up of adapter ligation.")

        cmd.grip_eject(hammy)

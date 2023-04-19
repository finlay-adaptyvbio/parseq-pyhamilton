from pyhamilton import HamiltonInterface

import logging, logging.config, math, time, os, csv
import pandas as pd

# import commands as cmd
import deck as dk
import state as st
import helpers as hp
import labware as lw

# Logging settings

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": f"{hp.color.RED}%(levelname)s{hp.color.END} %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "simple",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": "DEBUG", "propagate": True},
    },
}

logging.getLogger("parse").setLevel(logging.WARNING)

logging.config.dictConfig(LOGGING)

logger = logging.getLogger()

layout_path = "C:\\Users\\Adaptyvbio\\Documents\\PyHamilton\\adaptyv-pyhamilton\\layouts\\lib_nanopore.lay"
csv_path = "C:\\Users\\Adaptyvbio\\Downloads\\test.csv"

deck = dk.get_deck(layout_path)

TIPS = 96
TUBE_VOLUME = 1800

ETHANOL = "StandardVolume_EtOH_DispenseJet_Empty"
ALIQUOT_300 = "StandardVolume_Water_DispenseJet_Part"
EMPTY_50 = "Tip_50ul_Water_DispenseJet_Empty"

complete = 0
normalize = 0

if __name__ == "__main__":
    # Sample info

    fragment_size = hp.prompt_int("Fragment size (bp)", 1000)

    # Concentrations and normalization calculations

    sample_concentrations_path = csv_path

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
    water_volume = [(sum(water_volumes) // 50 + 1) * 50.0]
    n_ethanol_tubes = int((math.ceil(n_samples * 300 / TUBE_VOLUME) + 1) / 2.0 * 2)
    edta_volume = 2 * n_samples
    bead_volume_end_prep = 15 * n_samples
    bead_volume_barcode = 8 * n_samples
    bead_volume_ligation = 20

    # Assign labware to deck positions

    carrier = lw.carrier_24(deck)
    c3 = lw.plate_96(deck, "C3")
    d3 = lw.plate_96(deck, "D3")
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

    t = tips_384_96.default_tips.get_tips_384mph(8, 2)
    print(t)


        

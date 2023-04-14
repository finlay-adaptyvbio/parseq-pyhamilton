from pyhamilton import (
    HamiltonInterface,
    Plate96,
    Tip96,
    Reservoir300,  # type: ignore
    EppiCarrier24,  # type: ignore
)

import commands, helpers, deck, labware

import logging, logging.config, time, csv

import pandas as pd

# Logging settings

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": f"{helpers.color.RED}%(levelname)s{helpers.color.END} %(message)s"
        },
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

layout_path = "C:\\Users\\Adaptyvbio\\Documents\\PyHamilton\\adaptyv-pyhamilton\\layouts\\purification.lay"
csv_path = "C:\\Users\\Adaptyvbio\\Downloads\\test.csv"

layout = deck.get_deck(layout_path)

if __name__ == "__main__":
    fragment_size = helpers.prompt_int("Fragment size (bp)", 1000)

    # Concentrations and normalization calculations

    logger.debug("Reading concentrations...")

    sample_concentrations_path = csv_path

    sample_concentrations = pd.read_csv(
        sample_concentrations_path, names=["Sample", "C [ng/uL]"]
    )
    sample_concentrations["bp"] = fragment_size
    sample_concentrations["MW [Da]"] = sample_concentrations["bp"] * 617.96 + 36.04
    sample_concentrations["C [nM]"] = (
        sample_concentrations["C [ng/uL]"] / sample_concentrations["MW [Da]"] * 1e6
    )
    sample_concentrations["moles [fmol]"] = 200
    sample_concentrations["Sample V [uL]"] = (
        sample_concentrations["moles [fmol]"] / sample_concentrations["C [nM]"]
    )
    sample_concentrations["Water V [uL]"] = (
        12.5 - sample_concentrations["Sample V [uL]"]
    )

    print(sample_concentrations)

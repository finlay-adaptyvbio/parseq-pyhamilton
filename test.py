from pyhamilton import (
    HamiltonInterface,
    Plate96,
    Tip96,
    Reservoir300,
    EppiCarrier24,
)

import commands as cmd
import deck as dk
import helpers as hp

import logging, logging.config, time, csv

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

layout_path = "C:\\Users\\Adaptyvbio\\Documents\\PyHamilton\\adaptyv-pyhamilton\\layouts\\purification.lay"
csv_path = (
    "C:\\Users\\Adaptyvbio\\Documents\\PyHamilton\\adaptyv-pyhamilton\\temp\\cherry.csv"
)

with open(csv_path, "r") as f:
    reader = csv.reader(f)
    rows = [row[0].split(" ") for row in reader]
    wells = [row[0].split(".") for row in rows]

l = [well[1] for well in wells]

deck = dk.get_deck(layout_path)

if __name__ == "__main__":
    test_plate = dk.get_labware_list(deck, ["C5"], Reservoir300)[0]
    test_frame = dk.plate_384(
        test_plate,
        l,
    )
    print(test_frame.frame())
    while test_frame.wells() > 0:
        pipet_wells = test_frame.get_wells_2ch()
    print(test_frame.frame())
    test_frame.reset_frame()
    print(test_frame.frame())
    print(test_frame.static_wells(["A1", "A2"]))

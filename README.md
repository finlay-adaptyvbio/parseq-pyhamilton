# Adaptyv-PyHamilton

Source code for automation of PARSEQ pipeline and other protocols developed using [PyHamilton](https://github.com/dgretton/pyhamilton), the python library for Hamilton robots.

## Features

- A state-centric approach to protocol management which allows automatic error recovery and tracking of each step involved in the process
- A CLI handles the local library of protocols, each written as a modular Python script, simplifying the day-to-day running of the pipeline
- Custom labware classes implement physical matrices (ie. a 384-well MTP in 16x24 format) as [Pandas](https://pandas.pydata.org/) DataFrames, enabling efficient sorting of wells for optimised pipetting and automatic tracking of wells and tips during a process
- Commands for operating the 384-channel pipetting head, which PyHamilton lacks
- Unlocking useful actions, such as picking up a subset of tips, prohibited by the proprietary Hamilton software (VENUS)
- Wrappers to simplify common combinations of robot movements into short one-liners
- Extended support for common labware formats
- Notifications via [Slack](https://slack.com/) API when user intervention is required

## Quick start

### main.py

All methods are called from a central script **main.py**. This script accepts CLI arguments as follows:

> main.py _method_ --layout _(optional)_ --log _LEVEL_

User prompts will take care of any other parameters required for a method, for example CSVs for well maps.

VENUS sometimes includes non-existent labware which are parsed by **deck.py** and cause errors in list assigments at runtime. PyHamilton functions to extract labware from layout files also don't always differentiate between stack identifiers and labware identifiers, which causes the same issue.

A new method to clean parsed layout files removes any non-existent labware automatically!

To simulate a run use

> HamiltonInterface(simulate=True)

when running the main loop. This opens a VENUS window where simulation mode can be enabled, otherwise the script is silent (currently just throws an error).

Each script is hardcoded to a layout file included in the **layouts** directory. To use another layout file a flag can be provided when running the main script:
> main.py _method_ --layout _/path/to/layout/file_

Make sure the provided layout file is compatible with the automated labware assigment included in each method!

A default state file from the **states** directory is also hardcoded for each script, allowing error recovery and tracking of method steps.

## PARSEQ pipeline

### Culture plate merging

### bPCR

### Pooling

### DNA bead purification

### Library preparation for NGS

### Cherry-picking

## Other protocols

### Plate filling

### Plate passaging

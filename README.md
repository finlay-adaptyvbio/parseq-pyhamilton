# Adaptyv-PyHamilton

Source code for methods and protocols developed using pyhamilton python library.

## Running protocols

### main.py

All methods are called from a central script **main.py**. This script accepts CLI arguments as follows:

> main.py _method_ --layout _(optional)_ --log _LEVEL_

User prompts will take care of any other parameters required for a method, for example CSVs for well maps.

VENUS sometimes includes non-existent labware which are parsed by **deck.py** and cause errors in list assigments at runtime. PyHamilton functions to extract labware from layout files also don't always differentiate between stack identifiers and labware identifiers, which causes the same issue. ~~Make sure to verify layout file using **layout.py** before running a script.~~

A new method to clean parsed layout files removes any non-existent labware automatically!

To simulate a run use

> HamiltonInterface(simulate=True)

when running the main loop. This opens a VENUS window where simulation mode can be enabled, otherwise the script is silent (currently just throws an error).

Each script is hardcoded to a layout file included in the **layouts** directory. To use another layout file a flag can be provided when running the main script:
> main.py _method_ --layout _/path/to/layout/file_

Make sure the provided layout file is compatible with the automated labware assigment included in each method!

A default state file from the **states** directory is also hardcoded for each script, allowing error recovery and tracking of method steps.

## TODO

- [x] migrate cherry-picking to new format
- [x] automated error recovery
- [x] add more user facing prompts
- [ ] notifications
  - [ ] script exit (fail | success)
  - [ ] capture error msg
- [x] more output/logging
  - [ ] get VENUS log files
  - [ ] save log to file not just stdout
- [ ] comments

## Protocols

### 1. Plate-merging

- emptying and transferring separated into 2 scripts
- requires CSV for wells to empty and wells to transfer
  - sorted_well_map.csv from b.sight script

### 2. PCR

- colony and barcoding pcrs separated into 2 scripts as usually run consecutively not concurrently
- 4 plates max per run
- master mix from 96-well plate as 300 mL reservoir results in significant waste

### 3. Pooling

- 8 plates max per run
- intermediate pooling in 96-well plate

### 4. Cherry-picking

- \> 24 plates max per run
- slight modification of pm_filling.py script
- requires CSV for wells to pick
  - cherry.csv from pNGS analysis

## Scripts

- state management (error recovery and tracking)
- deck & sequence management (layout file parsing)
- wrappers for pyhamilton basic commands
- helper functions (user prompts, csv processing)

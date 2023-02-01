# Adaptyv-PyHamilton

Source code for methods and protocols developed using pyhamilton python library.

## Running protocols

Make sure to verify layout file using **layout.py** before running a script. VENUS sometimes includes non-existent labware which are parsed by **deck.py** and cause errors in list assigments at runtime. PyHamilton functions to extract labware from layout files also don't always differentiate between stack identifiers and labware identifiers, which causes the same issue.

To simulate a run use

> HamiltonInterface(simulate=True)

when running the main loop. This opens a VENUS window where simulation mode can be enabled, otherwise the script is silent (currently just throws an error).

Each script is hardcoded to a layout file included in its subdirectory, to run with an alternative layout the script must be pointed to the corresponding layout file.

## TODO

* migrate cherry-picking to new format
* automated error recovery
* add more user facing prompts
* notifications
* more output/logging
* comments

## Protocols

### 1. Plate-merging

* emptying and transferring separated into 2 scripts
* requires CSVs for wells to empty and wells to transfer

### 2. PCR

* colony and barcoding pcrs separated into 2 scripts as usually run consecutively not concurrently
* 4 plates max per run
* master mix from 96-well plate as 300 mL reservoir results in significant waste

### 3. Pooling

* 8 plates max per run
* intermediate pooling in 96-well plate

### 4. Cherry-picking

* \> 24 plates max per run
* single channel for now

## Scripts

* state management (error recovery) - **WIP**
* layout file parsing (inbuilt pyhamilton functions & VENUS are currently unreliable)
* deck & sequence management
* wrappers for pyhamilton basic commands

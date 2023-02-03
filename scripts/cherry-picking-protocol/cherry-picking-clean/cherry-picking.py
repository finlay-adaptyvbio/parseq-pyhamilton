import json
import math
import os
import helpers as hp
import load
import actions as act
import datetime
import shutil
from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType, Plate384, Tip96, INITIALIZE, GRIP_GET, GRIP_PLACE, GRIP_MOVE, tip_pick_up, tip_eject, aspirate, dispense)

LAYOUT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../cherry_picking_protocol_stacked_tips.lay")
#INPUT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../new_mapping_3.csv")#"test_data","2p_more_than_2_tgt_p.csv")
TMP_DIR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/tmp")
OUT_DIR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/out")
SRC_STACK_LIMIT = 6
TGT_STACK_LIMIT = 6
TIP_STACK_LIMIT = 4
WASTE_SEQUENCE = "Waste"
LIQUID_CLASS = "Tip_50ul_96COREHead1000ul_Water_DispenseJet_PartEmpty"

new_mapping = {} # New well: Old well

state = {
    "treated_src_plates_count": 0, # Number of source plates that have been treated (everything has been extracted from them)
    "treated_tgt_plates_count":0, # Number of target plates that have been treated (they have been filled as much as possible)
    "treated_tip_racks_count":-1, # -1 because we start with an additional tip rack on the active tips position 
    "gripped_plate":{
        "current_plate": None,
        "current_lid": False
    },
    "active_src": {
        "plate_seq": "Gre_384_Sq_0006",
        "lid_seq": "Gre_384_Sq_0006_lid",
        "current_plate": None
    },
    "active_tgt": {
        "plate_seq": "Gre_384_Sq_0007",
        "lid_seq": "Gre_384_Sq_0007_lid",
        "current_plate": None,
        "next_well_id": 0, #0,
        "well_count": 384
    },
    "lid_holder_src": {
        "plate_seq": "cp_src_lid_holder_plate",
        "lid_seq": "cp_src_lid_holder_lid",
        "current_lid": None
    },
    "lid_holder_tgt": {
        "plate_seq": "cp_tgt_lid_holder_plate",
        "lid_seq": "cp_tgt_lid_holder_lid",
        "current_lid": None
    },
    "tips": {
        "next_tip_index": 0,
        "max_tips_count": 96,
        "seq": "TIP_50ul_L_NE_stack_0002", # Used for pipetting and throwing in waste
        "seq_for_moving_from_to_stack": "TIP_50ul_L_NE_stack_0005", # NOT for throwing in waste 
        "seq_waste": "TIP_50ul_L_NE_stack_0008",
        "current": False
    },
    "src_stack_1": [ # Bottom to top
        {
            "plate_seq": "Gre_384_Sq_0004_0001",
            "lid_seq": "Gre_384_Sq_0004_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0004_0002",
            "lid_seq": "Gre_384_Sq_0004_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0004_0003",
            "lid_seq": "Gre_384_Sq_0004_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0004_0004",
            "lid_seq": "Gre_384_Sq_0004_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0004_0005",
            "lid_seq": "Gre_384_Sq_0004_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0004_0006",
            "lid_seq": "Gre_384_Sq_0004_0006_lid",
            "current_plate": None
        },
    ],
    "src_stack_2": [ # Bottom to top
        {
            "plate_seq": "Gre_384_Sq_0003_0001",
            "lid_seq": "Gre_384_Sq_0003_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0003_0002",
            "lid_seq": "Gre_384_Sq_0003_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0003_0003",
            "lid_seq": "Gre_384_Sq_0003_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0003_0004",
            "lid_seq": "Gre_384_Sq_0003_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0003_0005",
            "lid_seq": "Gre_384_Sq_0003_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0003_0006",
            "lid_seq": "Gre_384_Sq_0003_0006_lid",
            "current_plate": None
        },
    ], 
    "src_stack_3": [ # Bottom to top
        {
            "plate_seq": "Gre_384_Sq_0002_0001",
            "lid_seq": "Gre_384_Sq_0002_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0002_0002",
            "lid_seq": "Gre_384_Sq_0002_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0002_0003",
            "lid_seq": "Gre_384_Sq_0002_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0002_0004",
            "lid_seq": "Gre_384_Sq_0002_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0002_0005",
            "lid_seq": "Gre_384_Sq_0002_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0002_0006",
            "lid_seq": "Gre_384_Sq_0002_0006_lid",
            "current_plate": None
        },
    ],
    "src_stack_4": [ # Bottom to top
        {
            "plate_seq": "Gre_384_Sq_0010_0001",
            "lid_seq": "Gre_384_Sq_0010_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0010_0002",
            "lid_seq": "Gre_384_Sq_0010_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0010_0003",
            "lid_seq": "Gre_384_Sq_0010_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0010_0004",
            "lid_seq": "Gre_384_Sq_0010_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0010_0005",
            "lid_seq": "Gre_384_Sq_0010_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0010_0006",
            "lid_seq": "Gre_384_Sq_0010_0006_lid",
            "current_plate": None
        },
    ],
    "tgt_stack_1":[
        {
            "plate_seq": "Gre_384_Sq_0005_0001",
            "lid_seq": "Gre_384_Sq_0005_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0005_0002",
            "lid_seq": "Gre_384_Sq_0005_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0005_0003",
            "lid_seq": "Gre_384_Sq_0005_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0005_0004",
            "lid_seq": "Gre_384_Sq_0005_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0005_0005",
            "lid_seq": "Gre_384_Sq_0005_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0005_0006",
            "lid_seq": "Gre_384_Sq_0005_0006_lid",
            "current_plate": None
        },
    ],
    "tgt_stack_2":[
        {
            "plate_seq": "Gre_384_Sq_0001_0001",
            "lid_seq": "Gre_384_Sq_0001_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0001_0002",
            "lid_seq": "Gre_384_Sq_0001_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0001_0003",
            "lid_seq": "Gre_384_Sq_0001_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0001_0004",
            "lid_seq": "Gre_384_Sq_0001_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0001_0005",
            "lid_seq": "Gre_384_Sq_0001_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_Sq_0001_0006",
            "lid_seq": "Gre_384_Sq_0001_0006_lid",
            "current_plate": None
        },
    ],
    "tip_stack_1":[
        {
            "seq": "TIP_50ul_L_NE_stack_0003_0001",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0003_0002",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0003_0003",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0003_0004",
            "current": None
        },
    ],
    "tip_stack_2":[
        {
            "seq": "TIP_50ul_L_NE_stack_0004_0001",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0004_0002",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0004_0003",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0004_0004",
            "current": None
        },
    ],
    "tip_stack_3":[
        {
            "seq": "TIP_50ul_L_NE_stack_0006_0001",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0006_0002",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0006_0003",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0006_0004",
            "current": None
        },
    ],
    "tip_stack_4":[
        {
            "seq": "TIP_50ul_L_NE_stack_0007_0001",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0007_0002",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0007_0003",
            "current": None
        },
        {
            "seq": "TIP_50ul_L_NE_stack_0007_0004",
            "current": None
        },
    ],
}


# -------------------------
#         SETUP
# -------------------------


lmgr = LayoutManager(LAYOUT_FILE_PATH)

tips_type = ResourceType(Tip96, state["tips"]["seq"])
# print("tip seq        :", state["tips"]["seq"])
tip_resource = lmgr.assign_unused_resource(tips_type)

src_plate_type = ResourceType(Plate384,  state["active_src"]["plate_seq"])
src_plate_resource = lmgr.assign_unused_resource(src_plate_type)
tgt_plate_type = ResourceType(Plate384,  state["active_tgt"]["plate_seq"])
tgt_plate_resource = lmgr.assign_unused_resource(tgt_plate_type)

original_input_file_path = ""
current_tgt_plate = None
current_next_well_id = 0
# TODO: Check if there is something to be loaded
# Check if there is a dir in tmp, if yes, ask if load it? (delete if not?)
existing_runs = os.listdir(TMP_DIR_PATH)
if len(existing_runs) > 0:
    print("--- ATTENTION ---")
    print("There are existing runs:")

    user_input_is_continue_prev = input("Do you wish to load one of them? (yes/no)\n")
    while user_input_is_continue_prev != "yes" and user_input_is_continue_prev != "no":
        user_input_is_continue_prev = input("Please type 'yes' if you would like to load, 'no' if you would like to start a new run:\n")
    
    if user_input_is_continue_prev == "yes":
        print("Here are the unfinished runs: ")
        for i in range(len(existing_runs)):
            run = existing_runs[i]
            print(f"[{str(i)}] -", run)
        exp_to_continue_idx = input("Please type the number between [ ] of the run you would like to continue:\n")
        selected_run = existing_runs[int(exp_to_continue_idx)]
        selected_run_tmp_path = os.path.join(TMP_DIR_PATH, selected_run)
        # TODO: Load 

        # TODO: Get latest instance of run
        existing_instances = os.listdir(selected_run_tmp_path)
        existing_instances = [int(x) for x in existing_instances] 
        existing_instances.sort()
        prev_instance_dir = existing_instances[-1]
        new_instance_dir = prev_instance_dir + 1

        # TODO: make the new csv
        prev_instance_mapping_file_path = os.path.join(selected_run_tmp_path,str(prev_instance_dir), "map.json")
        prev_instance_input_csv_file_path = os.path.join(selected_run_tmp_path,str(prev_instance_dir), "input.csv")

        instance_of_run_path = os.path.join(selected_run_tmp_path,str(new_instance_dir))
        os.makedirs(instance_of_run_path)
        new_instance_input_csv_file_path = os.path.join(selected_run_tmp_path,str(new_instance_dir), "input.csv")
        original_input_file_path = new_instance_input_csv_file_path
        load.remove_done_wells_from_csv(prev_instance_input_csv_file_path, prev_instance_mapping_file_path, new_instance_input_csv_file_path)

        # TODO: get the last well used and get the new nb of target plates
        current_tgt_plate, current_next_well_id = load.get_next_tgt_well_used_in_current_plate(os.path.join(selected_run_tmp_path,str(prev_instance_dir), "state_after_dispensing.json"))

    else:
        # START NEW RUN

        # Give name to this cherry-picking run
        user_input_run_name = input(f"Please give a name to this NEW run:\n")

        # Create folder in tmp for this run
        run_tmp_dir_path = os.path.join(TMP_DIR_PATH, f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{user_input_run_name}")
        run_out_dir_path = os.path.join(OUT_DIR_PATH, f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{user_input_run_name}")

        # tmp files
        if not os.path.exists(run_tmp_dir_path):
            os.makedirs(run_tmp_dir_path)
        
        original_input_file_path = input(f"Please provide a path to the input csv file:\n")
        while not os.path.isfile(original_input_file_path):
            original_input_file_path = input(f"Please provide a path to the input csv file:\n")

        instance_of_run_path = os.path.join(run_tmp_dir_path, "0")
        os.makedirs(instance_of_run_path)
        shutil.copy(original_input_file_path,os.path.join(instance_of_run_path, 'input.csv'))

else:
    # Give name to this cherry-picking run
    user_input_run_name = input(f"Please give a name to this NEW run:\n")

    # Create folder in tmp for this run
    run_tmp_dir_path = os.path.join(TMP_DIR_PATH, f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{user_input_run_name}")
    run_out_dir_path = os.path.join(OUT_DIR_PATH, f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{user_input_run_name}")

    # tmp files
    if not os.path.exists(run_tmp_dir_path):
        os.makedirs(run_tmp_dir_path)
    
    original_input_file_path = input(f"Please provide a path to the input csv file:\n")
    while not os.path.isfile(original_input_file_path):
        original_input_file_path = input(f"Please provide a path to the input csv file:\n")

    instance_of_run_path = os.path.join(run_tmp_dir_path, "0")
    os.makedirs(instance_of_run_path)
    shutil.copy(original_input_file_path,os.path.join(instance_of_run_path, 'input.csv'))

# Get the input list of all the wells for each plate
print(original_input_file_path)
plates = hp.get_wells_of_interest_from_csv(original_input_file_path)

# Get number of interesting samples to be cherry-picked
src_wells_of_interest_count = 0
src_plates_count = 0
for plate in plates:
    src_wells_of_interest_count += len(plates[plate])
    src_plates_count += 1

if src_plates_count > 12:
    raise "Attention!! Cannot have more than 12 plates"

# Calculate how many target plates will be needed based on the nb of wells to cherrypick from src plates
src_wells_of_interest_count_without_available_loaded_tgt = src_wells_of_interest_count
if current_tgt_plate: # Check if user is loading to continue previous run
    available_wells_in_current_tgt_plate = 384 - current_next_well_id
    src_wells_of_interest_count_without_available_loaded_tgt = src_wells_of_interest_count - available_wells_in_current_tgt_plate

tgt_plate_count = math.ceil(src_wells_of_interest_count_without_available_loaded_tgt / 384)

# Confirm with user the number and placement of the target plates
print("We will now put empty plates that will contain the cherry-picked samples.")
user_input_put_empty_plates = False
while user_input_put_empty_plates != 'yes': 
    user_input_put_empty_plates = input(f"Please label {tgt_plate_count} target empty plates (with their lids) - These will contain the cherry-picked samples.\nType 'yes' when {tgt_plate_count} plates have been labelled:\n")
    if current_tgt_plate:
        print(f"Do not label the plate: {current_tgt_plate}. It has to be added at the top")

# Confirm with user the names of the target plates

previous_labels = []
if current_tgt_plate:
    previous_labels.append(current_tgt_plate)

print("-- Previous Active Plate:", current_tgt_plate)
last_index_tgt_plate = -1
if tgt_plate_count > 0:
    for i in range(tgt_plate_count):
        last_index_tgt_plate = i
        plate_label = input(f"Please place plate #{i+1} in target stack 2.\nType the label given to this plate:\n")
        while plate_label in previous_labels or plate_label == "":
            plate_label = input(f"Plate Labels should be unique and not null\nPlease place plate #{i+1} in target stack 2.\nType the label given to this plate:\n")
        previous_labels.append(plate_label)
        state[f"tgt_stack_2"][i]["current_plate"] = plate_label

# Add the last tgt plate on top
state[f"tgt_stack_2"][last_index_tgt_plate + 1]["current_plate"] = current_tgt_plate
state["active_tgt"]["next_well_id"] = int(current_next_well_id)

# Confirm with user the that the active src and tgt sites are empty (there are no plates)
user_input_active_tgt_pos = False
while user_input_active_tgt_pos != 'yes':
    user_input_active_tgt_pos = input(f"Type 'yes' to confirm that the position of the active TARGET plate is empty:\n")

user_input_active_src_pos = False
while user_input_active_src_pos != 'yes':
    user_input_active_src_pos = input(f"Type 'yes' to confirm that the position of the active SOURCE plate is empty:\n")

# Ask the user to place plates with no lids in the lid holder positions
user_input_tgt_lid_holder_pos = False
while user_input_tgt_lid_holder_pos != 'yes':
    user_input_tgt_lid_holder_pos = input(f"Please place an empty plate (with no lid) in the TARGET lid holder position.\nType 'yes' to confirm that the plate has been placed:\n")

user_input_src_lid_holder_pos = False
while user_input_src_lid_holder_pos != 'yes':
    user_input_src_lid_holder_pos = input(f"Please place an empty plate (with no lid) in the SOURCE lid holder position.\nType 'yes' to confirm that the plate has been placed:\n")

# Add first rack
user_input_first_rack_active = False
while user_input_first_rack_active != 'yes':
    user_input_first_rack_active = input(f"Please place a 96 tip rack on the active_tip position.\nType 'yes' to confirm that the tip rack has been placed:\n")

state["tips"]["current"] = "tip_rack"

# Manage pipette tips, ask where are we in terms of pipette tips
def get_pipette_tip_next_pos_from_user():
    user_input_pipette_tip_column = 0
    while not (user_input_pipette_tip_column > 0 and user_input_pipette_tip_column <= 12):
        user_input_pipette_tip_column = input(f"Pipette tip column number (1-12):\n")
        try:
            user_input_pipette_tip_column = int(user_input_pipette_tip_column)
        except ValueError:
            print("Please enter a valid number")
            user_input_pipette_tip_column = 0

    user_input_pipette_tip_row = 0
    while not (user_input_pipette_tip_row > 0 and user_input_pipette_tip_row <= 8):
        user_input_pipette_tip_row = input(f"Pipette tip row number (1-8):\n")
        try:
            user_input_pipette_tip_row = int(user_input_pipette_tip_row)
        except ValueError:
            print("Please enter a valid number")
            user_input_pipette_tip_row = 0

    # Locate pipette tip (get id in sequence)
    return 8 * (user_input_pipette_tip_column - 1) + user_input_pipette_tip_row - 1 # 8 rows

next_pipette_tip_index = get_pipette_tip_next_pos_from_user()
state["tips"]["next_tip_index"] = next_pipette_tip_index


# calculate amount of tips left
tips_left_count = 96 - next_pipette_tip_index

# TIPS
# Get number of stacks left:
tip_racks_to_stack_count = math.ceil( (src_wells_of_interest_count - tips_left_count ) / 96)
input(f"racks stacked [Any Key]: {str(tip_racks_to_stack_count)}")
if tip_racks_to_stack_count > 16:
    raise "Tip Stacks required are > 16. Aborting..."


# Before asking user about current pipette position - guide them through positioning the tips in the correct stacks (e.g. "place 4 full stacks in stack_1 and 2 in stack_2")
def get_tip_stacks_disposition(tip_racks_to_stack_count:int, stack_limit:int): 
    racks_in_stack_count = [0, 0, 0, 0] # ["tip_stack_1", "tip_stack_2", "tip_stack_3", "tip_stack_4"]
    stacks_needed_count = math.ceil( (tip_racks_to_stack_count)  / stack_limit) 
    added_racks = 0
    for i in range(stacks_needed_count):
        to_add_in_current_stack = tip_racks_to_stack_count - added_racks
        if to_add_in_current_stack > stack_limit:
            to_add_in_current_stack = 4

        racks_in_stack_count[i] = to_add_in_current_stack
        added_racks += to_add_in_current_stack

    return racks_in_stack_count

tip_racks_in_stacks_counts = get_tip_stacks_disposition(tip_racks_to_stack_count, TIP_STACK_LIMIT) # -1 because one stack will be on the active tips site from the beginning

input(f"Tip Racks Stacks disposition [Any Key]: {str(tip_racks_in_stacks_counts)}")

tip_stack_names = ["tip_stack_1", "tip_stack_2", "tip_stack_3", "tip_stack_4"]
for i in range(len(tip_stack_names)): 
    tip_rack_count = tip_racks_in_stacks_counts[i]
    current_tip_stack = tip_stack_names[i]
    if tip_rack_count == 0:
        break
    
    tip_rack_added_input = False
    while tip_rack_added_input != 'yes':
        tip_rack_added_input = input(f"Type 'yes' to confirm that a stack of ({str(tip_rack_count)}) tip racks have been placed in {current_tip_stack} :\n")
    
    for index_in_stack in range(tip_rack_count):
        state[current_tip_stack][index_in_stack]["current"] = "tip_rack"

# Ask the user to set the plates (in stacks 1 and 2)
placed_in_stack = 0
index_in_current_stack = 0
stack_to_place_in = "2"
for plate in plates:
    # Fill stack 1 and 2, leave stack 3 empty
    if placed_in_stack == 6:
        stack_to_place_in = "3"
        index_in_current_stack = 0
    if placed_in_stack >= 12:
        print("Reached limit for source plates. Cannot add any more.")
        break
    user_input_src_plate_add_to_stack = False
    while user_input_src_plate_add_to_stack != 'yes':
        user_input_src_plate_add_to_stack = input(f"Please place the LIDDED PLATE '{plate}' in source stack {stack_to_place_in}.\nType 'yes' to confirm that the plate has been placed:\n")
        # change state
    state[f"src_stack_{stack_to_place_in}"][index_in_current_stack]["current_plate"] = plate
    placed_in_stack += 1 
    index_in_current_stack += 1



# -------------------------
#        EXECUTION
# -------------------------

# Need functions to:
#   [X] get the current stacked src plate from the state - returns the stack it is in and the index to know how high it is
#   [X] get the current stacked tgt plate from the state - returns the stack it is in and the index to know how high it is
#   [X] get the next done src plate position from the state - returns the potential position (stack and index to know how high it is)
#   [X] get the next done tgt plate position from the state - returns the potential position (stack and index to know how high it is)

json.dump(state, open("00_initial_state.json",'w'))
remaining_wells_of_interest = src_wells_of_interest_count
with HamiltonInterface(simulate=True) as hammy:
    print("Initializing...")
    hammy.wait_on_response(hammy.send_command(INITIALIZE))
    print('Done Initializing.')


    # Loop over source plates 
    while state["treated_src_plates_count"] < src_plates_count:
        # Get new active src
        act.move_next_src_plate_from_stack_to_active_position(state,hammy, SRC_STACK_LIMIT)
        str_msg = f"-- Move lid from active src to src lid holder [Press Enter]"
        #input(str_msg)

        # move lid from active_src_pos to src_lid_holder 
        act.move_active_src_lid_to_lid_holder(state, hammy)

        if state["active_tgt"]["current_plate"] == None:
            act.get_target_plate(state, hammy, SRC_STACK_LIMIT)
        
        json.dump(state, open("./01_before_cherry_picking_state.json",'w'))
        # Cherry Pick!
        wells_to_pick = hp.convertPlatePositionsToIndices(plates[state["active_src"]["current_plate"]])

        

        # Settings for cherry-picking procedures
        liquid_class = LIQUID_CLASS #'Tip_50ul_Water_DispenseJet_Empty' #'Tip_50ul_96COREHead_Water_DispenseJet_Empty'
        for well_to_pick in wells_to_pick:
            str_msg = f"-- Check if there still are tips [Press Enter]"
            #input(str_msg)
            # Check if there still are tips (state["tips"]["next_tip_index"])
            while state["tips"]["next_tip_index"] >= state["tips"]["max_tips_count"]:
                #input("--------\nAttention: No more tips. Please add a new tips set [Any Key].\n--------")
        	    
                json.dump(state, open("./02_before_changing_tips.json",'w'))
                act.throw_active_tip_rack_into_waste(state,hammy)
                json.dump(state, open("./03_before_changing_tips_but_after_waste_tips.json",'w'))
                state["treated_tip_racks_count"] += 1 
                state["tips"]["next_tip_index"] = 0

                # Get New Tips
                act.move_tip_rack_from_stack_to_active_tip_position(state, hammy, TIP_STACK_LIMIT)

            str_msg = f"-- Check if active target plate is full [Press Enter]"
            #input(str_msg)
            # Check if still places in tgt plate
            if state["active_tgt"]["next_well_id"] >= state["active_tgt"]["well_count"]:
                print("[Notice] active target plate is full. Replacing it...")
                act.move_full_tgt_plate_from_active_position_to_stack(state, hammy, SRC_STACK_LIMIT)

                state["treated_tgt_plates_count"] += 1

                # Check if this is the last target plate and stop if yes, this means the source should also be completed, coincidentally they were finished together
                if state["treated_tgt_plates_count"] == tgt_plate_count:
                    print("No more target plates available. Should be done also with source")
                    break
                
                # Get new target plate and remove its lid
                act.get_target_plate(state, hammy, SRC_STACK_LIMIT)
                state["active_tgt"]["next_well_id"] = 0
            
            str_msg = f"-- Pick well {well_to_pick} [Press Enter]"
            #input(str_msg)
            # Run cherry-picking for one well
            tip_pos = (tip_resource, state["tips"]["next_tip_index"])
            # print("tip pos        :", tip_pos)
            # Update next tip position in state
            state["tips"]["next_tip_index"] += 1

            well_pos_in_src_plate = (src_plate_resource, well_to_pick)

            well_pos_in_tgt_plate = (tgt_plate_resource, state["active_tgt"]["next_well_id"])

            try:
                new_mapping[str(state["active_tgt"]["current_plate"]) + "_" + str(state["active_tgt"]["next_well_id"])] = str(state["active_src"]["current_plate"]) + "_" + str(well_to_pick)
            except:
                print('somthing went wrong with the mapping ')

            # Update next target well position in state
            state["active_tgt"]["next_well_id"] += 1

            # Aspirate from well of interest
            tip_pick_up(hammy, [tip_pos])
            aspirate(hammy, [well_pos_in_src_plate], [2], liquidClass = liquid_class,
                mixCycles=3,
                mixVolume=5.0,
                liquidHeight=0.5
            )

            # Dispense into target well
            dispense(hammy, [well_pos_in_tgt_plate], [2], liquidClass = liquid_class)
            tip_eject(hammy,  wasteSequence="Waste") #[tip_pos]) 
            json.dump(new_mapping, open("./L_mapping.json",'w'))
            # Print Progress to user
            json.dump(new_mapping, open(os.path.join(instance_of_run_path, "map.json"),'w'))
            json.dump(state, open(os.path.join(instance_of_run_path, "state_after_dispensing.json"),'w'))
            remaining_wells_of_interest -= 1
            print(f"Progress: {src_wells_of_interest_count - remaining_wells_of_interest}/{src_wells_of_interest_count}", )
        
            str_msg = f"-- Done picking well '{well_to_pick}' [Press Enter]"
            #input(str_msg)


        # Store active src (assuming it is done)
        act.move_src_plate_from_active_pos_to_done_stack(state, hammy, SRC_STACK_LIMIT)


        # state update: Add one plate as already treated
        state["treated_src_plates_count"] += 1
        to_print = state["treated_src_plates_count"]
        print(f"Plates Processed: {to_print}/{src_plates_count}")

    # Check if there is a plate on the active tgt site. if so, put it back.
    if state["active_tgt"]["current_plate"] != None:
        act.put_tgt_plate_in_done_tgt_stack(state, hammy, SRC_STACK_LIMIT)
    os.makedirs(run_out_dir_path)
    json.dump(new_mapping, open(os.path.join(run_out_dir_path, "map.json"),'w'))
    
    # TODO: Archive/delete intermediate data

    print("\n-----\nCherry-picking Protocol Done\n-----\n")
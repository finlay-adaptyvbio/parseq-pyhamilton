import json
import math
import os
import helpers as hp
from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType, Plate384, Tip96, INITIALIZE, GRIP_GET, GRIP_PLACE, GRIP_MOVE, tip_pick_up, tip_eject, aspirate, dispense)

LAYOUT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cherry_picking_protocol_stacked_tips.lay")
INPUT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "new_mapping_3.csv")#"test_data","2p_more_than_2_tgt_p.csv")
SRC_STACK_LIMIT = 6
TGT_STACK_LIMIT = 6
TIP_STACK_LIMIT = 4
WASTE_SEQUENCE = "Waste"

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
        "next_well_id": 46, #0,
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

# Get the input list of all the wells for each plate
plates = hp.get_wells_of_interest_from_csv(INPUT_FILE_PATH)

# Get number of interesting samples to be cherry-picked
src_wells_of_interest_count = 0
src_plates_count = 0
for plate in plates:
    src_wells_of_interest_count += len(plates[plate])
    src_plates_count += 1

if src_plates_count > 12:
    raise "Attention!! Cannot have more than 12 plates"

# Calculate how many target plates will be needed based on the nb of wells to cherrypick from src plates
tgt_plate_count = math.ceil(src_wells_of_interest_count / 384)

# Confirm with user the number and placement of the target plates
print("We will now put empty plates that will contain the cherry-picked samples.")
user_input_put_empty_plates = False
while user_input_put_empty_plates != 'yes':
    user_input_put_empty_plates = input(f"Please label {tgt_plate_count} target empty plates (with their lids) - These will contain the cherry-picked samples.\nType 'yes' when {tgt_plate_count} plates have been labelled:\n")

# Confirm with user the names of the target plates
previous_labels = []
for i in range(tgt_plate_count):
    plate_label = input(f"Please place plate #{i+1} in target stack 2.\nType the label given to this plate:\n")
    while plate_label in previous_labels or plate_label == "":
        plate_label = input(f"Plate Labels should be unique and not null\nPlease place plate #{i+1} in target stack 2.\nType the label given to this plate:\n")
    previous_labels.append(plate_label)
    state[f"tgt_stack_2"][i]["current_plate"] = plate_label


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

# TODO: ----------------------- MODIFIED 
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
# TODO: Put on stacks
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
# TODO: ----------------------- MODIFIED 

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

def put_tgt_plate_in_done_tgt_stack(ejectToolWhenFinish:int = 1):
    cmd_grip_get_lid(
        hammy,
        state["lid_holder_tgt"]["plate_seq"],
        state["lid_holder_tgt"]["lid_seq"],
        transportMode = 1,
    )
    # Update state
    state["gripped_plate"]["current_lid"] = state["lid_holder_tgt"]["current_lid"]
    state["lid_holder_tgt"]["current_lid"] = None

    cmd_grip_place_lid(
        hammy,
        state["active_tgt"]["plate_seq"],
        state["active_tgt"]["lid_seq"],
        transportMode = 1,
        ejectToolWhenFinish=0
    )
    # Update state
    state["lid_holder_tgt"]["current_lid"] = None
    # Put plate in done target stack
    cmd_grip_get_plate_with_lid(
        hammy, 
        state["active_tgt"]["plate_seq"], 
        state["active_tgt"]["lid_seq"],
        transportMode = 2
    )
    # Update state
    state["gripped_plate"]["current_plate"] = state["gripped_plate"]["current_plate"]
    state["gripped_plate"]["current_lid"]   = state["gripped_plate"]["current_plate"]
    state["active_tgt"]["current_plate"]    = None


    next_done_tgt_stack_name, next_done_tgt_stack_index = hp.get_next_done_stacked_plate(state,SRC_STACK_LIMIT,"tgt")#get_next_done_tgt_plate_pos(state)
    next_done_tgt_plate_seq = state[next_done_tgt_stack_name][next_done_tgt_stack_index]["plate_seq"]
    next_done_tgt_lid_seq = state[next_done_tgt_stack_name][next_done_tgt_stack_index]["lid_seq"] 
    cmd_grip_place_plate_with_lid(
        hammy, 
        next_done_tgt_plate_seq,
        next_done_tgt_lid_seq,
        transportMode = 2,
        ejectToolWhenFinish = ejectToolWhenFinish
    )
    # Update state
    state[next_done_tgt_stack_name][next_done_tgt_stack_index]["current_plate"] = state["gripped_plate"]["current_plate"]
    state["gripped_plate"]["current_plate"] = None
    state["gripped_plate"]["current_lid"]   = None

def get_next_done_src_plate_pos(state:dict):
    treated_src_plates_count = state["treated_src_plates_count"]
    stack_nb = "1"
    if not (treated_src_plates_count < 12):
        return None, None

    if (treated_src_plates_count > SRC_STACK_LIMIT):
        stack_nb = "2"

    stack_name = f"src_stack_{stack_nb}"
    upper_most_plate = 0
    for pos in state[stack_name]:
        if pos["current_plate"] == None:
            break
        if upper_most_plate == SRC_STACK_LIMIT:
            input(f"Error. There are no more places available in 'src done stack' (src_stack_{stack_nb}). Abort [Press Enter]")
            raise ""
            break
        upper_most_plate += 1
    
    index_in_stack = upper_most_plate
    return stack_name, index_in_stack

def get_next_done_tgt_plate_pos(state:dict):
    treated_tgt_plates_count = state["treated_tgt_plates_count"]
    if not(treated_tgt_plates_count < TGT_STACK_LIMIT):
        return None, None
    
    stack_name = f'tgt_stack_1'
    upper_most_plate = 0
    for pos in state[stack_name]:
        if pos["current_plate"] == None:
            break
        if upper_most_plate == TGT_STACK_LIMIT:
            input(f"Error. There are no more places available in 'tgt done stack' ({stack_name}). Abort [Press Enter]")
            raise ""
            break
        upper_most_plate += 1
    
    index_in_stack = upper_most_plate
    return stack_name, index_in_stack
    
# TODO: ----------------------- MODIFIED 
def cmd_grip_get_tip_rack (
        hamilton_interface:HamiltonInterface, 
        plateSequence:str, 
        toolSequence:str = 'COREGripTool_OnWaste_1000ul_0001',
    ):
    cmd_id = hamilton_interface.send_command(GRIP_GET, 
                                plateSequence      = plateSequence,
                                toolSequence       = toolSequence,
                                gripForce          = 9,
                                gripperToolChannel = 2,
                                gripHeight         = 26.5,
                                transportMode      = 0 )
    print(hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True))

def cmd_grip_place_tip_rack (
        hamilton_interface:HamiltonInterface, 
        plateSequence:str, 
        toolSequence:str = 'COREGripTool_OnWaste_1000ul_0001',
        ejectToolWhenFinish:int = 1,
    ):
    cmd_id = hamilton_interface.send_command(GRIP_PLACE, 
                                plateSequence      = plateSequence,
                                toolSequence       = toolSequence,
                                transportMode      = 0,
                                ejectToolWhenFinish = ejectToolWhenFinish)
    print(hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True))
# TODO: ----------------------- MODIFIED 

def cmd_grip_get_plate_with_lid(
        hamilton_interface:HamiltonInterface, 
        plateSequence:str, 
        lidSequence:str, 
        toolSequence:str = 'COREGripTool_OnWaste_1000ul_0001',
        gripForce:float = 3,
        transportMode:int = 2
    ):
    cmd_id = hamilton_interface.send_command(GRIP_GET, 
                                plateSequence      = plateSequence,
                                lidSequence        = lidSequence,
                                toolSequence       = toolSequence,
                                gripForce          = gripForce,
                                gripperToolChannel = 2,
                                gripHeight         = 10.0,
                                transportMode      = transportMode )
    print(hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True))

def cmd_grip_place_plate_with_lid(
        hamilton_interface:HamiltonInterface,
        plateSequence:str, 
        lidSequence:str, 
        toolSequence:str = 'COREGripTool_OnWaste_1000ul_0001',
        transportMode:int = 2,
        ejectToolWhenFinish:int = 1,
    ):
    cmd_id = hamilton_interface.send_command(GRIP_PLACE,
                                plateSequence       = plateSequence,
                                lidSequence         = lidSequence,
                                toolSequence        = toolSequence,
                                transportMode       = transportMode,
                                ejectToolWhenFinish = ejectToolWhenFinish)
    print(hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True))


def cmd_grip_get_lid(
        hamilton_interface:HamiltonInterface, 
        plateSequence:str, 
        lidSequence:str, 
        toolSequence:str = 'COREGripTool_OnWaste_1000ul_0001',
        gripForce:float = 3,
        transportMode:int = 1
    ):
    cmd_id = hamilton_interface.send_command(GRIP_GET, 
                                #plateSequence      = plateSequence,
                                lidSequence        = lidSequence,
                                toolSequence       = toolSequence,
                                gripForce          = gripForce,
                                gripperToolChannel = 2,
                                gripHeight         = 3.0,
                                transportMode      = transportMode )
    print(hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True))

def cmd_grip_place_lid(
        hamilton_interface:HamiltonInterface,
        plateSequence:str,
        lidSequence:str,
        toolSequence:str = 'COREGripTool_OnWaste_1000ul_0001',
        transportMode:int = 1,
        ejectToolWhenFinish:int = 1,
    ):
    cmd_grip_place_plate_with_lid(hamilton_interface,plateSequence,lidSequence,toolSequence, transportMode=transportMode,ejectToolWhenFinish=ejectToolWhenFinish)

# TODO: ----------------------- MODIFIED 
def throw_active_tip_rack_into_waste(state:dict):
    # Throw Tips in Trash
    cmd_grip_get_tip_rack(
        hammy, 
        state["tips"]["seq"]
    )
    # Update state
    state["tips"]["current"] = None
    state["gripped_plate"]["current_plate"] = "tip_rack"

    cmd_grip_place_tip_rack(
        hammy,
        state["tips"]["seq_waste"]
    )
    state["gripped_plate"]["current_plate"] = None
# TODO: ----------------------- MODIFIED  

json.dump(state, open("./00_initial_state.json",'w'))

with HamiltonInterface(simulate=True) as hammy:
    print("Initializing...")
    hammy.wait_on_response(hammy.send_command(INITIALIZE))
    print('Done Initializing.')


    # Loop over source plates 
    while state["treated_src_plates_count"] < src_plates_count:
        # Get new active src
        #   Move plate w lid from src_stack_3 with lid to active_src_pos
        next_src_stack_name, next_src_stack_index = hp.get_next_stacked_plate(state, SRC_STACK_LIMIT, "src")#get_next_stacked_src_plate(state)
        print("next stack source stack name :", next_src_stack_name)
        print("next stack source stack index:", next_src_stack_index)
        print("state:", state[next_src_stack_name][next_src_stack_index])
        next_src_plate_seq = state[next_src_stack_name][next_src_stack_index]["plate_seq"]
        next_src_lid_seq = state[next_src_stack_name][next_src_stack_index]["lid_seq"] 
        str_msg = f"-- Move plate from source to active [Press Enter]"
        #input(str_msg)
        cmd_grip_get_plate_with_lid(
            hammy,
            next_src_plate_seq,
            next_src_lid_seq,
            transportMode=2
        )
        # Update state
        state["gripped_plate"]["current_plate"] = state[next_src_stack_name][next_src_stack_index]["current_plate"]
        state["gripped_plate"]["current_lid"]   = state[next_src_stack_name][next_src_stack_index]["current_plate"]
        state[next_src_stack_name][next_src_stack_index]["current_plate"] = None
        print('gripped plate:',state["gripped_plate"]["current_plate"])
        cmd_grip_place_plate_with_lid( #cmd_grip_place_plate_with_lid(
            hammy, 
            state["active_src"]["plate_seq"],
            state["active_src"]["lid_seq"],
            transportMode=2,
            ejectToolWhenFinish=0
        )
        # Update state
        state["active_src"]["current_plate"] = state["gripped_plate"]["current_plate"]
        state["gripped_plate"]["current_plate"] = None
        state["gripped_plate"]["current_lid"]   = None

        plate_treated_now = state[next_src_stack_name][next_src_stack_index]["current_plate"]
        str_msg = f"-- Move lid from active src to src lid holder [Press Enter]"
        #input(str_msg)

        #   move lid from active_src_pos to src_lid_holder 
        cmd_grip_get_lid(
            hammy,
            state["active_src"]["plate_seq"],
            state["active_src"]["lid_seq"],
            transportMode = 1,
        )
        state["gripped_plate"]["current_lid"] = state["active_src"]["current_plate"]

        cmd_grip_place_lid(
            hammy,
            state["lid_holder_src"]["plate_seq"],
            state["lid_holder_src"]["lid_seq"],
            transportMode = 1,
            ejectToolWhenFinish = 0
        )
        # Update state
        state["lid_holder_src"]["current_lid"] = state["gripped_plate"]["current_lid"]
        state["gripped_plate"]["current_lid"] = None


        def get_target_plate(ejectToolWhenFinish:bool = True):
            # Get new active tgt
            #   Move plate w lid from tgt_stack_2 with lid to active_tgt_pos
            next_tgt_stack_name, next_tgt_stack_index = hp.get_next_stacked_plate(state, SRC_STACK_LIMIT, "tgt")
            next_tgt_plate_seq = state[next_tgt_stack_name][next_tgt_stack_index]["plate_seq"]
            next_tgt_lid_seq = state[next_tgt_stack_name][next_tgt_stack_index]["lid_seq"] 
            str_msg = f"-- Move plate from target stack to active [Press Enter]"
            #input(str_msg)
            cmd_grip_get_plate_with_lid(
                hammy, 
                next_tgt_plate_seq,
                next_tgt_lid_seq,
                transportMode = 2,
            )
            # Update state
            state["gripped_plate"]["current_plate"] = state[next_tgt_stack_name][next_tgt_stack_index]["current_plate"]
            state["gripped_plate"]["current_lid"]   = state[next_tgt_stack_name][next_tgt_stack_index]["current_plate"]
            state[next_tgt_stack_name][next_tgt_stack_index]["current_plate"] = None

            cmd_grip_place_plate_with_lid(
                hammy, 
                state["active_tgt"]["plate_seq"], 
                state["active_tgt"]["lid_seq"],
                transportMode = 2,
                ejectToolWhenFinish=0
            )
            # Update state
            state["active_tgt"]["current_plate"] = state["gripped_plate"]["current_plate"]
            state["gripped_plate"]["current_plate"] = None
            state["gripped_plate"]["current_lid"]   = None
            
            str_msg = f"-- Move lid from active tgt to tgt lid holder [Press Enter]"
            #input(str_msg)
            #   move lid from active_tgt_pos to tgt_lid_holders
            cmd_grip_get_lid(
                hammy,
                state["active_tgt"]["plate_seq"],
                state["active_tgt"]["lid_seq"],
                transportMode = 1
            )
            state["gripped_plate"]["current_lid"] = state["active_tgt"]["current_plate"]
            
            cmd_grip_place_lid(
                hammy,
                state["lid_holder_tgt"]["plate_seq"],
                state["lid_holder_tgt"]["lid_seq"],
                transportMode = 1,
                ejectToolWhenFinish = ejectToolWhenFinish
            )
            # Update state
            state["lid_holder_tgt"]["current_lid"] = state["gripped_plate"]["current_lid"]
            state["gripped_plate"]["current_lid"] = None

        if state["active_tgt"]["current_plate"] == None:
            get_target_plate()
        
        json.dump(state, open("./01_before_cherry_picking_state.json",'w'))
        # Cherry Pick!
        active_src_plate_name = state["active_src"]["current_plate"]
        
        wells_to_pick = hp.convertPlatePositionsToIndices( plates[active_src_plate_name] )

        remaining_wells_of_interest = src_wells_of_interest_count

        # Settings for cherry-picking procedures
        liquid_class = "Tip_50ul_96COREHead1000ul_Water_DispenseJet_PartEmpty" #'Tip_50ul_Water_DispenseJet_Empty' #'Tip_50ul_96COREHead_Water_DispenseJet_Empty'

        for well_to_pick in wells_to_pick:
            str_msg = f"-- Check if there still are tips [Press Enter]"
            #input(str_msg)
            # Check if there still are tips (state["tips"]["next_tip_index"])
            while state["tips"]["next_tip_index"] >= state["tips"]["max_tips_count"]:
                input("--------\nAttention: No more tips. Please add a new tips set [Any Key].\n--------")
                """print("--------\nAttention: No more tips. Please add a new tips set.\n--------")
                # Confirm with user the that the active src and tgt sites are empty (there are no plates)
                user_input_new_tips_added = False
                while user_input_new_tips_added != 'yes':
                    user_input_new_tips_added = input(f"Type 'yes' to confirm that new tips have been added:\n")
                
                # Get new next_tip_position
                next_pipette_tip_index = get_pipette_tip_next_pos_from_user()
                state["tips"]["next_tip_index"] = next_pipette_tip_index
        	    """
                json.dump(state, open("./02_before_changing_tips.json",'w'))
                throw_active_tip_rack_into_waste(state)
                json.dump(state, open("./03_before_changing_tips_but_after_waste_tips.json",'w'))
                # NEW
                state["treated_tip_racks_count"] += 1 
                state["tips"]["next_tip_index"] = 0#0
                # TODO: ----------------------- START MODIFIED 
                # Get New Tips
                #   Move plate w lid from src_stack_3 with lid to active_src_pos
                next_tip_rack_stack_name, next_tip_rack_stack_index = hp.get_next_stacked_tip_rack(state, TIP_STACK_LIMIT)
                next_tip_rack_seq = state[next_tip_rack_stack_name][next_tip_rack_stack_index]["seq"]
                str_msg = f"-- Move tip rack from {next_tip_rack_stack_name}-{str(next_tip_rack_stack_index)} to active [Press Enter]"
                #input(str_msg)
                cmd_grip_get_tip_rack(
                    hammy,
                    next_tip_rack_seq,
                )
                # Update state
                state["gripped_plate"]["current_plate"] = "tip_rack"
                state[next_tip_rack_stack_name][next_tip_rack_stack_index]["current"] = None
                print('gripped plate:',state["gripped_plate"]["current_plate"])
                json.dump(state, open("./04_after_getting_new_rack.json",'w'))
                cmd_grip_place_tip_rack( #cmd_grip_place_plate_with_lid(
                    hammy, 
                    state["tips"]["seq_for_moving_from_to_stack"], 
                )
                # Update state
                state["tips"]["current"] = state["gripped_plate"]["current_plate"]
                state["gripped_plate"]["current_plate"] = None
                json.dump(state, open("./05_after_placing_new_rack.json",'w'))
                # TODO: ----------------------- START MODIFIED 

            
            str_msg = f"-- Check if active target plate is full [Press Enter]"
            #input(str_msg)
            # Check if still places in tgt plate
            if state["active_tgt"]["next_well_id"] >= state["active_tgt"]["well_count"]:
                print("[Notice] active target plate is full. Replacing it...")
                # Close Lid
                cmd_grip_get_lid(
                    hammy,
                    state["lid_holder_tgt"]["plate_seq"],
                    state["lid_holder_tgt"]["lid_seq"],
                    transportMode = 1,
                )
                # Update state
                state["gripped_plate"]["current_lid"] = state["lid_holder_tgt"]["current_lid"]
                state["lid_holder_tgt"]["current_lid"] = None

                cmd_grip_place_lid(
                    hammy,
                    state["active_tgt"]["plate_seq"],
                    state["active_tgt"]["lid_seq"],
                    transportMode = 1,
                    ejectToolWhenFinish=0
                )
                # Update state
                state["lid_holder_tgt"]["current_lid"] = None

                # Put target plate back
                #   Move plate w lid from active_tgt_pos to tgt_stack_1 (or 2 if 1 is full) - essentially to next done tgt position
                cmd_grip_get_plate_with_lid(
                    hammy, 
                    state["active_tgt"]["plate_seq"], 
                    state["active_tgt"]["lid_seq"],
                    transportMode = 2,
                )
                # Update state
                state["gripped_plate"]["current_plate"] = state["active_tgt"]["current_plate"]
                state["gripped_plate"]["current_lid"]   = state["active_tgt"]["current_plate"]
                state["active_tgt"]["current_plate"] = None

                next_done_tgt_stack_name, next_done_tgt_stack_index = hp.get_next_done_stacked_plate(state,SRC_STACK_LIMIT,"tgt")#get_next_done_tgt_plate_pos(state)
                next_done_tgt_plate_seq = state[next_done_tgt_stack_name][next_done_tgt_stack_index]["plate_seq"]
                next_done_tgt_lid_seq = state[next_done_tgt_stack_name][next_done_tgt_stack_index]["lid_seq"] 
                cmd_grip_place_plate_with_lid(
                    hammy,
                    next_done_tgt_plate_seq,
                    next_done_tgt_lid_seq,
                    transportMode = 2,
                )
                # Update state
                state[next_done_tgt_stack_name][next_done_tgt_stack_index]["current_plate"] = state["gripped_plate"]["current_plate"]
                state["gripped_plate"]["current_plate"] = None
                state["gripped_plate"]["current_lid"]   = None


                state["treated_tgt_plates_count"] += 1

                # Check if this is the last target plate and stop if yes, this means the source should also be completed, coincidentally they were finished together
                if state["treated_tgt_plates_count"] == tgt_plate_count:
                    print("No more target plates available. Should be done also with source")
                    break
                
                # Get new target plate and remove its lid
                get_target_plate()
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
            aspirate(hammy, [well_pos_in_src_plate], [1], liquidClass = liquid_class)

            # Dispense into target well
            dispense(hammy, [well_pos_in_tgt_plate], [0.1], liquidClass = liquid_class)
            tip_eject(hammy, wasteSequence="Waste") #[tip_pos])
            json.dump(new_mapping, open("./L_mapping.json",'w'))
            # Print Progress to user
            remaining_wells_of_interest -= 1
            print(f"Progress: {src_wells_of_interest_count - remaining_wells_of_interest}/{src_wells_of_interest_count}", )
        
            str_msg = f"-- Done picking well '{well_to_pick}' [Press Enter]"
            #input(str_msg)

        # Store active src (assuming it is done)
        #   move lid from src_lid_holder to active_src_pos
        cmd_grip_get_lid(
            hammy,
            state["lid_holder_src"]["plate_seq"],
            state["lid_holder_src"]["lid_seq"],
            transportMode = 1,
        )
        # Update state
        state["gripped_plate"]["current_lid"] = state["lid_holder_src"]["current_lid"]
        state["lid_holder_src"]["current_lid"] = None

        cmd_grip_place_lid(
            hammy,
            state["active_src"]["plate_seq"],
            state["active_src"]["lid_seq"],
            transportMode = 1,
            ejectToolWhenFinish=0
        )
        # Update state
        state["lid_holder_src"]["current_lid"] = None
        
        #   Move plate w lid from active_src_pos to src_stack_1 (or 2 if 1 is full) - essentially to next done src position
        cmd_grip_get_plate_with_lid(
            hammy, 
            state["active_src"]["plate_seq"], 
            state["active_src"]["lid_seq"],
            transportMode = 2,
        )
        # Update state
        state["gripped_plate"]["current_plate"] = state["active_src"]["current_plate"]
        state["gripped_plate"]["current_lid"]   = state["active_src"]["current_plate"]
        state["active_src"]["current_plate"] = None

        next_done_src_stack_name, next_done_src_stack_index = hp.get_next_done_stacked_plate(state,SRC_STACK_LIMIT,"src")#get_next_done_src_plate_pos(state)
        next_done_src_plate_seq = state[next_done_src_stack_name][next_done_src_stack_index]["plate_seq"]
        next_done_src_lid_seq = state[next_done_src_stack_name][next_done_src_stack_index]["lid_seq"] 
        cmd_grip_place_plate_with_lid(
            hammy,
            next_done_src_plate_seq,
            next_done_src_lid_seq,
            transportMode = 2,
        )
        # Update state
        state[next_done_src_stack_name][next_done_src_stack_index]["current_plate"] = state["gripped_plate"]["current_plate"]
        state["gripped_plate"]["current_plate"] = None
        state["gripped_plate"]["current_lid"]   = None


        # state update: Add one plate as already treated
        state["treated_src_plates_count"] += 1
        to_print = state["treated_src_plates_count"]
        print(f"Plates Processed: {to_print}/{src_plates_count}")

    # Check if there is a plate on the active tgt site. if so, put it back.
    if state["active_tgt"]["current_plate"] != None:
        put_tgt_plate_in_done_tgt_stack()
    json.dump(new_mapping, open("./FINAL_mapping.json",'w'))
    print("\n-----\nCherry-picking Protocol Done\n-----\n")
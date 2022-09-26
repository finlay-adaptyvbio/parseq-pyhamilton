import json
import math
import helpers as hp
from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType, Plate384, Tip96, INITIALIZE, GRIP_GET, GRIP_PLACE, tip_pick_up, tip_eject, aspirate, dispense)


SRC_STACK_LIMIT = 6
TGT_STACK_LIMIT = 6

state = {
    "treated_src_plates_count": 0, # Number of source plates that have been treated (everything has been extracted from them)
    "treated_tgt_plates_count":0, # Number of target plates that have been treated (they have been filled as much as possible)
    "gripped_plate":{
        "plate_seq": "Gre_384_0008_0001",
        "lid_seq": "Gre_384_0008_0001_lid",
        "current_plate": None,
        "current_lid": False
    },
    "active_src": {
        "plate_seq": "cp_active_src_plate",
        "lid_seq": "cp_active_src_lid",
        "current_plate": None
    },
    "active_tgt": {
        "plate_seq": "cp_active_tgt_plate",
        "lid_seq": "cp_active_tgt_lid",
        "current_plate": None,
        "next_well_id": 0,
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
        "seq": "MlStar1000ulHighVolumeTip"
    },
    "src_stack_1": [ # Bottom to top
        {
            "plate_seq": "Gre_384_0001_0001",
            "lid_seq": "Gre_384_0001_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0001_0002",
            "lid_seq": "Gre_384_0001_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0001_0003",
            "lid_seq": "Gre_384_0001_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0001_0004",
            "lid_seq": "Gre_384_0001_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0001_0005",
            "lid_seq": "Gre_384_0001_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0001_0006",
            "lid_seq": "Gre_384_0001_0006_lid",
            "current_plate": None
        },
    ],
    "src_stack_2": [ # Bottom to top
        {
            "plate_seq": "Gre_384_0002_0001",
            "lid_seq": "Gre_384_0002_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0002_0002",
            "lid_seq": "Gre_384_0002_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0002_0003",
            "lid_seq": "Gre_384_0002_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0002_0004",
            "lid_seq": "Gre_384_0002_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0002_0005",
            "lid_seq": "Gre_384_0002_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0002_0006",
            "lid_seq": "Gre_384_0002_0006_lid",
            "current_plate": None
        },
    ], 
    "src_stack_3": [ # Bottom to top
        {
            "plate_seq": "Gre_384_0003_0001",
            "lid_seq": "Gre_384_0003_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0003_0002",
            "lid_seq": "Gre_384_0003_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0003_0003",
            "lid_seq": "Gre_384_0003_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0003_0004",
            "lid_seq": "Gre_384_0003_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0003_0005",
            "lid_seq": "Gre_384_0003_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0003_0006",
            "lid_seq": "Gre_384_0003_0006_lid",
            "current_plate": None
        },
    ],
    "tgt_stack_1":[
        {
            "plate_seq": "Gre_384_0004_0001",
            "lid_seq": "Gre_384_0004_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0004_0002",
            "lid_seq": "Gre_384_0004_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0004_0003",
            "lid_seq": "Gre_384_0004_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0004_0004",
            "lid_seq": "Gre_384_0004_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0004_0005",
            "lid_seq": "Gre_384_0004_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0004_0006",
            "lid_seq": "Gre_384_0004_0006_lid",
            "current_plate": None
        },
    ],
    "tgt_stack_2":[
        {
            "plate_seq": "Gre_384_0005_0001",
            "lid_seq": "Gre_384_0005_0001_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0005_0002",
            "lid_seq": "Gre_384_0005_0002_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0005_0003",
            "lid_seq": "Gre_384_0005_0003_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0005_0004",
            "lid_seq": "Gre_384_0005_0004_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0005_0005",
            "lid_seq": "Gre_384_0005_0005_lid",
            "current_plate": None
        },
        {
            "plate_seq": "Gre_384_0005_0006",
            "lid_seq": "Gre_384_0005_0006_lid",
            "current_plate": None
        },
    ]
}


# -------------------------
#         SETUP
# -------------------------


# Get the input list of all the wells for each plate
plates = hp.get_wells_of_interest_from_csv("C:\\Projects\\Adaptyv Bio\\pyhamilton-cherrypicking\\unique_sequences_well_index.csv")

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

# Ask the user to set the plates (in stacks 1 and 2)
placed_in_stack = 0
index_in_current_stack = 0
stack_to_place_in = "3"
for plate in plates:
    # Fill stack 1 and 2, leave stack 3 empty
    if placed_in_stack == 6:
        stack_to_place_in = "2"
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

json.dump(state, open("./state.json",'w'))

# -------------------------
#        EXECUTION
# -------------------------

# Need functions to:
#   [X] get the current stacked src plate from the state - returns the stack it is in and the index to know how high it is
#   [X] get the current stacked tgt plate from the state - returns the stack it is in and the index to know how high it is
#   [X] get the next done src plate position from the state - returns the potential position (stack and index to know how high it is)
#   [X] get the next done tgt plate position from the state - returns the potential position (stack and index to know how high it is)

def get_next_stacked_src_plate(state:dict):
    treated_src_plates_count = state["treated_src_plates_count"]
    stack_nb = "2"
    if not(treated_src_plates_count < 12):
        return None, None
    
    if (treated_src_plates_count > SRC_STACK_LIMIT): # Assuming we only have 2 stacks
        stack_nb = "3"

    stack_name = f'src_stack_{stack_nb}'
    upper_most_plate = 0
    for pos in state[stack_name]:
        if pos["current_plate"] == None:
            break
        if upper_most_plate == SRC_STACK_LIMIT:
            break
        upper_most_plate += 1

    index_in_stack = upper_most_plate - 1
    return stack_name, index_in_stack

def get_next_stacked_tgt_plate(state:dict):
    treated_tgt_plates_count = state["treated_tgt_plates_count"]
    if not(treated_tgt_plates_count < TGT_STACK_LIMIT):
        return None, None
    
    stack_name = f'tgt_stack_2'
    upper_most_plate = 0
    for pos in state[stack_name]:
        if pos["current_plate"] == None:
            break
        if upper_most_plate == TGT_STACK_LIMIT:
            break
        upper_most_plate += 1
    
    index_in_stack = upper_most_plate - 1
    return stack_name, index_in_stack

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
            break
        upper_most_plate += 1
    
    index_in_stack = upper_most_plate - 1
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
            break
        upper_most_plate += 1
    
    index_in_stack = upper_most_plate - 1
    return stack_name, index_in_stack
    

def cmd_grip_get_plate_with_lid(
        hamilton_interface:HamiltonInterface, 
        plateSequence:str, 
        lidSequence:str, 
        toolSequence:str = 'COREGripTool_OnWaste_1000ul_0001',
        gripForce:float = 3,
    ):
    cmd_id = hamilton_interface.send_command(GRIP_GET, 
                                plateSequence      = plateSequence,
                                lidSequence        = lidSequence,
                                toolSequence       = toolSequence,
                                gripForce          = gripForce,
                                gripperToolChannel = 2,
                                gripHeight         = 11.0,
                                transportMode      = 1 )
    print(hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True))

def cmd_grip_place_plate_with_lid(
        hamilton_interface:HamiltonInterface,
        plateSequence:str, 
        lidSequence:str, 
        toolSequence:str = 'COREGripTool_OnWaste_1000ul_0001',
    ):
    cmd_id = hamilton_interface.send_command(GRIP_PLACE,
                                plateSequence = plateSequence,
                                lidSequence   = lidSequence,
                                toolSequence  = toolSequence,
                                transportMode = 1 )
    print(hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True))

def cmd_grip_get_lid(
        hamilton_interface:HamiltonInterface, 
        plateSequence:str, 
        lidSequence:str, 
        toolSequence:str = 'COREGripTool_OnWaste_1000ul_0001',
        gripForce:float = 3,
    ):
    cmd_id = hamilton_interface.send_command(GRIP_GET, 
                                plateSequence      = plateSequence,
                                lidSequence        = lidSequence,
                                toolSequence       = toolSequence,
                                gripForce          = gripForce,
                                gripperToolChannel = 2,
                                gripHeight         = 3.0,
                                transportMode      = 1 )
    print(hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True))

def cmd_grip_place_lid(
        hamilton_interface:HamiltonInterface,
        plateSequence:str,
        lidSequence:str,
        toolSequence:str = 'COREGripTool_OnWaste_1000ul_0001',
    ):
    cmd_grip_place_plate_with_lid(hamilton_interface,plateSequence,lidSequence,toolSequence)


layfile_abs_path = ''
lmgr = LayoutManager(layfile_abs_path)

with HamiltonInterface(simulate=True) as hammy:
    hammy.wait_on_response(hammy.send_command(INITIALIZE))
    print('\nInitialized!')


    # Loop over source plates 
    while state["treated_src_plates_count"] < src_plates_count:

        # Get new active src
        #   Move plate w lid from src_stack_3 with lid to active_src_pos
        next_src_stack_name, next_src_stack_index = get_next_stacked_src_plate(state)
        next_src_plate_seq = state[next_src_stack_name][next_src_stack_index]["plate_seq"]
        next_src_lid_seq = state[next_src_stack_name][next_src_stack_index]["lid_seq"] 
        cmd_grip_get_plate_with_lid(
            hammy,
            next_src_plate_seq,
            next_src_lid_seq
        )
        # Update state
        state["gripped_plate"]["current_plate"] = state[next_src_stack_name][next_src_stack_index]["current_plate"]
        state["gripped_plate"]["current_lid"]   = state[next_src_stack_name][next_src_stack_index]["current_plate"]
        state[next_src_stack_name][next_src_stack_index]["current_plate"] = None

        cmd_grip_place_plate_with_lid(
            hammy, 
            state["active_src"]["plate_seq"],
            state["active_src"]["lid_seq"]
        )
        # Update state
        state["active_src"]["current_plate"] = state["gripped_plate"]["current_plate"]
        state["gripped_plate"]["current_plate"] = None
        state["gripped_plate"]["current_lid"]   = None
        
        #   move lid from active_src_pos to src_lid_holder 
        cmd_grip_get_lid(
            hammy,
            state["active_src"]["plate_seq"],
            state["active_src"]["lid_seq"]
        )
        state["gripped_plate"]["current_lid"] = state["active_src"]["current_plate"]

        cmd_grip_place_lid(
            hammy,
            state["lid_holder_src"]["plate_seq"],
            state["lid_holder_src"]["lid_seq"]
        )
        # Update state
        state["lid_holder_src"]["current_lid"] = state["gripped_plate"]["current_lid"]
        state["gripped_plate"]["current_lid"] = None

        def get_target_plate():
            # Get new active tgt
            #   Move plate w lid from tgt_stack_2 with lid to active_tgt_pos
            next_tgt_stack_name, next_tgt_stack_index = get_next_stacked_tgt_plate(state)
            next_tgt_plate_seq = state[next_tgt_stack_name][next_tgt_stack_index]["plate_seq"]
            next_tgt_lid_seq = state[next_tgt_stack_name][next_tgt_stack_index]["lid_seq"] 
            cmd_grip_get_plate_with_lid(
                hammy, 
                next_tgt_plate_seq,
                next_tgt_lid_seq
            )
            # Update state
            state["gripped_plate"]["current_plate"] = state[next_tgt_stack_name][next_tgt_stack_index]["current_plate"]
            state["gripped_plate"]["current_lid"]   = state[next_tgt_stack_name][next_tgt_stack_index]["current_plate"]
            state[next_tgt_stack_name][next_tgt_stack_index]["current_plate"] = None

            cmd_grip_place_plate_with_lid(
                hammy, 
                state["active_tgt"]["plate_seq"], 
                state["active_tgt"]["lid_seq"]
            )
            # Update state
            state["active_tgt"]["current_plate"] = state["gripped_plate"]["current_plate"]
            state["gripped_plate"]["current_plate"] = None
            state["gripped_plate"]["current_lid"]   = None
            
            #   move lid from active_tgt_pos to tgt_lid_holder
            cmd_grip_get_lid(
                hammy,
                state["active_tgt"]["plate_seq"],
                state["active_tgt"]["lid_seq"]
            )
            state["gripped_plate"]["current_lid"] = state["active_tgt"]["current_plate"]

            cmd_grip_place_lid(
                hammy,
                state["lid_holder_tgt"]["plate_seq"],
                state["lid_holder_tgt"]["lid_seq"]
            )
            # Update state
            state["lid_holder_tgt"]["current_lid"] = state["gripped_plate"]["current_lid"]
            state["gripped_plate"]["current_lid"] = None

        get_target_plate()

        # Cherry Pick!
        active_src_plate_name = state["active_src"]["current_plate"]
        
        wells_to_pick = hp.convertPlatePositionsToIndeces( plates[active_src_plate_name] )

        remaining_wells_of_interest = src_wells_of_interest_count

        # Settings for cherry-picking procedures
        liquid_class = 'HighVolume_Water_DispenseJet_Part'

        for well_to_pick in wells_to_pick:
            # Check if there still are tips (state["tips"]["next_tip_index"])
            while state["tips"]["next_tip_index"] >= state["tips"]["max_tips_count"]:
                print("--------\nAttention: No more tips. Please add a new tips set.\n--------")
                # Confirm with user the that the active src and tgt sites are empty (there are no plates)
                user_input_new_tips_added = False
                while user_input_new_tips_added != 'yes':
                    user_input_new_tips_added = input(f"Type 'yes' to confirm that new tips have been added:\n")
                
                # Get new next_tip_position
                next_pipette_tip_index = get_pipette_tip_next_pos_from_user()
                state["tips"]["next_tip_index"] = next_pipette_tip_index


            # Check if still places in tgt plate
            if state["active_tgt"]["next_well_id"] >= state["active_tgt"]["well_count"]:
                print("[Notice] active target plate is full. Replacing it...")
                # Close Lid
                cmd_grip_get_lid(
                    hammy,
                    state["lid_holder_tgt"]["plate_seq"],
                    state["lid_holder_tgt"]["lid_seq"]
                )
                # Update state
                state["gripped_plate"]["current_lid"] = state["lid_holder_tgt"]["current_lid"]
                state["lid_holder_tgt"]["current_lid"] = None

                cmd_grip_place_lid(
                    hammy,
                    state["active_tgt"]["plate_seq"],
                    state["active_tgt"]["lid_seq"]
                )
                # Update state
                state["lid_holder_tgt"]["current_lid"] = None

                def put_tgt_plate_in_done_tgt_stack():
                    # Put plate in done target stack
                    cmd_grip_get_plate_with_lid(
                        hammy, 
                        state["active_tgt"]["plate_seq"], 
                        state["active_tgt"]["lid_seq"]
                    )
                    # Update state
                    state["gripped_plate"]["current_plate"] = state["gripped_plate"]["current_plate"]
                    state["gripped_plate"]["current_lid"]   = state["gripped_plate"]["current_plate"]
                    state["active_tgt"]["current_plate"]    = None


                    next_done_tgt_stack_name, next_done_tgt_stack_index = get_next_done_tgt_plate_pos(state)
                    next_done_tgt_plate_seq = state[next_done_tgt_stack_name][next_done_tgt_stack_index]["plate_seq"]
                    next_done_tgt_lid_seq = state[next_done_tgt_stack_name][next_done_tgt_stack_index]["lid_seq"] 
                    cmd_grip_place_plate_with_lid(
                        hammy, 
                        next_done_tgt_plate_seq,
                        next_done_tgt_lid_seq
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
            
            # Run cherry-picking for one well
            tip_resource = lmgr.assign_unused_resource(ResourceType(Tip96, state["tips"]["seq"]))
            tip_pos = (tip_resource, state["tips"]["next_tip_index"])
            # Update next tip position in state
            state["tips"]["next_tip_index"] += 1

            src_plate_type = ResourceType(Plate384, state["active_src"]["plate_seq"])
            src_plate_resource = lmgr.assign_unused_resource(src_plate_type)
            well_pos_in_src_plate = (src_plate_resource, well_to_pick)

            tgt_plate_type = ResourceType(Plate384, state["active_tgt"]["plate_seq"])
            tgt_plate_resource = lmgr.assign_unused_resource(tgt_plate_type)
            well_pos_in_tgt_plate = (tgt_plate_resource, state["active_tgt"]["next_well_id"])
            # Update next target well position in state
            state["active_tgt"]["next_well_id"] += 1

            # Aspirate from well of interest
            tip_pick_up(hammy, [tip_pos])
            aspirate(hammy, [well_pos_in_src_plate], [.001], liquidClass = liquid_class)

            # Dispense into target well
            dispense(hammy, [well_pos_in_tgt_plate], [.001], liquidClass = liquid_class)
            tip_eject(hammy, [tip_pos])
            
            # Print Progress to user
            remaining_wells_of_interest -= 1
            print(f"Progress: {remaining_wells_of_interest}/{src_wells_of_interest_count}", )
        

        # Store active src (assuming it is done)
        #   move lid from src_lid_holder to active_src_pos
        cmd_grip_get_lid(
            hammy,
            state["lid_holder_src"]["plate_seq"],
            state["lid_holder_src"]["lid_seq"]
        )
        # Update state
        state["gripped_plate"]["current_lid"] = state["lid_holder_src"]["current_lid"]
        state["lid_holder_src"]["current_lid"] = None

        cmd_grip_place_lid(
            hammy,
            state["active_src"]["plate_seq"],
            state["active_src"]["lid_seq"]
        )
        # Update state
        state["lid_holder_src"]["current_lid"] = None
        
        #   Move plate w lid from active_src_pos to src_stack_1 (or 2 if 1 is full) - essentially to next done src position
        cmd_grip_get_plate_with_lid(
            hammy, 
            state["active_src"]["plate_seq"], 
            state["active_src"]["lid_seq"]
        )
        # Update state
        state["gripped_plate"]["current_plate"] = state["active_src"]["current_plate"]
        state["gripped_plate"]["current_lid"]   = state["active_src"]["current_plate"]
        state["active_src"]["current_plate"] = None

        next_done_src_stack_name, next_done_src_stack_index = get_next_done_src_plate_pos(state)
        next_done_src_plate_seq = state[next_done_src_stack_name][next_done_src_stack_index]["plate_seq"]
        next_done_src_lid_seq = state[next_done_src_stack_name][next_done_src_stack_index]["lid_seq"] 
        cmd_grip_place_plate_with_lid(
            hammy,
            next_done_src_plate_seq,
            next_done_src_lid_seq
        )
        # Update state
        state[next_done_src_stack_name][next_done_src_stack_index]["current_plate"] = state["gripped_plate"]["current_plate"]
        state["gripped_plate"]["current_plate"] = None
        state["gripped_plate"]["current_lid"]   = None


        # state update: Add one plate as already treated
        state["treated_src_plates_count"] += 1

    # Check if there is a plate on the active tgt site. if so, put it back.
    if state["treated_src_plates_count"] < tgt_plate_count:
        put_tgt_plate_in_done_tgt_stack()
    print("\n-----\nCherry-picking Protocol Done\n-----\n")
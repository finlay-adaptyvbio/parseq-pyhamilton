from pyhamilton import (HamiltonInterface)
import cmd_wrappers as cmdw
import helpers as hp

def get_target_plate(state:dict, hamilton_interface:HamiltonInterface, src_stack_limit:int, ejectToolWhenFinish:bool = True):
    # Get new active tgt
    #   Move plate w lid from tgt_stack_2 with lid to active_tgt_pos
    next_tgt_stack_name, next_tgt_stack_index = hp.get_next_stacked_plate(state, src_stack_limit, "tgt")
    next_tgt_plate_seq = state[next_tgt_stack_name][next_tgt_stack_index]["plate_seq"]
    next_tgt_lid_seq = state[next_tgt_stack_name][next_tgt_stack_index]["lid_seq"] 
    str_msg = f"-- Move plate from target stack to active [Press Enter]"
    #input(str_msg)
    cmdw.grip_get_plate_with_lid(
        hamilton_interface, 
        next_tgt_plate_seq,
        next_tgt_lid_seq,
        transportMode = 2,
    )
    # Update state
    state["gripped_plate"]["current_plate"] = state[next_tgt_stack_name][next_tgt_stack_index]["current_plate"]
    state["gripped_plate"]["current_lid"]   = state[next_tgt_stack_name][next_tgt_stack_index]["current_plate"]
    state[next_tgt_stack_name][next_tgt_stack_index]["current_plate"] = None

    cmdw.grip_place_plate_with_lid(
        hamilton_interface, 
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
    cmdw.grip_get_lid(
        hamilton_interface,
        state["active_tgt"]["plate_seq"],
        state["active_tgt"]["lid_seq"],
        transportMode = 1
    )
    state["gripped_plate"]["current_lid"] = state["active_tgt"]["current_plate"]
    
    cmdw.grip_place_lid(
        hamilton_interface,
        state["lid_holder_tgt"]["plate_seq"],
        state["lid_holder_tgt"]["lid_seq"],
        transportMode = 1,
        ejectToolWhenFinish = ejectToolWhenFinish
    )
    # Update state
    state["lid_holder_tgt"]["current_lid"] = state["gripped_plate"]["current_lid"]
    state["gripped_plate"]["current_lid"] = None

def throw_active_tip_rack_into_waste(state:dict, hamilton_interface:HamiltonInterface):
    # Throw Tips in Trash
    cmdw.grip_get_96_tip_rack(
        hamilton_interface, 
        state["tips"]["seq"]
    )
    # Update state
    state["tips"]["current"] = None
    state["gripped_plate"]["current_plate"] = "tip_rack"

    cmdw.grip_place_96_tip_rack(
        hamilton_interface,
        state["tips"]["seq_waste"]
    )
    state["gripped_plate"]["current_plate"] = None

def put_tgt_plate_in_done_tgt_stack(state:dict,hamilton_interface:HamiltonInterface, src_stack_limit:int, ejectToolWhenFinish:int = 1):
    cmdw.grip_get_lid(
        hamilton_interface,
        state["lid_holder_tgt"]["plate_seq"],
        state["lid_holder_tgt"]["lid_seq"],
        transportMode = 1,
    )
    # Update state
    state["gripped_plate"]["current_lid"] = state["lid_holder_tgt"]["current_lid"]
    state["lid_holder_tgt"]["current_lid"] = None

    cmdw.grip_place_lid(
        hamilton_interface,
        state["active_tgt"]["plate_seq"],
        state["active_tgt"]["lid_seq"],
        transportMode = 1,
        ejectToolWhenFinish = 0
    )
    # Update state
    state["lid_holder_tgt"]["current_lid"] = None
    # Put plate in done target stack
    cmdw.grip_get_plate_with_lid(
        hamilton_interface, 
        state["active_tgt"]["plate_seq"], 
        state["active_tgt"]["lid_seq"],
        transportMode = 2
    )
    # Update state
    state["gripped_plate"]["current_plate"] = state["gripped_plate"]["current_plate"]
    state["gripped_plate"]["current_lid"]   = state["gripped_plate"]["current_plate"]
    state["active_tgt"]["current_plate"]    = None


    next_done_tgt_stack_name, next_done_tgt_stack_index = hp.get_next_done_stacked_plate(state,src_stack_limit,"tgt")#get_next_done_tgt_plate_pos(state)
    next_done_tgt_plate_seq = state[next_done_tgt_stack_name][next_done_tgt_stack_index]["plate_seq"]
    next_done_tgt_lid_seq = state[next_done_tgt_stack_name][next_done_tgt_stack_index]["lid_seq"] 
    cmdw.grip_place_plate_with_lid(
        hamilton_interface, 
        next_done_tgt_plate_seq,
        next_done_tgt_lid_seq,
        transportMode = 2,
        ejectToolWhenFinish = ejectToolWhenFinish
    )
    # Update state
    state[next_done_tgt_stack_name][next_done_tgt_stack_index]["current_plate"] = state["gripped_plate"]["current_plate"]
    state["gripped_plate"]["current_plate"] = None
    state["gripped_plate"]["current_lid"]   = None


#   Move plate w lid from src_stack_3 with lid to active_src_pos
def move_next_src_plate_from_stack_to_active_position(state:dict, hamilton_interface:HamiltonInterface, src_stack_limit:int):
    next_src_stack_name, next_src_stack_index = hp.get_next_stacked_plate(state, src_stack_limit, "src")
    print("next stack source stack name :", next_src_stack_name)
    print("next stack source stack index:", next_src_stack_index)
    # print("state:", state[next_src_stack_name][next_src_stack_index])
    next_src_plate_seq = state[next_src_stack_name][next_src_stack_index]["plate_seq"]
    next_src_lid_seq = state[next_src_stack_name][next_src_stack_index]["lid_seq"] 
    str_msg = f"-- Move plate from source to active [Press Enter]"
    #input(str_msg)
    cmdw.grip_get_plate_with_lid(
        hamilton_interface,
        next_src_plate_seq,
        next_src_lid_seq,
        transportMode = 2
    )
    # Update state
    state["gripped_plate"]["current_plate"] = state[next_src_stack_name][next_src_stack_index]["current_plate"]
    state["gripped_plate"]["current_lid"]   = state[next_src_stack_name][next_src_stack_index]["current_plate"]
    state[next_src_stack_name][next_src_stack_index]["current_plate"] = None
    
    #print('gripped plate:',state["gripped_plate"]["current_plate"])
    cmdw.grip_place_plate_with_lid (
        hamilton_interface, 
        state["active_src"]["plate_seq"],
        state["active_src"]["lid_seq"],
        transportMode = 2,
        ejectToolWhenFinish=0
    )
    # Update state
    state["active_src"]["current_plate"] = state["gripped_plate"]["current_plate"]
    state["gripped_plate"]["current_plate"] = None
    state["gripped_plate"]["current_lid"]   = None

def move_active_src_lid_to_lid_holder(state:dict, hamilton_interface:HamiltonInterface):
    cmdw.grip_get_lid(
        hamilton_interface,
        state["active_src"]["plate_seq"],
        state["active_src"]["lid_seq"],
        transportMode = 1,
    )
    state["gripped_plate"]["current_lid"] = state["active_src"]["current_plate"]

    cmdw.grip_place_lid(
        hamilton_interface,
        state["lid_holder_src"]["plate_seq"],
        state["lid_holder_src"]["lid_seq"],
        transportMode = 1,
        ejectToolWhenFinish = 0
    )
    # Update state
    state["lid_holder_src"]["current_lid"] = state["gripped_plate"]["current_lid"]
    state["gripped_plate"]["current_lid"] = None

def move_tip_rack_from_stack_to_active_tip_position(state:dict, hamilton_interface:HamiltonInterface, tip_stack_limit:int):
    next_tip_rack_stack_name, next_tip_rack_stack_index = hp.get_next_stacked_tip_rack(state, tip_stack_limit)
    next_tip_rack_seq = state[next_tip_rack_stack_name][next_tip_rack_stack_index]["seq"]
    str_msg = f"-- Move tip rack from {next_tip_rack_stack_name}-{str(next_tip_rack_stack_index)} to active [Press Enter]"
    #input(str_msg)
    cmdw.grip_get_96_tip_rack(
        hamilton_interface,
        next_tip_rack_seq,
    )
    # Update state
    state["gripped_plate"]["current_plate"] = "tip_rack"
    state[next_tip_rack_stack_name][next_tip_rack_stack_index]["current"] = None
    
    cmdw.grip_place_96_tip_rack( #cmd_grip_place_plate_with_lid(
        hamilton_interface, 
        state["tips"]["seq_for_moving_from_to_stack"], 
    )
    # Update state
    state["tips"]["current"] = state["gripped_plate"]["current_plate"]
    state["gripped_plate"]["current_plate"] = None


def move_full_tgt_plate_from_active_position_to_stack(state:dict, hamilton_interface:HamiltonInterface, src_stack_limit:int):
    # Close Lid
    cmdw.grip_get_lid(
        hamilton_interface,
        state["lid_holder_tgt"]["plate_seq"],
        state["lid_holder_tgt"]["lid_seq"],
        transportMode = 1,
    )
    # Update state
    state["gripped_plate"]["current_lid"] = state["lid_holder_tgt"]["current_lid"]
    state["lid_holder_tgt"]["current_lid"] = None

    cmdw.grip_place_lid(
        hamilton_interface,
        state["active_tgt"]["plate_seq"],
        state["active_tgt"]["lid_seq"],
        transportMode = 1,
        ejectToolWhenFinish=0
    )
    # Update state
    state["lid_holder_tgt"]["current_lid"] = None

    # Put target plate back
    #   Move plate w lid from active_tgt_pos to tgt_stack_1 (or 2 if 1 is full) - essentially to next done tgt position
    cmdw.grip_get_plate_with_lid(
        hamilton_interface, 
        state["active_tgt"]["plate_seq"], 
        state["active_tgt"]["lid_seq"],
        transportMode = 2,
    )
    # Update state
    state["gripped_plate"]["current_plate"] = state["active_tgt"]["current_plate"]
    state["gripped_plate"]["current_lid"]   = state["active_tgt"]["current_plate"]
    state["active_tgt"]["current_plate"] = None

    next_done_tgt_stack_name, next_done_tgt_stack_index = hp.get_next_done_stacked_plate(state, src_stack_limit, "tgt")#get_next_done_tgt_plate_pos(state)
    next_done_tgt_plate_seq = state[next_done_tgt_stack_name][next_done_tgt_stack_index]["plate_seq"]
    next_done_tgt_lid_seq = state[next_done_tgt_stack_name][next_done_tgt_stack_index]["lid_seq"] 
    cmdw.grip_place_plate_with_lid(
        hamilton_interface,
        next_done_tgt_plate_seq,
        next_done_tgt_lid_seq,
        transportMode = 2,
    )
    # Update state
    state[next_done_tgt_stack_name][next_done_tgt_stack_index]["current_plate"] = state["gripped_plate"]["current_plate"]
    state["gripped_plate"]["current_plate"] = None
    state["gripped_plate"]["current_lid"]   = None
    
def move_src_plate_from_active_pos_to_done_stack(state:dict, hamilton_interface:HamiltonInterface, src_stack_limit:int):
    #   move lid from src_lid_holder to active_src_pos
    cmdw.grip_get_lid(
        hamilton_interface,
        state["lid_holder_src"]["plate_seq"],
        state["lid_holder_src"]["lid_seq"],
        transportMode = 1,
    )
    # Update state
    state["gripped_plate"]["current_lid"] = state["lid_holder_src"]["current_lid"]
    state["lid_holder_src"]["current_lid"] = None

    cmdw.grip_place_lid(
        hamilton_interface,
        state["active_src"]["plate_seq"],
        state["active_src"]["lid_seq"],
        transportMode = 1,
        ejectToolWhenFinish=0
    )
    # Update state
    state["lid_holder_src"]["current_lid"] = None
    
    #   Move plate w lid from active_src_pos to src_stack_1 (or 2 if 1 is full) - essentially to next done src position
    cmdw.grip_get_plate_with_lid(
        hamilton_interface, 
        state["active_src"]["plate_seq"], 
        state["active_src"]["lid_seq"],
        transportMode = 2,
    )
    # Update state
    state["gripped_plate"]["current_plate"] = state["active_src"]["current_plate"]
    state["gripped_plate"]["current_lid"]   = state["active_src"]["current_plate"]
    state["active_src"]["current_plate"] = None

    next_done_src_stack_name, next_done_src_stack_index = hp.get_next_done_stacked_plate(state,src_stack_limit,"src")#get_next_done_src_plate_pos(state)
    next_done_src_plate_seq = state[next_done_src_stack_name][next_done_src_stack_index]["plate_seq"]
    next_done_src_lid_seq = state[next_done_src_stack_name][next_done_src_stack_index]["lid_seq"] 
    cmdw.grip_place_plate_with_lid(
        hamilton_interface,
        next_done_src_plate_seq,
        next_done_src_lid_seq,
        transportMode = 2,
    )
    # Update state
    state[next_done_src_stack_name][next_done_src_stack_index]["current_plate"] = state["gripped_plate"]["current_plate"]
    state["gripped_plate"]["current_plate"] = None
    state["gripped_plate"]["current_lid"]   = None
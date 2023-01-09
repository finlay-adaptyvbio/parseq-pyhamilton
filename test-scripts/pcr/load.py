import os
import pandas as pd
import json
import helpers as hp

INPUT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "new_mapping_2.csv")#"test_data","2p_more_than_2_tgt_p.csv")

def remove_done_wells_from_csv(prev_csv_absolute_path:str, done_map_file_path:str, output_csv_path:str) -> dict:
    """
    Extract wells across one or more plates to be cherry-picked from a .csv file that has the following format <Unique Sequence>,<Plate Name> <Well Position>, <Plate Name> <Well Position>, ... So the first column contains the unique sequence and all the columns after that are where this sequence is found (plate and well) 
    Arguments:
        csv_absolut_path: string of the absolute path of the csv file to be read
    Returns:
        Dictionary with keys as plate names and values are lists that contain all the positions (as strings) of the wells of interest 
    """
    done_map = json.load(open(done_map_file_path,'r'))
    dataframe = pd.read_csv(prev_csv_absolute_path, header=None)
    unique_well_poss = dataframe[1].to_list()
    idx_of_done = []
    
    
    #for i in range(len(unique_well_poss)):
    for i in range(len(unique_well_poss)):     
        unique_well_pos = unique_well_poss[i]
        plate, well_pos = unique_well_pos.split()
        well_idx = hp.convertPlatePositionToIndex(well_pos)

        pos_to_check = plate + "_" + str(well_idx)
        
        for dest_pos in done_map:
            src_pos = done_map[dest_pos]
            if src_pos == pos_to_check: # Already done src
                # Delete this row from Dataframe
                #dataframe = dataframe.drop(row)
                idx_of_done.append(i)
                #print("removed", pos_to_check)
                break
    
    idx_of_done.sort(reverse=True)
    for i in range(len(idx_of_done)):
        
        unique_well_poss.pop(idx_of_done[i])

    new_df = pd.DataFrame(unique_well_poss)
    new_df.to_csv(output_csv_path, header=False) 
        
def get_last_tgt_well_used_in_current_plate(map_file_path:str, new_input_csv_file_path:str):
    plate = None
    last_well_id = None


    done_map = json.load(open(map_file_path,'r'))
    done_map.keys()
    dataframe = pd.read_csv(new_input_csv_file_path, header=None)
    filtered_unique_well_poss = dataframe[1].to_list()


    # Find plate that exist in df and the done map, means it is not done
    for i in range(len(filtered_unique_well_poss)):
        filtered_unique_well_pos = filtered_unique_well_poss[i]
        filtered_plate, filtered_well_pos = filtered_unique_well_pos.split()

        map_keys_of_interest = [ k for k in done_map.keys() if k.startswith(filtered_plate)]
        if len(map_keys_of_interest) > 0:
            # found the plate
            plate = filtered_plate
            # get the last well done


        well_idx = hp.convertPlatePositionToIndex(filtered_unique_well_poss)

    
    return plate, last_well_id


def get_next_tgt_well_used_in_current_plate(state_saved_file_path:str):
    state = json.load(open(state_saved_file_path,'r'))
    plate = state["active_tgt"]["current_plate"]
    next_well_id = state["active_tgt"]["next_well_id"]

    print("current plate:", plate)
    print("next well id:", next_well_id)
    return plate, next_well_id
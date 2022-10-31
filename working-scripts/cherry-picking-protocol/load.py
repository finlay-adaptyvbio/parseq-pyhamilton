from email import header
import os
import pandas as pd
import json
import string
import helpers as hp

INPUT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "new_mapping_2.csv")#"test_data","2p_more_than_2_tgt_p.csv")

done_map = json.load(open('./L_mapping.json','r'))

def remove_done_wells_from_csv(csv_absolute_path:str, output_csv_path:str) -> dict:
    """
    Extract wells across one or more plates to be cherry-picked from a .csv file that has the following format <Unique Sequence>,<Plate Name> <Well Position>, <Plate Name> <Well Position>, ... So the first column contains the unique sequence and all the columns after that are where this sequence is found (plate and well) 
    Arguments:
        csv_absolut_path: string of the absolute path of the csv file to be read
    Returns:
        Dictionary with keys as plate names and values are lists that contain all the positions (as strings) of the wells of interest 
    """

    dataframe = pd.read_csv(csv_absolute_path, header=None)
    unique_well_poss = dataframe[1].to_list()
    print(unique_well_poss)
    
    #for i in range(len(unique_well_poss)):
    for i, row in dataframe.iterrows():
        print("df")
        print(i, row)
        return

        unique_well_pos = unique_well_poss[i]
        plate, well_pos = unique_well_pos.split()
        well_idx = hp.convertPlatePositionToIndex(well_pos)

        pos_to_check = plate + "_" + str(well_idx)
        
        for dest_pos in done_map:
            src_pos = done_map[dest_pos]
            if src_pos == pos_to_check: # Already done src
                # Delete this row from Dataframe
                dataframe = dataframe.drop(row)
                print("removed", pos_to_check)
                break

    dataframe.to_csv(output_csv_path, index=False, header=False)

def remove_done_wells_from_csv_2(csv_absolute_path:str, output_csv_path:str) -> dict:
    """
    Extract wells across one or more plates to be cherry-picked from a .csv file that has the following format <Unique Sequence>,<Plate Name> <Well Position>, <Plate Name> <Well Position>, ... So the first column contains the unique sequence and all the columns after that are where this sequence is found (plate and well) 
    Arguments:
        csv_absolut_path: string of the absolute path of the csv file to be read
    Returns:
        Dictionary with keys as plate names and values are lists that contain all the positions (as strings) of the wells of interest 
    """

    dataframe = pd.read_csv(csv_absolute_path, header=None)
    unique_well_poss = dataframe[1].to_list()
    idx_of_done = []
    print(unique_well_poss)
    
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
    print(idx_of_done)
    idx_of_done.sort(reverse=True)
    for i in range(len(idx_of_done)):
        
        unique_well_poss.pop(idx_of_done[i])

    new_df = pd.DataFrame(unique_well_poss)
    new_df.to_csv(output_csv_path, header=False)#index=False) #, 
        


remove_done_wells_from_csv_2(INPUT_FILE_PATH, 'new_mapping_3.csv')
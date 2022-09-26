import string
import pandas as pd

def convertPlatePositionsToIndeces(plate_positions_to_pick:list, plate_type:str = 'Plate384') -> list :
    """
    Converts a list of strings representing the wells in columns as a number and the rows as letters ['A01', 'C12']
    Arguments:
        plate_positions_to_pick: list of strings
    Returns:
        A list of the same length as plate_positions_to_pick but instead of strings it will have integers representing the indeces 
    """
    alphabet = string.ascii_lowercase

    col_count = 24
    row_count = 16
    if plate_type == "Plate384":
        col_count = 24
        row_count = 16
    elif plate_type == "Plate96":
        col_count = 12
        row_count = 8
    else:
        raise ValueError(f"The plate_type provided '{plate_type}' is not supported.")

    plate_indeces:list = [] 
    for plate_pos in plate_positions_to_pick:
        row:int = alphabet.find(plate_pos[0].lower())
        if row >= row_count: 
            raise ValueError(f"Row provided exceeds the number of rows on the plate_type provided") 
        col:int = int(plate_pos[1:]) - 1
        if col >= col_count: 
            raise ValueError(f"Column provided exceeds the number of rows on the plate_type provided") 

        index:int = row_count * col + row
        plate_indeces.append(index)
        print(plate_pos, row, col, index)
    
    return plate_indeces

""" print(convertPlatePositionsToIndeces(['a1','a2','a03','p3'], 'Plate384')) """

def get_wells_of_interest_from_csv(csv_absolute_path:string) -> dict:
    """
    Extract wells across one or more plates to be cherry-picked from a .csv file that has the following format <Unique Sequence>,<Plate Name> <Well Position>, <Plate Name> <Well Position>, ... So the first column contains the unique sequence and all the columns after that are where this sequence is found (plate and well) 
    Arguments:
        csv_absolut_path: string of the absolute path of the csv file to be read
    Returns:
        Dictionary with keys as plate names and values are lists that contain all the positions (as strings) of the wells of interest 
    """
    plates = {}

    dataframe = pd.read_csv(csv_absolute_path, header=None)

    unique_well_poss = dataframe[1].to_list()
    
    for unique_well_pos in unique_well_poss:
        plate, well_pos = unique_well_pos.split()
        if not( plate in plates ):
            plates[plate] = []
        plates[plate].append(well_pos)

    return plates


import string
import pandas as pd


def convertPlatePositionToIndex(
    plate_position: str, plate_type: str = "Plate384"
) -> list:
    """
    Converts a strings representing the wells in columns as a number and the rows as letters ['A01', 'C12']
    Arguments:
        plate_position: strings
    Returns:
        integer representing the index in a default plate sequence (readable by PyHamilton scripts)
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

    row: int = alphabet.find(plate_position[0].lower())
    if row >= row_count:
        raise ValueError(
            f"Row provided exceeds the number of rows on the plate_type provided"
        )
    col: int = int(plate_position[1:]) - 1
    if col >= col_count:
        raise ValueError(
            f"Column provided exceeds the number of rows on the plate_type provided"
        )

    index: int = row_count * col + row

    # print(plate_position, row, col, index)

    return index


def convertPlatePositionsToIndices(
    plate_positions_to_pick: list, plate_type: str = "Plate384"
) -> list:
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

    plate_indeces: list = []
    for plate_pos in plate_positions_to_pick:
        row: int = alphabet.find(plate_pos[0].lower())
        if row >= row_count:
            raise ValueError(
                f"Row provided exceeds the number of rows on the plate_type provided"
            )
        col: int = int(plate_pos[1:]) - 1
        if col >= col_count:
            raise ValueError(
                f"Column provided exceeds the number of rows on the plate_type provided"
            )

        index: int = row_count * col + row
        plate_indeces.append(index)
        # print(plate_pos, row, col, index)

    return plate_indeces


""" print(convertPlatePositionsToIndeces(['a1','a2','a03','p3'], 'Plate384')) """


def get_wells_of_interest_from_csv(csv_absolute_path: string) -> dict:
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
        if not (plate in plates):
            plates[plate] = []
        plates[plate].append(well_pos)

    return plates


def get_next_stacked_plate(state: dict, stack_limit: int, src_or_tgt: str):
    """
    Identify the next stacked plate that can be picked up by the Hamilton.
    Arguments:
        state: dict of the current state of the machine.
        stack_limit: int maximum number of plates that can be placed on a stack.
        src_or_tgt: string either "src" or "tgt" to know which type of plate to look for in the state.
    Returns:
        Two strings that represent the position of the next plate to be taken and the stack it is in.
    """
    treated_plates_count = state[f"treated_{src_or_tgt}_plates_count"]
    # print("# treated plates: ", treated_plates_count)

    # Find which stack to take from
    stacks_full = int(treated_plates_count / stack_limit)
    stack_to_take_from_nb = stacks_full + 2
    stack_to_take_from = f"{src_or_tgt}_stack_{str(stack_to_take_from_nb)}"
    # print("will start treatment of: ", treated_plates_count + 1, "th plate")
    # print("stack to take from: ", stack_to_take_from)

    # print("Full stacks: ", stacks_full)

    # figure out the plate level to take (bottom = 0, top = 5)
    plate_index = 5
    for pos in reversed(state[stack_to_take_from]):
        if pos["current_plate"] != None:
            break
        plate_index -= 1
    # print("plate index: ", plate_index)
    return stack_to_take_from, plate_index


def get_next_done_stacked_plate(state: dict, stack_limit: int, src_or_tgt: str):
    """
    Identify the next stacked plate position that a plate can be placed in.
    Arguments:
        state: dict of the current state of the machine.
        stack_limit: int maximum number of plates that can be placed on a stack.
        src_or_tgt: string either "src" or "tgt" to know which type of plate to look for in the state.
    Returns:
        Two strings that represent the position of the next plate to be placed in and the stack it is in.
    """
    treated_plates_count = state[f"treated_{src_or_tgt}_plates_count"]
    # print("# treated plates: ", treated_plates_count)

    # Find which stack to take from
    stacks_full = int(treated_plates_count / stack_limit)
    stack_to_take_from_nb = stacks_full + 1
    stack_to_take_from = f"{src_or_tgt}_stack_{str(stack_to_take_from_nb)}"
    # print("will start treatment of: ", treated_plates_count + 1, "th plate")
    # print("stack to take from: ", stack_to_take_from)

    # print("Full stacks: ", stacks_full)

    # figure out the plate level to take (bottom = 0, top = 5)
    plate_index = 0
    for pos in state[stack_to_take_from]:
        if pos["current_plate"] == None:
            break
        plate_index += 1
    return stack_to_take_from, plate_index


def get_next_stacked_tip_rack(state: dict, stack_limit: int):
    """
    Identify the next stacked plate that can be picked up by the Hamilton.
    Arguments:
        state: dict of the current state of the machine.
        stack_limit: int maximum number of plates that can be placed on a stack.
        src_or_tgt: string either "src" or "tgt" to know which type of plate to look for in the state.
    Returns:
        Two strings that represent the position of the next plate to be taken and the stack it is in.
    """

    stacks = ["1", "2", "3", "4"]
    treated_tip_racks_count = state[f"treated_tip_racks_count"]
    # print("# treated plates: ", treated_plates_count)

    # Find which stack to take from

    stacks_fully_done = int(treated_tip_racks_count / stack_limit)
    # print("stacks_fully_done", stacks_fully_done)
    stack_to_take_from_nb = stacks[stacks_fully_done]
    stack_to_take_from = f"tip_stack_{str(stack_to_take_from_nb)}"
    # print("will start treatment of: ", treated_plates_count + 1, "th plate")
    # print("stack to take from: ", stack_to_take_from)

    # print("Full stacks: ", stacks_full)

    # figure out the plate level to take (bottom = 0, top = 3)
    plate_index = 3
    for pos in reversed(state[stack_to_take_from]):
        if pos["current"] != None:
            break
        plate_index -= 1
    # print("plate index: ", plate_index)
    return stack_to_take_from, plate_index

import os

from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType, Plate384, INITIALIZE, GRIP_GET, GRIP_PLACE)

# Current directory path
dir_path = os.path.dirname(__file__)

# Get layout file path
layout_filename     = 'move_384_plate.lay'
layfile = os.path.abspath(os.path.join(dir_path, layout_filename))

source_plate_name   = 'Gre_384_Sq_0001'
target_plate_name   = 'Gre_384_Sq_0002'

# Initialize layout manager
lmgr = LayoutManager(layfile)

# Source plate
src_plate_type = ResourceType(Plate384, source_plate_name)
source_plate = lmgr.assign_unused_resource(src_plate_type)

target_plate_type = ResourceType(Plate384, target_plate_name)
target_plate = lmgr.assign_unused_resource(target_plate_type)

if __name__ == '__main__':
    src_plate_pos = source_plate.layout_name() + ', ' + source_plate.position_id(0)
    target_plate_pos = target_plate.layout_name() + ', ' + target_plate.position_id(0)

    with HamiltonInterface(simulate=True) as hammy:
        hammy.wait_on_response(hammy.send_command(INITIALIZE))
        print('\nInitialized!')

        cmd_id = hammy.send_command(GRIP_GET, 
                                    #plateLabwarePositions=src_plate_pos 
                                    plateSequence=source_plate_name,
                                    toolSequence='COREGripTool_OnWaste_1000ul_0001',
                                    gripForce=3,
                                    gripperToolChannel=2,
                                    transportMode=0)
        print(hammy.wait_on_response(cmd_id, raise_first_exception=True))

        cmd_id = hammy.send_command(GRIP_PLACE,
                                    #plateLabwarePositions=target_plate_pos
                                    plateSequence=target_plate_name,
                                    toolSequence='COREGripTool_OnWaste_1000ul_0001',
                                    transportMode=0)
        print(hammy.wait_on_response(cmd_id, raise_first_exception=True))
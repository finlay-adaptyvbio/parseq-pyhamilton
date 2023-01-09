import os

from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType, Plate24, Plate96, Plate384, Tip96,
    INITIALIZE, PICKUP, EJECT, ASPIRATE, DISPENSE, ISWAP_GET, ISWAP_PLACE, HEPA, GRIP_GET, GRIP_MOVE, GRIP_PLACE,
    WASH96_EMPTY, PICKUP96, EJECT96, ASPIRATE96, DISPENSE96,  initialize, hepa_on, tip_pick_up, 
    tip_eject, aspirate, dispense, wash_empty_refill, tip_pick_up_96, tip_eject_96, aspirate_96, dispense_96,
    oemerr, PositionError, move_plate)

layout_filename     = 'Py_cherry_picking.lay'
source_plate_name   = 'Gre_384_Sq_0001'
target_plate_name   = 'Gre_384_Sq_0002'

layfile = os.path.abspath(os.path.join(r"C:\\Users\\Adaptyvbio\\Documents\\PyHamilton\\layouts", layout_filename))
lmgr = LayoutManager(layfile)

plate_type = ResourceType(Plate384, source_plate_name)
source_plate = lmgr.assign_unused_resource(plate_type)
source_plate_pos = (source_plate,0)

target_site_type = ResourceType(Plate384, target_plate_name)
target_site = lmgr.assign_unused_resource(target_site_type)

if __name__ == '__main__':
    plate_pos = source_plate.layout_name() + ', ' + source_plate.position_id(0)
    target_pos = target_site.layout_name() + ', ' + target_site.position_id(0)

    print(plate_pos)

    with HamiltonInterface(simulate=True) as hammy:
        hammy.wait_on_response(hammy.send_command(INITIALIZE))
        print('\nInitialized!')

        '''
        cmd_id = hammy.send_command(GRIP_MOVE, 
                                    plateLabwarePositions='Fal_96_Rd_0001;')

        '''
        cmd_id = hammy.send_command(GRIP_GET, 
                                    #plateLabwarePositions=source_plate.layout_name(),#+', A3', 
                                    plateSequence="Gre_384_Sq_0001_lid",
                                    toolSequence='COREGripTool_OnWaste_1000ul_0001',
                                    gripForce=3,
                                    gripperToolChannel=2,
                                    transportMode=1)
        print(hammy.wait_on_response(cmd_id, raise_first_exception=True))

        cmd_id = hammy.send_command(GRIP_PLACE,
                                    plateSequence="Gre_384_Sq_0002_lid",
                                    #plateLabwarePositions=target_site.layout_name(),#+', A1', 
                                    toolSequence='COREGripTool_OnWaste_1000ul_0001',
                                    transportMode=1)
        print(hammy.wait_on_response(cmd_id, raise_first_exception=True))

        """ 
        cmd_id = hammy.send_command(GRIP_MOVE, 
                                    plateLabwarePositions='Fal_96_Rd_0002, A1')
        print(hammy.wait_on_response(cmd_id, raise_first_exception=True))
        """
        '''
        for id in (hammy.send_command(ISWAP_GET, plateLabwarePositions=plate_pos):
                   hammy.send_command(ISWAP_PLACE, plateLabwarePositions=target_pos)):
            
            print(hammy.wait_on_response(id, raise_first_exception=True))
            print('ID is ',id)
        
        for id in (hammy.send_command(ISWAP_GET, plateLabwarePositions=target_pos),
                   hammy.send_command(ISWAP_PLACE, plateLabwarePositions=plate_pos)):
            print(hammy.wait_on_response(id, raise_first_exception=True))
        '''
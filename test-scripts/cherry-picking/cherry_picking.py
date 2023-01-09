#!python3

import os
import copy
from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType, Plate24, Plate96, Tip96,
    INITIALIZE, PICKUP, EJECT, ASPIRATE, DISPENSE, ISWAP_GET, ISWAP_PLACE, HEPA,
    WASH96_EMPTY, PICKUP96, EJECT96, ASPIRATE96, DISPENSE96,  initialize, hepa_on, tip_pick_up, 
    tip_eject, aspirate, dispense, wash_empty_refill, tip_pick_up_96, tip_eject_96, aspirate_96, dispense_96,
    oemerr, PositionError, move_plate)

layout_filename = 'Py_Adaptyv_v1.5.lay'
liquid_class = 'HighVolume_Water_DispenseJet_Part'

layfile = os.path.abspath(os.path.join(r"C:\\Users\\Adaptyvbio\\Documents\\PyHamilton\\layouts", layout_filename))
lmgr = LayoutManager(layfile)

""" tip_name_from_line = lambda line: LayoutManager.layline_first_field(line)
print(tip_name_from_line)
tip_name_condition = lambda line: LayoutManager.field_starts_with(tip_name_from_line(line), 'HT_L_')
print(tip_name_condition) """
tips_type = ResourceType(Tip96, "HT_L_0002")#tip_name_condition, tip_name_from_line)
tip_resource = lmgr.assign_unused_resource(tips_type)

tip_starting_pos    = 16
nr_of_trials        = 2
tip_positions = [(tip_resource, tip_starting_pos + i) for i in range(nr_of_trials)]

plate_type = ResourceType(Plate96, 'Fal_96_Rd_0001')
plate_resource = lmgr.assign_unused_resource(plate_type)

print('plate type =', plate_type)
#raise ValueError()
plate_starting_pos = 0
plate_positions = [(plate_resource, plate_starting_pos + i) for i in range(nr_of_trials)]

if __name__ == '__main__':

    '''
    tip_no = 88 # top right corner
    well_no = 7 # bottom left corner
    tip_labware_pos = tip_resource.layout_name() + ', ' + tip_resource.position_id(tip_no) + ';'
    print(tip_resource.layout_name())
    #raise ValueError('Stopped by user')
    well_labware_pos = plate.layout_name() + ', ' + plate.position_id(well_no) + ';'
    liq_class = 'HighVolumeFilter_Water_DispenseJet_Empty'
    '''

    with HamiltonInterface() as hammy:

        initialize(hammy)

        for tip_pos,plate_pos in zip(tip_positions, plate_positions):
            tip_pick_up(hammy,  [tip_pos])
            aspirate(hammy,     [plate_pos], [.001], liquidClass=liquid_class)

            eject_pos = (plate_pos[0], plate_pos[1]+1)
            dispense(hammy,     [eject_pos], [.001], liquidClass=liquid_class)
            tip_eject(hammy,    [tip_pos])

        '''
        hammy.wait_on_response(hammy.send_command(INITIALIZE))
        ids = [hammy.send_command(PICKUP, labwarePositions=tip_labware_pos),
               hammy.send_command(ASPIRATE, labwarePositions=well_labware_pos, volumes=100.0, liquidClass=liq_class),
               hammy.send_command(DISPENSE, labwarePositions=well_labware_pos, volumes=100.0, liquidClass=liq_class),
               hammy.send_command(EJECT, labwarePositions=tip_labware_pos)]
        for id in ids:
            try:
                print(hammy.wait_on_response(id, raise_first_exception=True))
                print('Step ID = ',id)
            except HamiltonError as he:
                print('Exception ID = ', id)
                print(he)

        '''
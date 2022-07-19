print("checkpoint 1")

import os, sys, logging, time, csv
from datetime import datetime

from contextlib import contextmanager
import sys 
import IPython


from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType, Plate24, Plate96, Tip96,
    INITIALIZE, PICKUP, EJECT, ASPIRATE, DISPENSE, ISWAP_GET, ISWAP_PLACE, HEPA,
    WASH96_EMPTY, PICKUP96, EJECT96, ASPIRATE96, DISPENSE96,  initialize, hepa_on, tip_pick_up, 
    tip_eject, aspirate, dispense, wash_empty_refill, tip_pick_up_96, tip_eject_96, aspirate_96, dispense_96,
    oemerr, PositionError, move_plate)



from dilution_utils import resource_list_with_prefix



log_dir = os.path.join(this_file_dir, 'log')
if not os.path.exists(log_dir):
    os.mkdir(log_dir)
    
main_logfile = os.path.join(log_dir, 'main.log')



liq_class = 'StandardVolumeFilter_Water_DispenseJet_Empty_with_transport_vol'



layfile = os.path.join('assets', 'template_deck.lay')
lmgr = LayoutManager(layfile)


dw_plates_list = resource_list_with_prefix(lmgr, 'dw_plate_', Plate96, 5)

reader_plates_list = resource_list_with_prefix(lmgr, 'reader_plate_', Plate96, 5)

std_vol_tips_list=resource_list_with_prefix(lmgr, 'std_volume_tips_', Tip96, 4)
high_volume_tips = lmgr.assign_unused_resource(ResourceType(Tip96, "high_volume_tips"))



def enter_pyhamilton_repl():
    IPython.embed()
    
if __name__ == '__main__': 
    with HamiltonInterface(simulate=True) as ham_int:
        
        initialize(ham_int)
        
        tips_pos = [(std_vol_tips_list[0], x) for x in range(8)]
        tip_pick_up(ham_int, tips_pos)
        
        asp_poss_list = [[(dw_plates_list[0], x+16*i) for x in range(8)] for i in range(6)]
        disp_poss_list = [[(dw_plates_list[0], x+16*i+8) for x in range(8)] for i in range(6)]
        vols_list = [25]*8
        
        for column in range(6):
            aspirate(ham_int, asp_poss_list[column], vols_list, liquidClass = liq_class)
        for column in range(6):
            dispense(ham_int, disp_poss_list[column], vols_list, liquidClass = liq_class)
            
        tip_eject(ham_int, tips_pos)
        
        if 'repl' in sys.argv:
            enter_pyhamilton_repl()

        
        
        
        
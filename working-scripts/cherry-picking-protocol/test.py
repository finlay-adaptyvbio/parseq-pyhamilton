from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType,ASPIRATE384,DISPENSE384, Plate384, Tip96, PICKUP384,EJECT384, INITIALIZE, PICKUP, GRIP_GET, GRIP_PLACE, GRIP_MOVE, tip_pick_up, tip_eject, aspirate, dispense)
import os

# LAYOUT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cherry_picking_protocol_stacked_tips.lay")
LAYOUT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "384test.lay")

lmgr = LayoutManager(LAYOUT_FILE_PATH)

# tips_type = ResourceType(Tip96, state["tips"]["seq"])
"""
with HamiltonInterface(simulate=True) as hammy:
    print("Initializing...")
    hammy.wait_on_response(hammy.send_command(INITIALIZE))
    
    print('Done Initializing.')
    cmd_id = hammy.send_command(GRIP_GET, 
                            plateSequence      = "TIP_50ul_L_NE_stack_0002",
                            # lidSequence      = lidSequence,
                            toolSequence       = 'COREGripTool_OnWaste_1000ul_0001',
                            gripForce          = 9,
                            gripperToolChannel = 2,
                            gripHeight         = 26.5,
                            #gripWidth          = 68,
                            transportMode      = 0 )
    print(hammy.wait_on_response(cmd_id, raise_first_exception=True))
    cmd_id = hammy.send_command(GRIP_PLACE,
                                plateSequence       =  "TIP_50ul_L_NE_stack_0008",
                                # lidSequence       = lidSequence,
                                toolSequence        = 'COREGripTool_OnWaste_1000ul_0001',
                                transportMode       = 0,
                                ejectToolWhenFinish = 1)
    print(hammy.wait_on_response(cmd_id, raise_first_exception=True)) 
"""
"""
tips_type = ResourceType(Tip96, "TIP_50ul_L_NE_stack_0002")
# print("tip seq        :", state["tips"]["seq"])
tip_resource = lmgr.assign_unused_resource(tips_type)
tip_pos = (tip_resource, 0)
src_plate_type = ResourceType(Plate384,  "Gre_384_Sq_0005_0001")
plate_resource = lmgr.assign_unused_resource(src_plate_type)
well_pos_in_plate = (plate_resource, 0)


with HamiltonInterface(simulate=True) as hammy:
    print("Initializing...")
    hammy.wait_on_response(hammy.send_command(INITIALIZE))
    # Aspirate from well of interest
    tip_pick_up(hammy, [tip_pos])
    aspirate(hammy, [well_pos_in_plate], [10], liquidClass = "Tip_50ul_96COREHead1000ul_Water_DispenseJet_PartEmpty")
    # cmd_id = hammy.send_command(PICKUP, 
    #                        tipSequence       = "TIP_50ul_L_NE_stack_0002",
    #                        channelVariable   = "10")
    #print(hammy.wait_on_response(cmd_id, raise_first_exception=True))
    # Dispense into target well
    dispense(hammy, [well_pos_in_plate], [10], liquidClass = "Tip_50ul_96COREHead1000ul_Water_DispenseJet_PartEmpty")
    tip_eject(hammy, [tip_pos])
"""
with HamiltonInterface(simulate=True) as hammy:
    print("Initializing...")
    hammy.wait_on_response(hammy.send_command(INITIALIZE))
    # Aspirate from well of interest
    hammy.wait_on_response(hammy.send_command(
        PICKUP384, 
        tipSequence = "NTR_384_Primer"
    ))

    hammy.wait_on_response(hammy.send_command(
        ASPIRATE384,
        liquidClass = "Adaptyv_primer_dispensejet_empty",
        aspirateVolume = 30,
        aspirateSequence = "cp_src_lid_holder_plate"
    ))

    hammy.wait_on_response(hammy.send_command(
        DISPENSE384, 
        liquidClass = "Adaptyv_primer_dispensejet_empty",
        dispenseVolume = 30,
        dispenseSequence = "cp_src_lid_holder_plate"
    ))

    hammy.wait_on_response(hammy.send_command(
        EJECT384, 
        tipEjectToKnownPosition = 1,
    ))

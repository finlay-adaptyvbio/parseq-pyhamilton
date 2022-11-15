from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType, Plate384, Tip96, INITIALIZE, GRIP_GET, GRIP_PLACE, GRIP_MOVE, tip_pick_up, tip_eject, aspirate, dispense)

DEFAULT_GRIP_TOOL_SEQUENCE = 'COREGripTool_OnWaste_1000ul_0001'


def grip_get_plate_with_lid(
        hamilton_interface:HamiltonInterface, 
        plateSequence:str, 
        lidSequence:str, 
        toolSequence:str = DEFAULT_GRIP_TOOL_SEQUENCE,
        gripForce:float = 3,
        transportMode:int = 2,
        gripperToolChannel:int = 2,
        gripHeight:float = 10.0
    ):
    cmd_id = hamilton_interface.send_command(GRIP_GET, 
                                plateSequence      = plateSequence,
                                lidSequence        = lidSequence,
                                toolSequence       = toolSequence,
                                gripForce          = gripForce,
                                gripperToolChannel = gripperToolChannel,
                                gripHeight         = gripHeight,
                                transportMode      = transportMode )
    hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True)

def grip_place_plate_with_lid(
        hamilton_interface:HamiltonInterface,
        plateSequence:str, 
        lidSequence:str, 
        toolSequence:str = DEFAULT_GRIP_TOOL_SEQUENCE,
        transportMode:int = 2,
        ejectToolWhenFinish:int = 1,
    ):
    cmd_id = hamilton_interface.send_command(GRIP_PLACE,
                                plateSequence       = plateSequence,
                                lidSequence         = lidSequence,
                                toolSequence        = toolSequence,
                                transportMode       = transportMode,
                                ejectToolWhenFinish = ejectToolWhenFinish)
    hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True)


def grip_get_lid(
        hamilton_interface:HamiltonInterface, 
        plateSequence:str, 
        lidSequence:str, 
        toolSequence:str = DEFAULT_GRIP_TOOL_SEQUENCE,
        gripForce:float = 3,
        transportMode:int = 1,
        gripperToolChannel:int = 2,
        gripHeight:float = 3.0,
    ):
    cmd_id = hamilton_interface.send_command(GRIP_GET, 
                                #plateSequence      = plateSequence,
                                lidSequence        = lidSequence,
                                toolSequence       = toolSequence,
                                gripForce          = gripForce,
                                gripperToolChannel = gripperToolChannel,
                                gripHeight         = gripHeight,
                                transportMode      = transportMode )
    hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True)

def grip_place_lid(
        hamilton_interface:HamiltonInterface,
        plateSequence:str,
        lidSequence:str,
        toolSequence:str = DEFAULT_GRIP_TOOL_SEQUENCE,
        transportMode:int = 1,
        ejectToolWhenFinish:int = 1,
    ):
    grip_place_plate_with_lid(hamilton_interface,plateSequence,lidSequence,toolSequence, transportMode=transportMode,ejectToolWhenFinish=ejectToolWhenFinish)

def grip_get_96_tip_rack ( # With these settings can pickup from the side and from the middle
        hamilton_interface:HamiltonInterface, 
        plateSequence:str, 
        toolSequence:str = DEFAULT_GRIP_TOOL_SEQUENCE,
    ):
    cmd_id = hamilton_interface.send_command(GRIP_GET, 
                                plateSequence      = plateSequence,
                                toolSequence       = toolSequence,
                                gripForce          = 9,
                                gripperToolChannel = 2,
                                gripHeight         = 26.5,
                                transportMode      = 0 )
    hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True)

def grip_place_96_tip_rack (
        hamilton_interface:HamiltonInterface, 
        plateSequence:str, 
        toolSequence:str = DEFAULT_GRIP_TOOL_SEQUENCE,
        ejectToolWhenFinish:int = 1,
    ):
    cmd_id = hamilton_interface.send_command(GRIP_PLACE, 
                                plateSequence      = plateSequence,
                                toolSequence       = toolSequence,
                                transportMode      = 0,
                                ejectToolWhenFinish = ejectToolWhenFinish)
    hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True)
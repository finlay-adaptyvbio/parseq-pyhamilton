from pyhamilton import (
    HamiltonInterface,
    LayoutManager,
    ResourceType,
    Plate384,
    Plate96,
    Tip96,
    Tip384,
    Lid,
    INITIALIZE,
    GRIP_GET,
    GRIP_PLACE,
    GRIP_MOVE,
)

from pyhamilton.oemerr import PositionError

import logging

DEFAULT_GRIP_TOOL_SEQUENCE = "CORE_Grip"


def labware_pos_str(labware, idx):
    return labware.layout_name() + ", " + labware.position_id(idx)


def move_plate(ham, source_plate, target_plate, gripHeight=8.0):

    if isinstance(source_plate, (Plate384, Plate96)) and isinstance(
        target_plate, (Plate384, Plate96)
    ):

        logging.info(
            f"move_plate: Moving plate {source_plate.layout_name()} to {target_plate.layout_name()}."
        )

        src_plate_pos = labware_pos_str(source_plate, 0)
        trgt_plate_pos = labware_pos_str(target_plate, 0)

        cid = ham.send_command(
            GRIP_GET,
            plateLabwarePositions=src_plate_pos,
            gripHeight=gripHeight,
            transportMode=0,
        )

        try:
            ham.wait_on_response(cid, raise_first_exception=True, timeout=120)
        except PositionError:
            raise IOError

        cid = ham.send_command(
            GRIP_PLACE,
            plateLabwarePositions=trgt_plate_pos,
            transportMode=0,
        )
        try:
            ham.wait_on_response(cid, raise_first_exception=True, timeout=120)
        except PositionError:
            raise IOError


def move_lid(ham, source_lid, target_lid, gripHeight=5.0):

    if isinstance(source_lid, Lid) and isinstance(target_lid, Lid):

        logging.info(
            f"move_plate: Moving plate {source_lid.layout_name()} to {target_lid.layout_name()}."
        )

        src_lid_pos = labware_pos_str(source_lid, 0)
        trgt_lid_pos = labware_pos_str(target_lid, 0)

        cid = ham.send_command(
            GRIP_GET,
            lidLabwarePositions=src_lid_pos,
            gripHeight=gripHeight,
            transportMode=1,
        )

        try:
            ham.wait_on_response(cid, raise_first_exception=True, timeout=120)
        except PositionError:
            raise IOError

        cid = ham.send_command(
            GRIP_PLACE,
            lidLabwarePositions=trgt_lid_pos,
            transportMode=1,
        )

        try:
            ham.wait_on_response(cid, raise_first_exception=True, timeout=120)
        except PositionError:
            raise IOError


def grip_get_plate_with_lid(
    hamilton_interface: HamiltonInterface,
    plateSequence: str,
    lidSequence: str,
    toolSequence: str = DEFAULT_GRIP_TOOL_SEQUENCE,
    gripForce: float = 3,
    transportMode: int = 2,
    gripperToolChannel: int = 2,
    gripHeight: float = 10.0,
):
    cmd_id = hamilton_interface.send_command(
        GRIP_GET,
        plateSequence=plateSequence,
        lidSequence=lidSequence,
        toolSequence=toolSequence,
        gripForce=gripForce,
        gripperToolChannel=gripperToolChannel,
        gripHeight=gripHeight,
        transportMode=transportMode,
    )
    hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True)


def grip_place_plate_with_lid(
    hamilton_interface: HamiltonInterface,
    plateSequence: str,
    lidSequence: str,
    toolSequence: str = DEFAULT_GRIP_TOOL_SEQUENCE,
    transportMode: int = 2,
    ejectToolWhenFinish: int = 1,
):
    cmd_id = hamilton_interface.send_command(
        GRIP_PLACE,
        plateSequence=plateSequence,
        lidSequence=lidSequence,
        toolSequence=toolSequence,
        transportMode=transportMode,
        ejectToolWhenFinish=ejectToolWhenFinish,
    )
    hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True)


def grip_get_lid(
    hamilton_interface: HamiltonInterface,
    plateSequence: str,
    lidSequence: str,
    toolSequence: str = DEFAULT_GRIP_TOOL_SEQUENCE,
    gripForce: float = 3,
    transportMode: int = 1,
    gripperToolChannel: int = 2,
    gripHeight: float = 3.0,
):
    cmd_id = hamilton_interface.send_command(
        GRIP_GET,
        # plateSequence      = plateSequence,
        lidSequence=lidSequence,
        toolSequence=toolSequence,
        gripForce=gripForce,
        gripperToolChannel=gripperToolChannel,
        gripHeight=gripHeight,
        transportMode=transportMode,
    )
    hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True)


def grip_place_lid(
    hamilton_interface: HamiltonInterface,
    plateSequence: str,
    lidSequence: str,
    toolSequence: str = DEFAULT_GRIP_TOOL_SEQUENCE,
    transportMode: int = 1,
    ejectToolWhenFinish: int = 1,
):
    grip_place_plate_with_lid(
        hamilton_interface,
        plateSequence,
        lidSequence,
        toolSequence,
        transportMode=transportMode,
        ejectToolWhenFinish=ejectToolWhenFinish,
    )


def grip_get_96_tip_rack(  # With these settings can pickup from the side and from the middle
    hamilton_interface: HamiltonInterface,
    plateSequence: str,
    toolSequence: str = DEFAULT_GRIP_TOOL_SEQUENCE,
):
    cmd_id = hamilton_interface.send_command(
        GRIP_GET,
        plateSequence=plateSequence,
        toolSequence=toolSequence,
        gripForce=9,
        gripperToolChannel=2,
        gripHeight=26.5,
        transportMode=0,
    )
    hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True)


def grip_place_96_tip_rack(
    hamilton_interface: HamiltonInterface,
    plateSequence: str,
    toolSequence: str = DEFAULT_GRIP_TOOL_SEQUENCE,
    ejectToolWhenFinish: int = 1,
):
    cmd_id = hamilton_interface.send_command(
        GRIP_PLACE,
        plateSequence=plateSequence,
        toolSequence=toolSequence,
        transportMode=0,
        ejectToolWhenFinish=ejectToolWhenFinish,
    )
    hamilton_interface.wait_on_response(cmd_id, raise_first_exception=True)

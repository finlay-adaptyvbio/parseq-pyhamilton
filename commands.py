from pyhamilton import (
    HamiltonInterface,
    Lid,  # type: ignore
    Plate96,
    Plate384,
    Tip96,
    Tip384,  # type: ignore
    Reservoir300,  # type: ignore
    EppiCarrier24,  # type: ignore
    INITIALIZE,  # type: ignore
    GRIP_GET,  # type: ignore
    GRIP_PLACE,  # type: ignore
    PICKUP,  # type: ignore
    EJECT,  # type: ignore
    DISPENSE,  # type: ignore
    ASPIRATE,  # type: ignore
    ASPIRATE384,  # type: ignore
    DISPENSE384,  # type: ignore
    PICKUP384,  # type: ignore
    EJECT384,  # type: ignore
)

import deck as dk

from pyhamilton.oemerr import PositionError
from typing import Union

# Defaults

DEFAULT_GRIP_TOOL_SEQUENCE = "CORE_Grip"
DEFAULT_LIQUID_CLASS_2CH = "StandardVolume_Water_DispenseJet_Empty"
DEFAULT_LIQUID_CLASS_384MPH = "50ulTip_conductive_384COREHead_Water_DispenseJet_Empty"

# Formatting constants

STR1 = 20
STR2 = 20
STR3 = 20
STR4 = 20

# TODO: Add docstrings


def initialize(ham: HamiltonInterface):
    print(f"Command: {'initialize':<STR1}")

    cid = ham.send_command(INITIALIZE)

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except:
        raise IOError


def labware_pos_str(labware, idx):
    return labware.layout_name() + ", " + labware.position_id(idx)


def compound_pos_str(pos_tuples):
    present_pos_tups = [pt for pt in pos_tuples if pt is not None]
    return ";".join(
        (labware_pos_str(labware, idx) for labware, idx in present_pos_tups)
    )


def grip_get(
    ham: HamiltonInterface,
    labware: Union[Plate96, Plate384, Lid],
    mode: int,
    **kw_args,
):
    print(
        f"Command: {'grip_get':<STR1} | Labware: {labware.layout_name():<STR2} |"
        f" Mode: {mode:<STR3}"
    )

    labwarePositions = labware_pos_str(labware, 0)
    transportMode = mode

    if mode == 0:
        cid = ham.send_command(
            GRIP_GET,
            plateLabwarePositions=labwarePositions,
            transportMode=transportMode,
            **kw_args,
        )

    elif mode == 1:
        cid = ham.send_command(
            GRIP_GET,
            lidLabwarePositions=labwarePositions,
            transportMode=transportMode,
            **kw_args,
        )

    else:
        raise ValueError

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def grip_place(
    ham: HamiltonInterface,
    labware: Union[Plate96, Plate384, Lid],
    mode: int,
    eject: bool = False,
    **kw_args,
):
    print(
        f"Command: {'grip_place':<STR1} | Labware: {labware.layout_name():<STR2} |"
        f" Mode: {mode:<STR3} | Eject: {eject:<STR4}"
    )

    labwarePositions = labware_pos_str(labware, 0)
    transportMode = mode
    ejectToolWhenFinish = eject

    if mode == 0:
        cid = ham.send_command(
            GRIP_PLACE,
            plateLabwarePositions=labwarePositions,
            transportMode=transportMode,
            ejectToolWhenFinish=ejectToolWhenFinish,
            **kw_args,
        )

    elif mode == 1:
        cid = ham.send_command(
            GRIP_PLACE,
            lidLabwarePositions=labwarePositions,
            transportMode=transportMode,
            ejectToolWhenFinish=ejectToolWhenFinish,
            **kw_args,
        )

    else:
        raise ValueError

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def tip_pick_up(
    ham: HamiltonInterface,
    positions: list[tuple[Tip96, int]],
    **kw_args,
):
    print(
        f"Command: {'tip_pick_up':<STR1} | Labware:"
        f" {positions[0][0].layout_name():<STR2} | Positions:"
        f" {[p[0].position_id(p[1]) for p in positions]:<STR3}"
    )

    labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        PICKUP,
        labwarePositions=labwarePositions,
        **kw_args,
    )

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def tip_eject(
    ham: HamiltonInterface,
    positions: list[tuple[Tip96, int]],
    waste: bool = False,
    **kw_args,
):
    print(
        f"Command: {'tip_eject':<STR1} | Labware:"
        f" {positions[0][0].layout_name():<STR2} | Positions:"
        f" {[p[0].position_id(p[1]) for p in positions]:<STR3} | Waste:"
        f" {waste:<STR4}"
    )

    if waste:
        useDefaultWaste = int(waste)
        labwarePositions = ""

    else:
        useDefaultWaste = int(waste)
        labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        EJECT,
        labwarePositions=labwarePositions,
        useDefaultWaste=useDefaultWaste,
        **kw_args,
    )

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def aspirate(
    ham: HamiltonInterface,
    positions: list[tuple[Union[Plate96, Plate384, Reservoir300, EppiCarrier24], int]],
    volumes: list[float],
    **kw_args,
):
    print(
        f"Command: {'aspirate':<STR1} | Labware:"
        f" {positions[0][0].layout_name():<STR2} | Positions:"
        f" {[p[0].position_id(p[1]) for p in positions]:<STR3} | Volumes:"
        f" {volumes:<STR4}"
    )

    if len(volumes) < len(positions):
        volumes.extend([volumes[0] for _ in range(len(volumes), len(positions))])
    elif len(volumes) > len(positions):
        raise ValueError

    if "liquidClass" not in kw_args:
        kw_args.update({"liquidClass": DEFAULT_LIQUID_CLASS_2CH})

    labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        ASPIRATE,
        labwarePositions=labwarePositions,
        volumes=volumes,
        **kw_args,
    )

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def dispense(
    ham: HamiltonInterface,
    positions: list[tuple[Union[Plate96, Plate384, Reservoir300, EppiCarrier24], int]],
    volumes: list[float],
    **kw_args,
):
    print(
        f"Command: {'dispense':<STR1} | Labware:"
        f" {positions[0][0].layout_name():<STR2} | Positions:"
        f" {[p[0].position_id(p[1]) for p in positions]:<STR3} | Volumes:"
        f" {volumes:<STR4}"
    )

    if len(volumes) < len(positions):
        volumes.extend([volumes[0] for _ in range(len(volumes), len(positions))])
    elif len(volumes) > len(positions):
        raise ValueError

    if "liquidClass" not in kw_args:
        kw_args.update({"liquidClass": DEFAULT_LIQUID_CLASS_2CH})

    labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        DISPENSE,
        labwarePositions=labwarePositions,
        volumes=volumes,
        **kw_args,
    )

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def tip_pick_up_384(
    ham: HamiltonInterface,
    positions: list[tuple[Tip384, int]],
    **kw_args,
):
    print(
        f"Command: {'tip_pick_up_384':<STR1} | Labware:"
        f" {positions[0][0].layout_name():<STR2} | Positions: {len(positions):<STR3}"
    )

    labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        PICKUP384,
        labwarePositions=labwarePositions,
        **kw_args,
    )

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def tip_eject_384(
    ham: HamiltonInterface,
    positions: list[tuple[Tip384, int]],
    mode: int = 0,
    **kw_args,
):
    print(
        f"Command: {'tip_eject_384':<STR1} | Labware:"
        f" {positions[0][0].layout_name():<STR2} | Positions: {len(positions):<STR3} |"
        f" Mode: {mode:<STR4}"
    )

    tipEjectToKnownPosition = int(mode)

    if mode == 0:
        labwarePositions = compound_pos_str(positions)
    elif mode == 1:
        labwarePositions = ""
    elif mode == 2:
        labwarePositions = ""
    else:
        raise ValueError

    cid = ham.send_command(
        EJECT384,
        labwarePositions=labwarePositions,
        tipEjectToKnownPosition=tipEjectToKnownPosition,
        **kw_args,
    )

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def aspirate_384(
    ham: HamiltonInterface,
    positions: list[tuple[Union[Plate96, Plate384, Reservoir300], int]],
    volume: float,
    **kw_args,
):
    print(
        f"Command: {'aspirate_384':<STR1} | Labware:"
        f" {positions[0][0].layout_name():<STR2} | Positions: {len(positions):<STR3} |"
        f" Volume: {volume:<STR4}"
    )

    if "liquidClass" not in kw_args:
        kw_args.update({"liquidClass": DEFAULT_LIQUID_CLASS_384MPH})

    labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        ASPIRATE384,
        labwarePositions=labwarePositions,
        aspirateVolume=volume,
        **kw_args,
    )

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def dispense_384(
    ham: HamiltonInterface,
    positions: list[tuple[Union[Plate96, Plate384, Reservoir300], int]],
    volume: float,
    **kw_args,
):
    print(
        f"Command: {'dispense_384':<STR1} | Labware:"
        f" {positions[0][0].layout_name():<STR2} | Positions: {len(positions):<STR3} |"
        f" Volume: {volume:<STR4}"
    )

    if "liquidClass" not in kw_args:
        kw_args.update({"liquidClass": DEFAULT_LIQUID_CLASS_384MPH})

    labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        DISPENSE384,
        labwarePositions=labwarePositions,
        dispenseVolume=volume,
        **kw_args,
    )

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def grip_get_tip_rack(
    ham: HamiltonInterface,
    labware: Union[Tip96, Tip384],
    **kw_args,
):
    print(
        f"Command: {'grip_get_tip_rack':<STR1} | Labware: {labware.layout_name():<STR2}"
    )

    labwarePositions = labware_pos_str(labware, 0)

    if isinstance(labware, Tip96):
        gripHeight = 26.5
        gripWidth = 77.0
    elif isinstance(labware, Tip384):
        gripHeight = 26.5
        gripWidth = 77.0
    else:
        raise TypeError

    cid = ham.send_command(
        GRIP_GET,
        plateLabwarePositions=labwarePositions,
        gripForce=9,
        gripHeight=gripHeight,
        gripWidth=gripWidth,
        **kw_args,
    )

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError


def grip_place_tip_rack(
    ham: HamiltonInterface,
    labware: Union[Tip96, Tip384],
    waste: bool = False,
    eject: bool = False,
    **kw_args,
):
    print(
        f"Command: {'grip_get_tip_rack':<STR1} | Labware:"
        f" {labware.layout_name():<STR2} | Waste: {waste:<STR3} | Eject: {eject:<STR4}"
    )

    ejectToolWhenFinish = eject

    if isinstance(labware, Tip96):
        rack_type = "_tip96"
    elif isinstance(labware, Tip384):
        rack_type = "_tip384"
    else:
        raise TypeError

    if waste:
        plateSequence = "Waste" + rack_type
        labwarePositions = ""

    else:
        plateSequence = ""
        labwarePositions = labware_pos_str(labware, 0)

    cid = ham.send_command(
        GRIP_PLACE,
        plateSequence=plateSequence,
        plateLabwarePositions=labwarePositions,
        ejectToolWhenFinish=ejectToolWhenFinish,
        **kw_args,
    )

    try:
        ham.wait_on_response(cid, raise_first_exception=True)
    except PositionError:
        raise IOError

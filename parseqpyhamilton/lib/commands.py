"""
This module contains functions that define common actions for the Hamilton robot.
Default command templates are defined as dict entries to easily modify common parameters.
"""

# Imports
import logging
from typing import Optional

# Classes
from pyhamilton import HamiltonInterface, HamiltonCmdTemplate, Plate96, Plate384, Tip96
from .labware import Tip384, Reservoir300, Lid, EppiCarrier24

# Logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Default VENUS parameters
DEFAULT_GRIP_TOOL_SEQUENCE = "CORE_Grip"
DEFAULT_LIQUID_CLASS_2CH = "StandardVolume_Water_DispenseJet_Empty"
DEFAULT_LIQUID_CLASS_384MPH = "50ulTip_conductive_384COREHead_Water_DispenseJet_Empty"
HEAD_PATTERN = "1" + "0" * (95)


# Position formatting functions
def labware_pos_str(labware, idx) -> str:
    """
    Returns a string representation of the layout name and position ID of a labware at a given index.
    Necessary to communicate with PyHamilton.

    Args:
    - labware: the labware object
    - idx: the index of the labware

    Returns:
    - a string representation of the layout name and position ID of the labware

    """
    return labware.layout_name() + ", " + labware.position_id(idx)


def compound_pos_str(pos_tuples: list) -> str:
    """
    Returns a string representation of the layout name and position ID of a list of labware at given indices.
    Necessary to communicate with PyHamilton.

    Args:
    - pos_tuples: list of tuples of labware and indices

    Returns:
    - a string representation of the layout name and position ID of the labware
    """

    present_pos_tups = [pt for pt in pos_tuples if pt is not None]
    return ";".join(
        (labware_pos_str(labware, idx) for labware, idx in present_pos_tups)
    )


# Commands
def initialize(ham: HamiltonInterface) -> None:
    """
    Initializes the HamiltonInterface object by sending the 'INITIALIZE' command and waiting for a response.

    Args:
    - ham (HamiltonInterface): The HamiltonInterface object to be initialized.

    Returns:
    - None
    """

    logger.debug("Command: %s", "initialize")

    cid = ham.send_command(commands["INITIALIZE"])

    ham.wait_on_response(cid, raise_first_exception=True)


def grip_get(
    ham: HamiltonInterface,
    labware: Plate96 | Plate384 | Lid,
    mode: int = 0,
    **kw_args,
) -> None:
    """
    Pick up a plate or lid with the gripper.

    Args:
    - ham: Robot interface.
    - labware: Labware object to pick up.
    - mode: 0 for plate, 1 for lid and 2 for plate with lid. Defaults to 0.

    Keyword Args:
    - gripForce (integer): 0-9, from lowest to highest force. Defaults to 7.
    - gripWidth (float): Grip width in mm. Defaults to 82.0.
    - gripHeight (float): Height from labware base in mm. Defaults to 9.0.
    - widthBefore (float): Width before gripping in mm. Defaults to 88.0.
    - gripSpeed (float): Speed used by grippers when approaching labware in mm/s. Defaults to 275.0.
    - zSpeed (float): Speed used by grippers for vertical movements in mm/s. Defaults to 125.0.
    - checkPlate (integer): 0 or 1, whether to check for plate presence. Defaults to 0.

    Returns:
    - None
    """

    logger.debug(
        "Command: %s | Labware: %s | Mode: %s", "grip_get", labware.layout_name(), mode
    )

    labwarePositions = labware_pos_str(labware, 0)
    transportMode = mode

    if mode == 0:
        cid = ham.send_command(
            commands["GRIP_GET"],
            plateLabwarePositions=labwarePositions,
            transportMode=transportMode,
            **kw_args,
        )
    elif mode == 1:
        cid = ham.send_command(
            commands["GRIP_GET"],
            lidLabwarePositions=labwarePositions,
            transportMode=transportMode,
            **kw_args,
        )
    else:
        raise ValueError

    ham.wait_on_response(cid, raise_first_exception=True)


def grip_place(
    ham: HamiltonInterface,
    labware: Plate96 | Plate384 | Lid,
    mode: int = 0,
    eject: bool = False,
    **kw_args,
) -> None:
    """
    Place a plate or lid with the gripper.

    Args:
        - ham: Robot interface.
        - labware: Labware object to place.
        - mode: 0 for plate, 1 for lid. Defaults to 0.
        - eject: Whether to eject the gripper tool after placing. Defaults to False.

    Keyword Args:
        - movementType (integer): 0=To carrier, 1=Complex movement. Defaults to 0.
        - zSpeed (float): Speed used by grippers for vertical movements in mm/s. Defaults to 125.0.
        - platePressOnDistance (float): Lift-up distance in mm. Defaults to 0.0. Requires movementType=1.
        - xAcceleration (integer): 1-5 from slowest to fastest. Defaults to 4.
    """
    logger.debug(
        "Command: %s | Labware: %s | Mode: %s | Eject: %s",
        "grip_place",
        labware.layout_name(),
        mode,
        eject,
    )

    labwarePositions = labware_pos_str(labware, 0)
    transportMode = mode
    ejectToolWhenFinish = eject

    if mode == 0:
        cid = ham.send_command(
            commands["GRIP_PLACE"],
            plateLabwarePositions=labwarePositions,
            transportMode=transportMode,
            ejectToolWhenFinish=ejectToolWhenFinish,
            **kw_args,
        )
    elif mode == 1:
        cid = ham.send_command(
            commands["GRIP_PLACE"],
            lidLabwarePositions=labwarePositions,
            transportMode=transportMode,
            ejectToolWhenFinish=ejectToolWhenFinish,
            **kw_args,
        )
    else:
        raise ValueError

    ham.wait_on_response(cid, raise_first_exception=True)


def tip_pick_up(
    ham: HamiltonInterface,
    positions: list[tuple[Tip96, int]],
    **kw_args,
) -> None:
    """
    Pick up tips (300 or 50 uL) using single channels.

    Args:
        - ham: Robot interface.
        - positions: List of tips to pick up.
    """
    logger.debug(
        "Command: %s | Labware: %s | Positions: %s",
        "tip_pick_up",
        positions[0][0].layout_name(),
        [p[0].position_id(p[1]) for p in positions],
    )

    labwarePositions = compound_pos_str(positions)

    if len(positions) == 1:
        channelVariable = "10"
    else:
        channelVariable = "11"

    cid = ham.send_command(
        commands["PICKUP"],
        labwarePositions=labwarePositions,
        channelVariable=channelVariable,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def tip_eject(
    ham: HamiltonInterface,
    positions: Optional[list[tuple[Tip96, int]]] = None,
    waste: bool = False,
    **kw_args,
) -> None:
    """
    Eject tips (300 or 50 uL) using single channels.

    Args:
        - ham: Robot interface.
        - positions: List of tips to eject. Defaults to [].
        - waste: Whether to eject the tips to default waste. Defaults to False.
    """
    if positions is None:
        positions = []

    if positions:
        labware = positions[0][0].layout_name()
    else:
        labware = "None"

    logger.debug(
        "Command: %s | Labware: %s | Positions: %s | Waste: %s",
        "tip_eject",
        labware,
        [p[0].position_id(p[1]) for p in positions],
        waste,
    )

    if waste:
        useDefaultWaste = int(waste)
        labwarePositions = ""

    else:
        useDefaultWaste = int(waste)
        labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        commands["EJECT"],
        labwarePositions=labwarePositions,
        useDefaultWaste=useDefaultWaste,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def grip_eject(
    ham: HamiltonInterface,
    **kw_args,
) -> None:
    """
    Eject the gripper tool.

    Args:
        - ham: Robot interface.
    """
    logger.debug("Command: %s", "grip_eject")

    cid = ham.send_command(
        commands["EJECT"],
        wasteSequence=DEFAULT_GRIP_TOOL_SEQUENCE,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def aspirate(
    ham: HamiltonInterface,
    positions: list[tuple[Plate96, int]]
    | list[tuple[Plate384, int]]
    | list[tuple[EppiCarrier24, int]]
    | list[tuple[Reservoir300, int]],
    volumes: list[float],
    **kw_args,
) -> None:
    """
    Aspirate from a plate, carrier or reservoir using single channels.

    Args:
        - ham: Robot interface.
        - positions where int is the well index and Labware the plate, carrier or reservoir to aspirate from.
        - volumes: List of volumes to aspirate.

    Keyword Args:
        - liquidClass (string): Liquid class to use. Defaults to DEFAULT_LIQUID_CLASS_2CH (300 uL tips with water).
        - aspirateMode (integer): 0=Normal, 1=No air gap, 2=Aspirate all volume. Defaults to 0.
        - capacitiveLLD (integer): 0=Off, 1=Max, 2=High, 3=Mid, 4=Low, 5=From labware definition. Defaults to 0.
        - pressureLLD (integer): 0=Off, 1=Max, 2=High, 3=Mid, 4=Low, 5=From liquid class definition. Defaults to 0.
        - liquidFollowing (integer): 0=Off , 1=On. Defaults to 0.
        - submergeDepth (float): mm of immersion below liquid's surface to start aspiration when using LLD. Defaults to 2.0.
        - liquidHeight (float): mm above container's base to start aspiration when not using LLD. Defaults to 1.0.
        - maxLLdDifference (float): max mm height difference between cLLD and pLLD detected liquid levels. Defaults to 0.0.
        - mixCycles (integer): number of mixing cycles (1 cycle = 1 aspiration + 1 dispensing). Defaults to 0.
        - mixPosition (float): additional immersion mm below aspiration position to start mixing. Defaults to 0.0.
        - mixVolume (float): mix volume in uL. Defaults to 0.0.
        - xDisplacement (float): x displacement in mm. Defaults to 0.0.
        - yDisplacement (float): y displacement in mm. Defaults to 0.0.
        - zDisplacement (float): z displacement in mm. Defaults to 0.0.
        - airTransportRetractDist (float): mm to move up in Z after finishing the aspiration at a fixed height before aspirating 'transport air'. Defaults to 5.0.
        - touchOff (integer): 0=Off , 1=On. Defaults to 0.
        - aspPosAboveTouch (float): mm to move up in Z after touch off detects the bottom before aspirating liquid. Defaults to 0.0.
    """
    logger.debug(
        "Command: %s | Labware: %s | Positions: %s | Volumes: %s",
        "aspirate",
        positions[0][0].layout_name(),
        [p[0].position_id(p[1]) for p in positions],
        volumes,
    )

    if len(volumes) < len(positions):
        volumes.extend([volumes[0] for _ in range(len(volumes), len(positions))])
    elif len(volumes) > len(positions):
        raise ValueError

    if "liquidClass" not in kw_args:
        kw_args.update({"liquidClass": DEFAULT_LIQUID_CLASS_2CH})

    if len(positions) == 1:
        channelVariable = "10"
    else:
        channelVariable = "11"

    labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        commands["ASPIRATE"],
        labwarePositions=labwarePositions,
        channelVariable=channelVariable,
        volumes=volumes,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def dispense(
    ham: HamiltonInterface,
    positions: list[tuple[Plate96, int]]
    | list[tuple[Plate384, int]]
    | list[tuple[EppiCarrier24, int]]
    | list[tuple[Reservoir300, int]],
    volumes: list[float],
    **kw_args,
) -> None:
    """
    Dispense to a plate, carrier or reservoir using single channels.

    Args:
        - ham: Robot interface.
        - positions where int is the well index and Labware the plate, carrier or reservoir to dispense to.
        - volumes: List of volumes to dispense.

    Keyword Args:
        - liquidClass (string): Liquid class to use. Defaults to DEFAULT_LIQUID_CLASS_2CH (300 uL tips with water).
        - dispenseMode (integer): 0=Jet Part, 1=Jet Empty, 2=Surface Part, 3=Surface Empty, 4=Jet Drain tip, 8=From liquid class, 9=Blowout tip. Defaults to 8.
        - capacitiveLLD (integer): 0=Off, 1=Max, 2=High, 3=Mid, 4=Low, 5=From labware definition. Defaults to 0.
        - liquidFollowing (integer): 0=Off , 1=On. Defaults to 0.
        - submergeDepth (float): mm of immersion below liquid's surface to start dispense when using LLD. Defaults to 2.0.
        - liquidHeight (float): mm above container's base to start dispense when not using LLD. Defaults to 1.0.
        - mixCycles (integer): number of mixing cycles (1 cycle = 1 aspiration + 1 dispensing). Defaults to 0.
        - mixPosition (float): additional immersion mm below aspiration position to start mixing. Defaults to 0.0.
        - mixVolume (float): mix volume in uL. Defaults to 0.0.
        - xDisplacement (float): x displacement in mm. Defaults to 0.0.
        - yDisplacement (float): y displacement in mm. Defaults to 0.0.
        - zDisplacement (float): z displacement in mm. Defaults to 0.0.
        - airTransportRetractDist (float): mm to move up in Z after finishing the aspiration at a fixed height before aspirating 'transport air'. Defaults to 5.0.
        - touchOff (integer): 0=Off , 1=On. Defaults to 0.
        - dispPositionAboveTouch (float): mm to move up in Z after touch off detects the bottom before dispensing liquid. Defaults to 0.0.
        - zMoveAfterStep (integer): 0=Normal, 1=Minimized. Defaults to 0.
        - sideTouch (integer): 0=Off, 1=On. Defaults to 0.
    """

    logger.debug(
        "Command: %s | Labware: %s | Positions: %s | Volumes: %s",
        "dispense",
        positions[0][0].layout_name(),
        [p[0].position_id(p[1]) for p in positions],
        volumes,
    )

    if len(volumes) < len(positions):
        volumes.extend([volumes[0] for _ in range(len(volumes), len(positions))])
    elif len(volumes) > len(positions):
        raise ValueError

    if "liquidClass" not in kw_args:
        kw_args.update({"liquidClass": DEFAULT_LIQUID_CLASS_2CH})

    if len(positions) == 1:
        channelVariable = "10"
    else:
        channelVariable = "11"

    labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        commands["DISPENSE"],
        labwarePositions=labwarePositions,
        volumes=volumes,
        channelVariable=channelVariable,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def tip_pick_up_384(
    ham: HamiltonInterface,
    positions: list[tuple[Tip96, int]] | list[tuple[Tip384, int]],
    **kw_args,
) -> None:
    """
    Pick up tips (50 uL) using 384 head. Only the first position is sent to the robot to allow for variable head patterns.

    Args:
        - ham: Robot interface.
        - positions: List of tips to pick up.
    """

    logger.debug(
        "Command: %s | Labware: %s | Positions: %s",
        "tip_pick_up_384",
        positions[0][0].layout_name(),
        len(positions),
    )

    labwarePositions = compound_pos_str(positions[:1])

    cid = ham.send_command(
        commands["PICKUP384"],
        labwarePositions=labwarePositions,
        tipMode=1,
        reducedPatternMode=1,
        headPatternAsVariable=3,
        headPatternVariable=HEAD_PATTERN,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def tip_eject_384(
    ham: HamiltonInterface,
    positions: Optional[list[tuple[Tip384, int]]] = None,
    mode: int = 0,
    **kw_args,
) -> None:
    """
    Eject tips (50 uL) using 384 head.

    Args:
        - ham: Robot interface.
        - positions: List of tips to eject. Defaults to [].
        - mode: 0 for eject to provided positions, 1 for eject to pick up position, 2 for eject to default waste. Defaults to 0.
    """

    if positions is None:
        positions = []

    if positions:
        labware = positions[0][0].layout_name()
    else:
        labware = "None"

    logger.debug(
        "Command: %s | Labware: %s | Positions: %s | Mode: %s",
        "tip_eject_384",
        labware,
        len(positions),
        mode,
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
        commands["EJECT384"],
        labwarePositions=labwarePositions,
        tipEjectToKnownPosition=tipEjectToKnownPosition,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def aspirate_384(
    ham: HamiltonInterface,
    positions: list[tuple[Plate96, int]]
    | list[tuple[Plate384, int]]
    | list[tuple[Reservoir300, int]],
    volume: float,
    **kw_args,
) -> None:
    """
    Aspirate from a plate or reservoir using 384 head.

    Args:
        - ham: Robot interface.
        - positions where int is the well index and Labware the plate or reservoir to aspirate from.
        - volume: Volume to aspirate.

    Keyword Args:
        - liquidClass (string): Liquid class to use. Defaults to DEFAULT_LIQUID_CLASS_384MPH (50 uL tips with water).
        - aspirateMode (integer): 0=Normal, 1=No air gap, 2=Aspirate all volume. Defaults to 0.
        - capacitiveLLD (integer): 0=Off, 1=Max, 2=High, 3=Mid, 4=Low, 5=From labware definition. Defaults to 0.
        - liquidFollowing (integer): 0=Off , 1=On. Defaults to 0.
        - submergeDepth (float): mm of immersion below liquid's surface to start aspiration when using LLD. Defaults to 2.0.
        - liquidHeight (float): mm above container's base to start aspiration when not using LLD. Defaults to 1.0.
        - mixCycles (integer): number of mixing cycles (1 cycle = 1 aspiration + 1 dispensing). Defaults to 0.
        - mixPosition (float): additional immersion mm below aspiration position to start mixing. Defaults to 0.0.
        - mixVolume (float): mix volume in uL. Defaults to 0.0.
        - airTransportRetractDist (float): mm to move up in Z after finishing the aspiration at a fixed height before aspirating 'transport air'. Defaults to 5.0.
    """

    logger.debug(
        "Command: %s | Labware: %s | Positions: %s | Volume: %s",
        "aspirate_384",
        positions[0][0].layout_name(),
        len(positions),
        volume,
    )

    if "liquidClass" not in kw_args:
        kw_args.update({"liquidClass": DEFAULT_LIQUID_CLASS_384MPH})

    labwarePositions = compound_pos_str(positions[:1])

    cid = ham.send_command(
        commands["ASPIRATE384"],
        labwarePositions=labwarePositions,
        aspirateVolume=volume,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def dispense_384(
    ham: HamiltonInterface,
    positions: list[tuple[Plate96, int]]
    | list[tuple[Plate384, int]]
    | list[tuple[Reservoir300, int]],
    volume: float,
    **kw_args,
) -> None:
    """
    Dispense to a plate or reservoir using 384 head.

    Args:
        - ham: Robot interface.
        - positions where int is the well index and Labware the plate or reservoir to dispense to.
        - volume: Volume to dispense.

    Keyword Args:
        - liquidClass (string): Liquid class to use. Defaults to DEFAULT_LIQUID_CLASS_384MPH (50 uL tips with water).
        - dispenseMode (integer): 0=Jet Part, 1=Jet Empty, 2=Surface Part, 3=Surface Empty, 4=Jet Drain tip, 8=From liquid class, 9=Blowout tip. Defaults to 0.
        - capacitiveLLD (integer): 0=Off, 1=Max, 2=High, 3=Mid, 4=Low, 5=From labware definition. Defaults to 0.
        - liquidFollowing (integer): 0=Off , 1=On. Defaults to 0.
        - submergeDepth (float): mm of immersion below liquid's surface to start dispense when using LLD. Defaults to 2.0.
        - liquidHeight (float): mm above container's base to start dispense when not using LLD. Defaults to 1.0.
        - mixCycles (integer): number of mixing cycles (1 cycle = 1 aspiration + 1 dispensing). Defaults to 0.
        - mixPosition (float): additional immersion mm below aspiration position to start mixing. Defaults to 0.0.
        - mixVolume (float): mix volume in uL. Defaults to 0.0.
        - airTransportRetractDist (float): mm to move up in Z after finishing the aspiration at a fixed height before aspirating 'transport air'. Defaults to 5.0.
        - zMoveAfterStep (integer): 0=Normal, 1=Minimized. Defaults to 0.
        - sideTouch (integer): 0=Off, 1=On. Defaults to 0.
    """

    logger.debug(
        "Command: %s | Labware: %s | Positions: %s | Volume: %s",
        "dispense_384",
        positions[0][0].layout_name(),
        len(positions),
        volume,
    )

    if "liquidClass" not in kw_args:
        kw_args.update({"liquidClass": DEFAULT_LIQUID_CLASS_384MPH})

    labwarePositions = compound_pos_str(positions[:1])

    cid = ham.send_command(
        commands["DISPENSE384"],
        labwarePositions=labwarePositions,
        dispenseVolume=volume,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def grip_get_tip_rack(
    ham: HamiltonInterface,
    labware: Tip96 | Tip384,
    **kw_args,
) -> None:
    """
    Pick up a tip rack with the gripper.

    Args:
        - ham: Robot interface.
        - labware: Tip rack to pick up.
    """

    logger.debug(
        "Command: %s | Labware: %s", "grip_get_tip_rack", labware.layout_name()
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
        commands["GRIP_GET"],
        plateLabwarePositions=labwarePositions,
        gripForce=9,
        gripHeight=gripHeight,
        gripWidth=gripWidth,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def grip_place_tip_rack(
    ham: HamiltonInterface,
    labware: Tip96 | Tip384,
    waste: bool = False,
    eject: bool = False,
    **kw_args,
) -> None:
    """
    Place a tip rack with the gripper.

    Args:
        - ham: Robot interface.
        - labware: Tip rack to place.
        - waste: Whether to place the tip rack in the waste position. Defaults to False.
        - eject: Whether to eject the gripper tool after placing. Defaults to False.
    """

    logger.debug(
        "Command: %s | Labware: %s | Waste: %s | Eject: %s",
        "grip_place_tip_rack",
        labware.layout_name(),
        waste,
        eject,
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
        commands["GRIP_PLACE"],
        plateSequence=plateSequence,
        plateLabwarePositions=labwarePositions,
        ejectToolWhenFinish=ejectToolWhenFinish,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


# Default command templates
command_templates: dict[str, tuple[str, dict]] = {
    "initialize": ("INITIALIZE", {"initializeAlways": 0}),
    "channelTipPickUp": (
        "PICKUP",
        {
            "tipSequence": "",
            "labwarePositions": "",
            "channelVariable": "11",
            "sequenceCounting": 0,
            "channelUse": 1,
        },
    ),
    "channelTipEject": (
        "EJECT",
        {
            "wasteSequence": "",
            "labwarePositions": "",
            "channelVariable": "11",
            "sequenceCounting": 0,
            "channelUse": 1,
            "useDefaultWaste": 0,
        },
    ),
    "channelAspirate": (
        "ASPIRATE",
        {
            "aspirateSequence": "",
            "labwarePositions": "",
            "volumes": None,
            "channelVariable": "11",
            "liquidClass": None,
            "sequenceCounting": 0,
            "channelUse": 1,
            "aspirateMode": 0,
            "capacitiveLLD": 0,
            "pressureLLD": 0,
            "liquidFollowing": 0,
            "submergeDepth": 2.0,
            "liquidHeight": 1.0,
            "maxLLdDifference": 0.0,
            "mixCycles": 0,
            "mixPosition": 0.0,
            "mixVolume": 0.0,
            "xDisplacement": 0.0,
            "yDisplacement": 0.0,
            "zDisplacement": 0.0,
            "airTransportRetractDist": 5.0,
            "touchOff": 0,
            "aspPosAboveTouch": 0.0,
        },
    ),
    "channelDispense": (
        "DISPENSE",
        {
            "dispenseSequence": "",
            "labwarePositions": "",
            "volumes": None,
            "channelVariable": "11",
            "liquidClass": None,
            "sequenceCounting": 0,
            "channelUse": 1,
            "dispenseMode": 8,
            "capacitiveLLD": 0,
            "liquidFollowing": 0,
            "submergeDepth": 2.0,
            "liquidHeight": 1.0,
            "mixCycles": 0,
            "mixPosition": 0.0,
            "mixVolume": 0.0,
            "xDisplacement": 0.0,
            "yDisplacement": 0.0,
            "zDisplacement": 0.0,
            "airTransportRetractDist": 5.0,
            "touchOff": 0,
            "dispPositionAboveTouch": 0.0,
            "zMoveAfterStep": 1,
            "sideTouch": 0,
        },
    ),
    "mph384TipPickUp": (
        "PICKUP384",
        {
            "tipSequence": "",
            "labwarePositions": "",
            "tipMode": 0,
            "headPatternVariable": "1" * 384,
            "sequenceCounting": 0,
            "reducedPatternMode": 0,
            "headPatternAsVariable": 0,
            "pickUpFromTipLifter": 0,
        },
    ),
    "mph384TipEject": (
        "EJECT384",
        {
            "wasteSequence": "",
            "labwarePositions": "",
            "sequenceCounting": 0,
            "tipEjectToKnownPosition": 0,
        },
    ),
    "mph384Aspirate": (
        "ASPIRATE384",
        {
            "aspirateSequence": "",
            "labwarePositions": "",
            "aspirateVolume": None,
            "liquidClass": None,
            "sequenceCounting": 0,
            "aspirateMode": 0,
            "capacitiveLLD": 0,
            "liquidFollowing": 0,
            "submergeDepth": 2.0,
            "liquidHeight": 1.0,
            "mixCycles": 0,
            "mixPosition": 0.0,
            "mixVolume": 0.0,
            "airTransportRetractDist": 5.0,
        },
    ),
    "mph384Dispense": (
        "DISPENSE384",
        {
            "dispenseSequence": "",
            "labwarePositions": "",
            "dispenseVolume": None,
            "liquidClass": None,
            "sequenceCounting": 0,
            "dispenseMode": 8,
            "capacitiveLLD": 0,
            "liquidFollowing": 0,
            "submergeDepth": 2.0,
            "liquidHeight": 1.0,
            "mixCycles": 0,
            "mixPosition": 0.0,
            "mixVolume": 0.0,
            "airTransportRetractDist": 5.0,
            "zMoveAfterStep": 0,
            "sideTouch": 0,
        },
    ),
    "gripGet": (
        "GRIP_GET",
        {
            "plateSequence": "",
            "plateLabwarePositions": "",
            "lidSequence": "",
            "lidLabwarePositions": "",
            "toolSequence": "CORE_Grip",
            "gripForce": 7,
            "gripperToolChannel": 2,
            "sequenceCounting": 0,
            "gripWidth": 82.0,
            "gripHeight": 9.0,
            "widthBefore": 88,
            "gripSpeed": 275.0,
            "zSpeed": 125.0,
            "transportMode": 0,
            "checkPlate": 0,
        },
    ),
    "gripPlace": (
        "GRIP_PLACE",
        {
            "plateSequence": "",
            "plateLabwarePositions": "",
            "lidSequence": "",
            "lidLabwarePositions": "",
            "toolSequence": "CORE_Grip",
            "sequenceCounting": 0,
            "movementType": 0,
            "transportMode": 0,
            "ejectToolWhenFinish": 1,
            "zSpeed": 125.0,
            "platePressOnDistance": 0.0,
            "xAcceleration": 4,
        },
    ),
}

# Make commands available locally
commands = {}
for command, template in command_templates.items():
    command_name, command_dict = template
    command = HamiltonCmdTemplate(template, list(command_dict.keys()))
    commands[command_name] = command

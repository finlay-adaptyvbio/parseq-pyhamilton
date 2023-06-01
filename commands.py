import logging

from pyhamilton import HamiltonInterface, HamiltonCmdTemplate, Plate96, Plate384, Tip96
from labware import Tip384, Reservoir300, Lid, EppiCarrier24

# Logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Defaults
DEFAULT_GRIP_TOOL_SEQUENCE = "CORE_Grip"
DEFAULT_LIQUID_CLASS_2CH = "StandardVolume_Water_DispenseJet_Empty"
DEFAULT_LIQUID_CLASS_384MPH = "50ulTip_conductive_384COREHead_Water_DispenseJet_Empty"

HEAD_PATTERN = "1" + "0" * (95)


# Position formatting functions
def labware_pos_str(labware, idx):
    return labware.layout_name() + ", " + labware.position_id(idx)


def compound_pos_str(pos_tuples):
    present_pos_tups = [pt for pt in pos_tuples if pt is not None]
    return ";".join(
        (labware_pos_str(labware, idx) for labware, idx in present_pos_tups)
    )


# Commands
def initialize(ham: HamiltonInterface):
    logger.debug(f"Command: {'initialize'}")

    cid = ham.send_command(commands["INITIALIZE"])

    ham.wait_on_response(cid, raise_first_exception=True)


def grip_get(
    ham: HamiltonInterface,
    labware: Plate96 | Plate384 | Lid,
    mode: int = 0,
    **kw_args,
):
    logger.debug(
        f"Command: {'grip_get'} | Labware: {labware.layout_name()} | Mode: {mode}"
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
):
    logger.debug(
        f"Command: {'grip_place'} | Labware: {labware.layout_name()} |"
        f" Mode: {mode} | Eject: {eject}"
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
):
    logger.debug(
        f"Command: {'tip_pick_up'} | Labware:"
        f" {positions[0][0].layout_name()} | Positions:"
        f" {[p[0].position_id(p[1]) for p in positions]}"
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
    positions: list[tuple[Tip96, int]] = [],
    waste: bool = False,
    **kw_args,
):
    if positions:
        labware = positions[0][0].layout_name()
    else:
        labware = "None"

    logger.debug(
        f"Command: {'tip_eject'} | Labware: {labware} | Positions:"
        f" {[p[0].position_id(p[1]) for p in positions]} | Waste: {waste}"
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
):
    logger.debug(f"Command: {'grip_eject'}")

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
):
    logger.debug(
        f"Command: {'aspirate'} | Labware:"
        f" {positions[0][0].layout_name()} | Positions:"
        f" {[p[0].position_id(p[1]) for p in positions]} | Volumes:"
        f" {volumes}"
    )

    if len(volumes) < len(positions):
        volumes.extend([volumes[0] for _ in range(len(volumes), len(positions))])
    elif len(volumes) > len(positions):
        raise ValueError

    if "liquidClass" not in kw_args:
        kw_args.update({"liquidClass": DEFAULT_LIQUID_CLASS_2CH})

    labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        commands["ASPIRATE"],
        labwarePositions=labwarePositions,
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
):
    logger.debug(
        f"Command: {'dispense'} | Labware:"
        f" {positions[0][0].layout_name()} | Positions:"
        f" {[p[0].position_id(p[1]) for p in positions]} | Volumes:"
        f" {volumes}"
    )

    if len(volumes) < len(positions):
        volumes.extend([volumes[0] for _ in range(len(volumes), len(positions))])
    elif len(volumes) > len(positions):
        raise ValueError

    if "liquidClass" not in kw_args:
        kw_args.update({"liquidClass": DEFAULT_LIQUID_CLASS_2CH})

    labwarePositions = compound_pos_str(positions)

    cid = ham.send_command(
        commands["DISPENSE"],
        labwarePositions=labwarePositions,
        volumes=volumes,
        **kw_args,
    )

    ham.wait_on_response(cid, raise_first_exception=True)


def tip_pick_up_384(
    ham: HamiltonInterface,
    positions: list[tuple[Tip96, int]] | list[tuple[Tip384, int]],
    **kw_args,
):
    logger.debug(
        f"Command: {'tip_pick_up_384'} | Labware:"
        f" {positions[0][0].layout_name()} | Positions: {len(positions)}"
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
    positions: list[tuple[Tip384, int]] = [],
    mode: int = 0,
    **kw_args,
):
    if positions:
        labware = positions[0][0].layout_name()
    else:
        labware = "None"

    logger.debug(
        f"Command: {'tip_eject_384'} | Labware:"
        f" {labware} | Positions: {len(positions)} |"
        f" Mode: {mode}"
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
):
    logger.debug(
        f"Command: {'aspirate_384'} | Labware:"
        f" {positions[0][0].layout_name()} | Positions: {len(positions)} |"
        f" Volume: {volume}"
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
):
    logger.debug(
        f"Command: {'dispense_384'} | Labware:"
        f" {positions[0][0].layout_name()} | Positions: {len(positions)} |"
        f" Volume: {volume}"
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
):
    logger.debug(f"Command: {'grip_get_tip_rack'} | Labware: {labware.layout_name()}")

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
):
    logger.debug(
        f"Command: {'grip_place_tip_rack'} | Labware:"
        f" {labware.layout_name()} | Waste: {waste} | Eject: {eject}"
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


# Default channel patterns
_channel_patt_2 = "11"
_channel_patt_384 = "1" * 384

# Default command templates
command_templates = {
    "initialize": ("INITIALIZE", {"initializeAlways": 0}),
    "channelTipPickUp": (
        "PICKUP",
        {
            "tipSequence": (
                ""
            ),  # (string) leave empty if you are going to provide specific labwarePositions below
            "labwarePositions": (
                ""
            ),  # (string) leave empty if you are going to provide a sequence name above.'LabwareId1, positionId1; LabwareId2,positionId2; ....'
            "channelVariable": (
                _channel_patt_2
            ),  # (string)  channel pattern e.g. '11110000'
            "sequenceCounting": 0,  # (integer) 0=don´t autoincrement,  1=Autoincrement
            "channelUse": (
                1
            ),  # (integer) 1=use all sequence positions (no empty wells), 2=keep channel pattern
        },
    ),
    "channelTipEject": (
        "EJECT",
        {
            "wasteSequence": (
                ""
            ),  # (string) leave empty if you are going to provide specific labware-positions below or ejecting to default waste
            "labwarePositions": (
                ""
            ),  # (string) leave empty if you are going to provide a sequence name above.'LabwareId1, positionId1; LabwareId2,positionId2; ....'
            "channelVariable": (
                _channel_patt_2
            ),  # (string) channel pattern e.g. "11110000"
            "sequenceCounting": (
                0
            ),  # (integer) 0=don´t autoincrement,  1=Autoincrement.  Value omitted if ejecting to default waste
            "channelUse": (
                1
            ),  # (integer) 1=use all sequence positions (no empty wells), 2=keep channel pattern
            "useDefaultWaste": (
                0
            ),  # (integer) 0=eject to custom waste sequence,  1=Use default waste
        },
    ),
    "channelAspirate": (
        "ASPIRATE",
        {
            "aspirateSequence": (
                ""
            ),  # (string) leave empty if you are going to provide specific labware-positions below
            "labwarePositions": (
                ""
            ),  # (string) leave empty if you are going to provide a sequence name above. 'LabwareId1, positionId1; LabwareId2,positionId2; ....'
            "volumes": (
                None
            ),  # (float or string) enter a single value used for all channels or enter an array of values for each channel like [10.0,15.5,11.2]
            "channelVariable": (
                _channel_patt_2
            ),  # (string) channel pattern e.g. "11110000"
            "liquidClass": None,  # (string)
            "sequenceCounting": 0,  # (integer) 0=don´t autoincrement,  1=Autoincrement
            "channelUse": (
                1
            ),  # (integer) 1=use all sequence positions (no empty wells), 2=keep channel pattern
            "aspirateMode": (
                0
            ),  # (integer) 0=Normal Aspiration, 1=Consecutive (don´t aspirate blowout), 2=Aspirate all
            "capacitiveLLD": (
                0
            ),  # (integer) 0=Off, 1=Max, 2=High, 3=Mid, 4=Low, 5=From labware definition
            "pressureLLD": (
                0
            ),  # (integer) 0=Off, 1=Max, 2=High, 3=Mid, 4=Low, 5=From liquid class definition
            "liquidFollowing": 0,  # (integer) 0=Off , 1=On
            "submergeDepth": (
                2.0
            ),  # (float) mm of immersion below liquid´s surface to start aspiration when using LLD
            "liquidHeight": (
                1.0
            ),  # (float) mm above container´s bottom to start aspiration when not using LLD
            "maxLLdDifference": (
                0.0
            ),  # (float) max mm height different between cLLD and pLLD detected liquid levels
            "mixCycles": (
                0
            ),  # (integer) number of mixing cycles (1 cycle = 1 asp + 1 disp)
            "mixPosition": (
                0.0
            ),  # (float) additional immersion mm below aspiration position to start mixing
            "mixVolume": 0.0,  # (float) mix volume
            "xDisplacement": 0.0,
            "yDisplacement": 0.0,
            "zDisplacement": 0.0,
            "airTransportRetractDist": (
                5.0
            ),  # (float) mm to move up in Z after finishing the aspiration at a fixed height before aspirating 'transport air'
            "touchOff": 0,  # (integer) 0=Off , 1=On
            "aspPosAboveTouch": (
                0.0
            ),  # (float)  mm to move up in Z after touch off detects the bottom before aspirating liquid
        },
    ),
    "channelDispense": (
        "DISPENSE",
        {
            "dispenseSequence": (
                ""
            ),  # (string) leave empty if you are going to provide specific labware-positions below
            "labwarePositions": (
                ""
            ),  # (string) leave empty if you are going to provide a sequence name above. 'LabwareId1, positionId1; LabwareId2,positionId2; ....'
            "volumes": (
                None
            ),  # (float or string) enter a single value used for all channels or enter an array of values for each channel like [10.0,15.5,11.2]
            "channelVariable": (
                _channel_patt_2
            ),  # (string) channel pattern e.g. "11110000"
            "liquidClass": None,  # (string)
            "sequenceCounting": 0,  # (integer) 0=don´t autoincrement,  1=Autoincrement
            "channelUse": (
                1
            ),  # (integer) 1=use all sequence positions (no empty wells), 2=keep channel pattern
            "dispenseMode": (
                8
            ),  # (integer) 0=Jet Part, 1=Jet Empty, 2=Surface Part, 3=Surface Empty, 4=Jet Drain tip, 8=From liquid class, 9=Blowout tip
            "capacitiveLLD": (
                0
            ),  # (integer) 0=Off, 1=Max, 2=High, 3=Mid, 4=Low, 5=From labware definition
            "liquidFollowing": 0,  # (integer) 0=Off , 1=On
            "submergeDepth": (
                2.0
            ),  # (float) mm of immersion below liquid´s surface to start dispense when using LLD
            "liquidHeight": (
                1.0
            ),  # (float) mm above container´s bottom to start dispense when not using LLD
            "mixCycles": (
                0
            ),  # (integer) number of mixing cycles (1 cycle = 1 asp + 1 disp)
            "mixPosition": (
                0.0
            ),  # (float) additional immersion mm below dispense position to start mixing
            "mixVolume": 0.0,  # (float) mix volume
            "xDisplacement": 0.0,
            "yDisplacement": 0.0,
            "zDisplacement": 0.0,
            "airTransportRetractDist": (
                5.0
            ),  # (float) mm to move up in Z after finishing the dispense at a fixed height before aspirating 'transport air'
            "touchOff": 0,  # (integer) 0=Off , 1=On
            "dispPositionAboveTouch": (
                0.0
            ),  # (float) mm to move up in Z after touch off detects the bottom, before dispense
            "zMoveAfterStep": (
                1
            ),  # (integer) 0=normal, 1=Minimized (Attention!!! this depends on labware clearance height, can crash).
            "sideTouch": 0,  # (integer) 0=Off , 1=On
        },
    ),
    "mph384TipPickUp": (
        "PICKUP384",
        {
            "tipSequence": (
                ""
            ),  # (string) leave empty if you are going to provide specific labware-positions below
            "labwarePositions": (
                ""
            ),  # (string) leave empty if you are going to provide a sequence name above. 'LabwareId1, positionId1; LabwareId2,positionId2; ....' Must contain 96 values
            "tipMode": 0,  # (integer) 0=All, 1=96 Tips, 2=Tip lifter
            "headPatternVariable": (
                _channel_patt_384
            ),  # (string) channel Variable e.g. "11110000...." . Must contain 96 values
            "sequenceCounting": 0,  # (integer) 0=don´t autoincrement,  1=Autoincrement
            "reducedPatternMode": (
                0
            ),  # (integer) 0=All (not reduced), 1=One channel, 2=Quarter  3=Row(s), 4=Column(s)
            "headPatternAsVariable": (
                0
            ),  # (integer) 0=Off, 1=Column pattern, 2=384 manual pattern, 3=96 manual pattern, 4=Row pattern
            "pickUpFromTipLifter": (
                0
            ),  # (integer) 0=Off, 1= One column, 2=Two columns, 3=All remaining tips
        },
    ),
    "mph384TipEject": (
        "EJECT384",
        {
            "wasteSequence": (
                ""
            ),  # (string) leave empty if you are going to provide specific labware-positions below or ejecting to default waste
            "labwarePositions": (
                ""
            ),  # (string) leave empty if you are going to provide a sequence name above. 'LabwareId1, positionId1; LabwareId2,positionId2; ....'
            "sequenceCounting": (
                0
            ),  # (integer)  0=don´t autoincrement,  1=Autoincrement.  Value omitted if ejecting to default waste
            "tipEjectToKnownPosition": (
                0
            ),  # (integer) 0=Eject to specified sequence position,  1=Eject on tip pick up position, 2=Eject on default waste
        },
    ),
    "mph384Aspirate": (
        "ASPIRATE384",
        {
            "aspirateSequence": (
                ""
            ),  # (string) leave empty if you are going to provide specific labware-positions below
            "labwarePositions": (
                ""
            ),  # (string) leave empty if you are going to provide a sequence name above. LabwareId1, positionId1; LabwareId2,positionId2; ....
            "aspirateVolume": (
                None
            ),  # (float)  single volume used for all channels in the head. There´s no individual control of each channel volume in multi-probe heads.
            "liquidClass": None,  # (string)
            "sequenceCounting": 0,  # (integer)  0=don´t autoincrement,  1=Autoincrement
            "aspirateMode": (
                0
            ),  # (integer) 0=Normal Aspiration, 1=Consecutive (don´t aspirate blowout), 2=Aspirate all
            "capacitiveLLD": (
                0
            ),  # (integer) 0=Off, 1=Max, 2=High, 3=Mid, 4=Low, 5=From labware definition
            "liquidFollowing": 0,  # (integer) 0=Off , 1=On
            "submergeDepth": (
                2.0
            ),  # (float) mm of immersion below liquid´s surface to start aspiration when using LLD
            "liquidHeight": (
                1.0
            ),  # (float) mm above container´s bottom to start aspiration when not using LLD
            "mixCycles": (
                0
            ),  # (integer) number of mixing cycles (1 cycle = 1 asp + 1 disp)
            "mixPosition": (
                0.0
            ),  # (float) additional immersion mm below aspiration position to start mixing
            "mixVolume": 0.0,  # (float) mix volume
            "airTransportRetractDist": (
                5.0
            ),  # (float) mm to move up in Z after finishing the aspiration at a fixed height before aspirating 'transport air'
        },
    ),
    "mph384Dispense": (
        "DISPENSE384",
        {
            "dispenseSequence": (
                ""
            ),  # (string) leave empty if you are going to provide specific labware-positions below
            "labwarePositions": (
                ""
            ),  # (string) leave empty if you are going to provide a sequence name above. LabwareId1, positionId1; LabwareId2,positionId2; ....
            "dispenseVolume": (
                None
            ),  # (float) single volume used for all channels in the head. There´s no individual control of each channel volume in multi-probe heads.
            "liquidClass": None,  # (string)
            "sequenceCounting": 0,  # (integer)  0=don´t autoincrement,  1=Autoincrement
            "dispenseMode": (
                8
            ),  # (integer) 0=Jet Part, 1=Jet Empty, 2=Surface Part, 3=Surface Empty,4=Jet Drain tip, 8=From liquid class, 9=Blowout tip
            "capacitiveLLD": (
                0
            ),  # (integer) 0=Off, 1=Max, 2=High, 3=Mid, 4=Low, 5=From labware definition
            "liquidFollowing": 0,  # (integer)  0=Off , 1=On
            "submergeDepth": (
                2.0
            ),  # (float) mm of immersion below liquid´s surface to start dispense when using LLD
            "liquidHeight": (
                1.0
            ),  # (float) mm above container´s bottom to start dispense when not using LLD
            "mixCycles": (
                0
            ),  # (integer)  number of mixing cycles (1 cycle = 1 asp + 1 disp)
            "mixPosition": (
                0.0
            ),  # (float)  additional immersion mm below dispense position to start mixing
            "mixVolume": 0.0,  # (float)  mix volume
            "airTransportRetractDist": (
                5.0
            ),  # (float) mm to move up in Z after finishing the dispense at a fixed height before aspirating 'transport air'
            "zMoveAfterStep": (
                0
            ),  # (integer) 0=normal, 1=Minimized (Attention!!! this depends on labware clearance height, can crash).
            "sideTouch": 0,  # (integer) 0=Off , 1=On
        },
    ),
    "gripGet": (
        "GRIP_GET",
        {
            "plateSequence": (
                ""
            ),  # leave empty if you are going to provide specific plate labware-position below
            "plateLabwarePositions": (
                ""
            ),  # leave empty if you are going to provide a plate sequence name above. LabwareId1, positionId1;
            "lidSequence": (
                ""
            ),  # leave empty if you don´t use lid or if you are going to provide specific plate labware-positions below or ejecting to default waste
            "lidLabwarePositions": (
                ""
            ),  # leave empty if you are going to provide a plate sequence name above. LabwareId1, positionId1;
            "toolSequence": "CORE_Grip",  # sequence name of the CO-RE Gripper
            "gripForce": 7,  # (integer) 0-9, from lowest to highest
            "gripperToolChannel": (
                2
            ),  # specifies the higher of two consecutive integers representing the CO-RE gripper channels.
            "sequenceCounting": (
                0
            ),  # (integer) 0=don´t autoincrement plate sequence,  1=Autoincrement
            "gripWidth": 82.0,  # (float) mm
            "gripHeight": 9.0,  # (float) mm
            "widthBefore": 88,  # (float) mm width before gripping
            "gripSpeed": 275.0,  # (float) mm/s. Must be supplied
            "zSpeed": 125.0,  # (float) mm/s. Must be supplied
            "transportMode": 0,  # (integer) 0=Plate only, 1=Lid only ,2=Plate with lid
            "checkPlate": 0,  # (integer)
        },
    ),
    "gripMove": (
        "GRIP_MOVE",
        {
            "plateSequence": (
                ""
            ),  # leave empty if you are going to provide specific plate labware-position below
            "xAcceleration": (
                4
            ),  # (integer) 1-5 from slowest to fastest, where 4 is default
            "plateLabwarePositions": (
                ""
            ),  # leave empty if you don´t use lid or if you are going to provide specific plate labware-positions below or ejecting to default waste
            "xDisplacement": 0.0,
            "yDisplacement": 0.0,
            "zDisplacement": 0.0,
        },
    ),
    "gripPlace": (
        "GRIP_PLACE",
        {
            "plateSequence": (
                ""
            ),  # leave empty if you are going to provide specific plate labware-position below
            "plateLabwarePositions": (
                ""
            ),  # leave empty if you are going to provide a plate sequence name above. LabwareId1, positionId1;
            "lidSequence": (
                ""
            ),  # leave empty if you don´t use lid or if you are going to provide specific plate labware-positions below or ejecting to default waste
            "lidLabwarePositions": (
                ""
            ),  # leave empty if you are going to provide a plate sequence name above. LabwareId1, positionId1;
            "toolSequence": (
                "CORE_Grip"
            ),  # sequence name of the iSWAP. leave empty if you are going to provide a plate sequence name above. LabwareId1, positionId1;
            "sequenceCounting": (
                0
            ),  # (integer) 0=don´t autoincrement plate sequence,  1=Autoincrement
            "movementType": 0,  # (integer) 0=To carrier, 1=Complex movement
            "transportMode": 0,  # (integer) 0=Plate only, 1=Lid only ,2=Plate with lid
            "ejectToolWhenFinish": 1,  # (integer) 0=Off, 1=On
            "zSpeed": 125.0,  # (float) mm/s
            "platePressOnDistance": (
                0.0
            ),  # (float) lift-up distance [mm] (only used if 'movement type' is set to 'complex movement'),
            "xAcceleration": (
                4
            ),  # (integer) 1-5 from slowest to fastest, where 4 is default
        },
    ),
}

# Make commands available locally
commands = {}
for template in command_templates:
    command_name, command_dict = command_templates[template]
    command = HamiltonCmdTemplate(template, list(command_dict.keys()))
    commands[command_name] = command

from pyhamilton import HamiltonInterface

from pyhamilton import (
    HHS_CREATE_STAR_DEVICE,
    HHS_START_SHAKER_TIMED,
    HHS_WAIT_FOR_SHAKER,
    HHS_STOP_SHAKER,
)
import commands as cmd

import time


def hhs_init(ham: HamiltonInterface):
    return_field = ["step-return2"]
    cmd = ham.send_command(HHS_CREATE_STAR_DEVICE, starDevice="ML_STAR", usedNode=1)
    response = ham.wait_on_response(
        cmd, raise_first_exception=True, return_data=return_field
    )
    return response.return_data[0]


def hhs_start_timer(ham: HamiltonInterface, hhs: int, speed: int, time: int):
    cmd = ham.send_command(
        HHS_START_SHAKER_TIMED, deviceNumber=hhs, shakingSpeed=speed, shakingTime=time
    )
    return ham.wait_on_response(cmd, raise_first_exception=True)


def hhs_wait_timer(ham: HamiltonInterface, hhs: int):
    cmd = ham.send_command(HHS_WAIT_FOR_SHAKER, deviceNumber=hhs)
    ham.wait_on_response(cmd, raise_first_exception=True)


def hhs_stop(ham: HamiltonInterface, hhs: int):
    cmd = ham.send_command(HHS_STOP_SHAKER, deviceNumber=hhs)
    ham.wait_on_response(cmd, raise_first_exception=True)


if __name__ == "__main__":
    with HamiltonInterface(simulate=True) as ham:
        cmd.initialize(ham)
        hhs = hhs_init(ham)
        print(hhs_start_timer(ham, hhs, 500, 10))
        time.sleep(10)
        hhs_wait_timer(ham, hhs)
        hhs_stop(ham, hhs)

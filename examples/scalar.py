from itertools import product
from cycler import cycler
from bluesky_web_plots.callback import WebPlotsCallback
from time import sleep
from bluesky.run_engine import RunEngine
import bluesky.plan_stubs as bps
import bluesky.plans as bpp

from ophyd_async.core import StandardReadable
from ophyd_async.sim import SimMotor
from ophyd_async.core import Device


def scan_with_settle(iterable):
    motor1 = SimMotor(name="motor1")
    motor2 = SimMotor(name="motor2")
    yield from bps.open_run()
    for x_pos, y_pos in iterable:
        yield from bps.mv(motor1, x_pos, motor2, y_pos)
        yield from bps.one_shot([motor1, motor2])
        yield from bps.sleep(0.25)
    yield from bps.close_run()


def scan_with_settle(iterable):
    motor1 = SimMotor(name="motor3")
    motor2 = SimMotor(name="motor2")
    yield from bps.open_run()
    for x_pos, y_pos in iterable:
        yield from bps.mv(motor1, x_pos, motor2, y_pos)
        yield from bps.one_shot([motor1, motor2])
        yield from bps.sleep(0.25)
    yield from bps.close_run()


RE = RunEngine()
RE.subscribe(WebPlotsCallback())
RE(scan_with_settle(product(range(10), range(100))))
RE(scan_with_settle(product(range(10), range(100))))

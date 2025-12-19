from itertools import product, chain
from bluesky_web_plots.structures import unpack_structures
from bluesky_web_plots.structures.scalar import Scalar, PlotAgainst
from bluesky_web_plots import WebPlotCallback
from bluesky.protocols import Readable
from bluesky.run_engine import RunEngine
import ophyd_async.plan_stubs as oaps
import numpy as np
from ophyd_async.epics.core import EpicsDevice, PvSuffix
from ophyd_async.core import (
    Array1D,
    StandardReadable,
    SignalR,
    set_mock_value,
    StandardReadableFormat,
)
import bluesky.plan_stubs as bps

from ophyd_async.core import FlyMotorInfo
from ophyd_async.sim import SimMotor
from typing import Iterable, Annotated as A


class McaDetector(EpicsDevice, StandardReadable):
    value: A[
        SignalR[Array1D[np.float64]],
        PvSuffix("VALUE"),
        StandardReadableFormat.HINTED_SIGNAL,
    ]


def sample_map(
    movables: list[SimMotor],
    positions: list[Iterable[float]],
    detectors: list[Readable] | None = None,
):
    detectors = detectors or []
    for position in product(*positions):
        yield from bps.mv(*list(chain(*zip(movables, position))))
        yield from bps.one_shot(movables + detectors)


def plan():
    mca = McaDetector(prefix="MCA", name="mca")
    motor1 = SimMotor(name="motor1")
    motor2 = SimMotor(name="motor2")
    motor3 = SimMotor(name="motor3")
    yield from bps.open_run(
        md={
            "hints": unpack_structures(
                Scalar(name=motor1.name, plot_against=PlotAgainst.TIME)
            )
        }
    )
    yield from oaps.ensure_connected(motor1, motor2, motor3, mca, mock=True)
    set_mock_value(mca.value, np.arange(1024))
    # Set velocity of motors, positions not used in the run.
    yield from bps.prepare(
        motor1, FlyMotorInfo(start_position=0, end_position=1, time_for_move=0.25)
    )
    yield from bps.prepare(
        motor2, FlyMotorInfo(start_position=0, end_position=1, time_for_move=0.25)
    )
    yield from bps.prepare(
        motor3, FlyMotorInfo(start_position=0, end_position=1, time_for_move=0.25)
    )
    yield from bps.close_run()

    yield from bps.open_run()
    yield from sample_map([motor1, motor2], [range(10), range(5)], detectors=[mca])
    yield from bps.close_run()

    yield from bps.open_run()
    yield from sample_map([motor2, motor3], [range(2), range(2)], detectors=[mca])
    yield from bps.close_run()

    yield from bps.open_run()
    yield from sample_map(
        [motor1, motor2, motor3], [range(3), range(4), range(5)], detectors=[mca]
    )
    yield from bps.close_run()


RE = RunEngine()
RE.subscribe(WebPlotCallback())
RE(plan())

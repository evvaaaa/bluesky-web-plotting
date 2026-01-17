import asyncio
import time
from itertools import product, chain
from ophyd_async import plan_stubs as oaps
from bluesky_web_plots.structures import unpack_structures
from bluesky_web_plots.structures.scalar import Scalar, PlotAgainst
from bluesky_web_plots import PlotlyCallback
from bluesky.protocols import Readable
from bluesky.run_engine import RunEngine
from ophyd_async.core import set_mock_value, callback_on_mock_put
import numpy as np
from ophyd_async.core import (
    Array1D,
    StandardReadable,
    soft_signal_r_and_setter,
    soft_signal_rw,
    StandardReadableFormat,
    AsyncStatus,
)
import bluesky.plan_stubs as bps

from typing import Iterable


class SomeActuator(StandardReadable):
    def __init__(self, name="", sim_velocity=float("inf"), initial=0):
        super().__init__(name=name)
        with self.add_children_as_readables(
            format=StandardReadableFormat.HINTED_SIGNAL
        ):
            self.readback, self.readback_setter = soft_signal_r_and_setter(
                float, name="readback", initial_value=initial
            )
        with self.add_children_as_readables(format=StandardReadableFormat.CHILD):
            self.setpoint = soft_signal_rw(
                float, name="setpoint", initial_value=initial
            )
        with self.add_children_as_readables(
            format=StandardReadableFormat.CONFIG_SIGNAL
        ):
            self.velocity, set_velocity = soft_signal_r_and_setter(
                float, name="velocity"
            )
        set_velocity(sim_velocity)

    @AsyncStatus.wrap
    async def set(self, value: float) -> None:
        wait_time = abs((await self.readback.get_value()) - value) / (
            await self.velocity.get_value()
        )
        await self.setpoint.set(value)
        await asyncio.sleep(wait_time)
        self.readback_setter(value)


class Mca(StandardReadable):
    def __init__(self, name=""):
        super().__init__(name=name)
        with self.add_children_as_readables():
            self.value, self.set_value = soft_signal_r_and_setter(
                Array1D[np.int64], name="value"
            )
            self.mean, self.set_mean = soft_signal_r_and_setter(int, name="mean")


def sample_map(
    movables: list[SomeActuator],
    positions: list[Iterable[float]],
    detectors: list[Readable] | None = None,
):
    yield from bps.open_run()
    detectors = detectors or []
    for position in product(*positions):
        yield from bps.mv(*list(chain(*zip(movables, position))))
        yield from bps.one_shot(movables + detectors)
    yield from bps.close_run()


mca = Mca(name="mca")
motor1 = SomeActuator(name="motor1")
motor2 = SomeActuator(name="motor2")
motor3 = SomeActuator(name="motor3", initial=90)


num_channels = 1024
channels = np.arange(num_channels)
peak = 50_000_000
sigma = 100  # Adjust for width


MOTOR_RANGES = (0, 100)


def setup_mock_logic(
    motor1: SomeActuator, motor2: SomeActuator, motor3: SomeActuator, mca: Mca
):
    # Best MCA reading at the optimum motor postition.
    PEAK = 50_000_000
    MCA_AT_X_Y_Z_50_99_67 = PEAK * np.exp(-0.5 * ((np.arange(1024) - 512) / 12) ** 2)

    def get_motor_scale_factor(highest_at, sigma):
        highest_at_on_waveform = int(
            highest_at / (MOTOR_RANGES[1] - MOTOR_RANGES[0]) * 10_000
        )
        return np.exp(
            -((np.arange(10_000) - highest_at_on_waveform) ** 2) / (2 * sigma**2)
        )

    MOTOR1_GAUSSIAN = get_motor_scale_factor(50, 1000)
    MOTOR2_GAUSSIAN = get_motor_scale_factor(99, 80000)
    MOTOR3_GAUSSIAN = get_motor_scale_factor(67, 1000)

    async def update_mca_for_motor(_, wait=True):
        simulated_guassian = MCA_AT_X_Y_Z_50_99_67.copy()
        for motor, motor_sim_values in (
            (motor1, MOTOR1_GAUSSIAN),
            (motor2, MOTOR2_GAUSSIAN),
            (motor3, MOTOR3_GAUSSIAN),
        ):
            simulated_guassian *= motor_sim_values[
                int(
                    10_000
                    * (
                        await motor.readback.get_value()
                        / (MOTOR_RANGES[1] - MOTOR_RANGES[0])
                    )
                )  # type: ignore
            ]
        set_mock_value(mca.value, simulated_guassian)
        set_mock_value(mca.mean, int(np.mean(simulated_guassian)))

    callback_on_mock_put(motor1.setpoint, update_mca_for_motor)
    callback_on_mock_put(motor2.setpoint, update_mca_for_motor)
    callback_on_mock_put(motor3.setpoint, update_mca_for_motor)


def prepare():
    yield from bps.open_run(
        md={
            "hints": unpack_structures(
                Scalar(name=motor1.readback.name, plot_against=PlotAgainst.TIME)
            )
        }
    )
    yield from oaps.ensure_connected(*[motor1, motor2, motor3, mca], mock=True)
    setup_mock_logic(motor1, motor2, motor3, mca)
    yield from bps.close_run()


RE = RunEngine()
RE.subscribe(PlotlyCallback())
RE(prepare())
RE(
    sample_map(
        [motor1, motor2],
        [np.linspace(0, 10, 20), np.linspace(10, 30, 20)],
        detectors=[mca],
    )
)
RE(
    sample_map(
        [motor1, motor2, motor3],
        [np.linspace(0, 10, 20), np.linspace(60, 70, 20), np.linspace(50, 90, 20)],
        detectors=[mca],
    )
)
# Keep the server alive for a bit to ensure the viewer has caught up
# not necessary in ipython/jupyter/as a service.
time.sleep(1)

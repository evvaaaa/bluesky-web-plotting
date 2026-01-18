import asyncio

import numpy as np
from ophyd_async.core import (
    Array1D,
    AsyncStatus,
    StandardReadable,
    StandardReadableFormat,
    callback_on_mock_put,
    set_mock_value,
    soft_signal_r_and_setter,
    soft_signal_rw,
)


class SomeActuator(StandardReadable):
    def __init__(self, name="", sim_velocity=100, initial=0):
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


num_channels = 1024
channels = np.arange(num_channels)
peak = 50_000_000
sigma = 100  # Adjust for width


MOTOR_RANGES = (0, 100)


def setup_sample_map_mock_logic(motor1: SomeActuator, motor2: SomeActuator, mca: Mca):
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

    async def update_mca_for_motor(_, wait=True):
        simulated_guassian = MCA_AT_X_Y_Z_50_99_67.copy()
        for motor, motor_sim_values in (
            (motor1, MOTOR1_GAUSSIAN),
            (motor2, MOTOR2_GAUSSIAN),
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

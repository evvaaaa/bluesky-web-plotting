import bluesky.plan_stubs as bps
import pytest
from bluesky.plans import count, grid_scan
from bluesky.run_engine import RunEngine
from ophyd_async import plan_stubs as oaps

from bluesky_web_plots.structures import unpack_structures
from bluesky_web_plots.structures.scalar import PlotAgainst, Scalar

from .mock_devices import Mca, SomeActuator, setup_sample_map_mock_logic


@pytest.fixture
def RE_and_mock_devices(
    zmq_proxy_run_engine,
) -> tuple[RunEngine, Mca, SomeActuator, SomeActuator]:
    mca = Mca(name="mca")
    motor1 = SomeActuator(name="motor1")
    motor2 = SomeActuator(name="motor2")

    def prepare():
        yield from bps.open_run()
        yield from oaps.ensure_connected(*[motor1, motor2, mca], mock=True)
        setup_sample_map_mock_logic(motor1, motor2, mca)
        yield from bps.close_run()

    zmq_proxy_run_engine(prepare())
    return zmq_proxy_run_engine, mca, motor1, motor2


def test_simple_count(RE_and_mock_devices, plot_subprocess):
    RE, mca, motor1, motor2 = RE_and_mock_devices
    RE(count([mca, motor1, motor2], num=10))


def test_grid_scan(RE_and_mock_devices, plot_subprocess):
    RE, mca, motor1, motor2 = RE_and_mock_devices
    plot_options = {
        "hints": unpack_structures(
            Scalar(name=motor1.readback.name, plot_against=PlotAgainst.TIME)
        )
    }

    RE(
        grid_scan(
            [mca],
            motor1,
            0,
            50,
            10,
            motor2,
            0,
            90,
            10,
            snake_axes=True,
            md=plot_options,
        )
    )

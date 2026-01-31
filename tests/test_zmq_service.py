import numpy as np
import bluesky.plan_stubs as bps
import pytest
from plotly import graph_objects as go
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
            Scalar(names=(motor1.readback.name,), plot_against=PlotAgainst.TIME)
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
    RE(
        grid_scan(
            [mca],
            motor1,
            10,
            20,
            10,
            motor2,
            10,
            20,
            10,
            snake_axes=True,
            md=plot_options,
        )
    )


def _make_arbitrary_figure() -> go.Figure:
    fig = go.Figure()

    def add_annotation(text: str, line: int):
        fig.add_annotation(
            text=text,
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(
                family="Pacifico, Comic Sans MS, cursive, sans-serif",
                size=32,
                color="rgba(50,50,50,0.4)",
            ),
            xref="paper",
            yref="paper",
            xshift=4,
            yshift=-4 - line * 64,
            opacity=0.7,
        )

        # Main annotation (on top, colored)
        fig.add_annotation(
            text=text,
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(
                family="Pacifico, Comic Sans MS, cursive, sans-serif",
                size=32,
                color="#e75480",
            ),
            yshift=-line * 64,
            xref="paper",
            yref="paper",
        )

    add_annotation("This could be anything you want!", line=0)
    add_annotation("It was made in the run engine", line=1)
    add_annotation("All plotly is serializable <3 <3 <3", line=2)

    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(255,240,245,1)",
        margin=dict(l=0, r=0, t=0, b=0),
        width=600,
        height=400,
    )

    t = np.linspace(0, 2 * np.pi, 200)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)

    x = (x - np.mean(x)) / (np.max(np.abs(x)) * 2) + 0.5
    y = (y - np.mean(y)) / (np.max(np.abs(y)) * 2) + 0.5

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            line=dict(color="#e75480", width=4),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    return fig


def test_arbitrary_run_start_plots(zmq_proxy_run_engine, plot_subprocess):
    def some_plan():
        yield from bps.open_run(
            md={
                "hints": unpack_structures(
                    static_figures={"whatever I like": _make_arbitrary_figure()}
                )
            }
        )
        yield from bps.close_run()

    zmq_proxy_run_engine(some_plan())

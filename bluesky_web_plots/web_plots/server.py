import itertools
import logging
import threading
from queue import Queue

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html
from flask import Flask

from bluesky_web_plots import __version__
from bluesky_web_plots.logger import logger


class PlotServer:
    def __init__(
        self, host: str = "0.0.0.0", port=8080, columns=2, local_window_mode=False
    ) -> None:
        self.HOST = host
        self.PORT = port
        self._columns = columns
        self.updated_plot_queue: Queue[tuple[str, go.Figure]] = Queue()
        self._plots: dict[str, go.Figure] = {}
        self._paused_figures: set[str] = set()
        self._hidden_figures: set[str] = set()
        self._lock = threading.Lock()

    def run(self) -> None:
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)
        server = Flask(__name__)
        self._app = Dash(
            title="Bluesky Web Plots",
            server=server,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            update_title=None,  # type: ignore
        )
        self._setup_layout()
        app_thread = threading.Thread(
            target=lambda: self._app.run(
                host=self.HOST,
                port=self.PORT,
                debug=False,
                use_reloader=False,
            ),
            daemon=True,
        )

        app_thread.start()

    def add_widget(self, name: str, figure: go.Figure):
        with self._lock:
            self._plots[name] = figure

    def _setup_layout(self):
        app = self._app

        def make_card(name, figure):
            return dbc.Card(
                [
                    dbc.CardHeader(
                        dbc.Row(
                            [dbc.Col(html.H5(name))],
                            justify="between",
                        ),
                    ),
                    dbc.Collapse(
                        dcc.Graph(id={"type": "plot", "index": name}, figure=figure),
                        id={"type": "collapse", "index": name},
                        is_open=True,
                    ),
                ],
                style={"margin": "10px"},
            )

        app.layout = html.Div(
            [
                html.Div(
                    [
                        html.H1("Bluesky Web Plots"),
                        html.Div(
                            f"https://github.com/evvaaaa/bluesky-web-plotting version {__version__}",
                            style={
                                "opacity": 0.5,
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "center",
                    },
                ),
                dcc.Interval(id="interval", interval=250, n_intervals=0),
                html.Div(id="plots-container"),
            ]
        )

        @app.callback(
            Output("plots-container", "children"),
            Input("interval", "n_intervals"),
            State("plots-container", "children"),
            prevent_initial_call=True,
        )
        def update_plots(n, children):
            logger.debug(f"Updated plots for the {n}th time.")
            with self._lock:
                while not self.updated_plot_queue.empty():
                    name, figure = self.updated_plot_queue.get()
                    self._plots[name] = figure

                columns = [[] for _ in range(self._columns)]
                columns_iter = itertools.cycle(columns)
                for name, fig in self._plots.items():
                    is_paused = name in self._paused_figures
                    display_fig = (
                        fig if not is_paused else fig
                    )  # Show last state if paused
                    next(columns_iter).append(make_card(name, display_fig))
                return dbc.Row(
                    [dbc.Col(column, width=12 // self._columns) for column in columns]
                )

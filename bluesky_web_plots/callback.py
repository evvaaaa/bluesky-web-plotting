import logging
import dash
from bluesky_web_plots.logger import logger
from typing import cast

from bluesky_web_plots import __version__
from event_model.documents import Document, EventDescriptor, RunStart, Event, DataKey
from dash import dcc, html
from dash.dependencies import Input, Output
from bluesky_web_plots.figures.base_figure import BaseFigure
import plotly.graph_objs as go
from .utils import deep_update
from flask import Flask
import threading
from queue import Queue
from bluesky_web_plots.figures.scalar import ScalarFigure


def hinted_fields(descriptor: EventDescriptor):
    # Figure out which columns to put in the table.
    obj_names = list(descriptor.get("object_keys", []))
    # We will see if these objects hint at whether
    # a subset of their data keys ('fields') are interesting. If they
    # did, we'll use those. If these didn't, we know that the RunEngine
    # *always* records their complete list of fields, so we can use
    # them all unselectively.
    columns = []
    for obj_name in obj_names:
        fields = descriptor.get("hints", {}).get(obj_name, {}).get("fields")
        fields = fields or descriptor.get("object_keys", {}).get(obj_name, [])
        columns.extend(fields)
    return columns


WATERMARK = html.Div(
    f"https://github.com/evvaaaa/bluesky-web-plotting version {__version__}",
    style={
        "position": "fixed",
        "bottom": "10px",
        "left": "0",
        "width": "100%",
        "textAlign": "center",
        "opacity": "0.8",
        "fontSize": "18px",
        "pointerEvents": "none",  # Allows clicks to pass through
        "zIndex": "9999",
    },
)


class WebPlotsCallback:
    def __init__(
        self, host: str = "0.0.0.0", port: int = 8095, update_period: float = 1.0
    ):
        self.document_queue: Queue[Document] = Queue()
        self.HOST = host
        self.PORT = port
        self.UPDATE_PERIOD = update_period
        self._lock = threading.Lock()
        self._figures: dict[str, BaseFigure] = {}
        self._update_event = threading.Event()
        self._structures: dict = {}

        server = Flask(__name__)

        # Dash self.app
        self.app = dash.Dash(__name__, server=server)

        self.app.layout = html.Div(
            [
                html.H1("Bluesky Web Plotting", style={"textAlign": "center"}),
                html.Div(id="graphs-container"),
                dcc.Interval(
                    id="interval-component",
                    interval=self.UPDATE_PERIOD * 1000,
                    n_intervals=0,
                ),
                WATERMARK,
            ]
        )

        @self.app.callback(
            Output("graphs-container", "children"),
            [Input("interval-component", "n_intervals")],
        )
        def update_graph(n_intervals):
            with self._lock:
                if not self._update_event.is_set():
                    raise dash.exceptions.PreventUpdate
                if not self._figures:
                    html_figures = [
                        dcc.Graph(
                            figure=go.Figure().update_layout(
                                title="Waiting for data..."
                            )
                        )
                    ]
                else:
                    html_figures = [
                        dcc.Graph(figure=figure.figure())
                        for figure in self._figures.values()
                    ]
                return html_figures

        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        self._plot_thread = threading.Thread(
            target=self.app.run,
            kwargs={"host": self.HOST, "port": self.PORT},
            daemon=True,
        )
        logger.info(f"Starting Dash server at http://{self.HOST}:{self.PORT}")
        self._plot_thread.start()

    def __call__(self, name: str, document: Document):
        if name == "start":
            self.run_start(cast(RunStart, document))
        if name == "descriptor":
            self.descriptor(cast(EventDescriptor, document))
        if name == "event":
            self.event(cast(Event, document))

        with self._lock:
            self._update_event.set()

    def run_start(self, run_start: RunStart):
        self._structures = deep_update(
            self._structures, run_start.get("hints", {}).get("WEB_PLOT_STRUCTURES", {})
        )

    def _new_figure_from_datakey(
        self, name: str, data_key: DataKey
    ) -> BaseFigure | None:
        if data_key["dtype"] == "number":
            return ScalarFigure(self._structures.get(name))

        logger.warning(
            f"No figure available for data key {name} with dtype {data_key['dtype']}"
        )

    def descriptor(self, descriptor: EventDescriptor):
        plotted_fields = hinted_fields(descriptor) + [
            field for field in "data_keys" if field in self._structures
        ]
        for name in plotted_fields:
            if name not in self._figures:
                new_figure = self._new_figure_from_datakey(
                    name, descriptor["data_keys"][name]
                )
                if not new_figure:
                    continue
                self._figures[name] = new_figure

            self._figures[name].descriptor(descriptor)
            self._figures[name].datakey(name, descriptor["data_keys"][name])

    def event(self, event: Event):
        with self._lock:
            for name in event["data"]:
                if name in self._figures:
                    self._figures[name].event(event)

from pprint import pprint
from datetime import datetime
from plotly import graph_objs as go
from event_model.documents import Event, RunStart, EventDescriptor, EventPage
from bluesky_web_plots.structures.scalar import PlotAgainst, Scalar
from .base_figure import BaseFigureCallback


class ArrayFigureCallback(BaseFigureCallback[None]):
    structure = None

    def __init__(self, name: str, structure: None = None):
        if structure:
            raise ValueError("ArrayFigureCallback does not require a structure.")
        self.name = name

        self.figure = go.Figure()
        self._scan_id = 0

    def run_start(self, document: RunStart):
        self._scan_id = document.get("scan_id", 0)

    def descriptor(self, document: EventDescriptor):
        data_key = document["data_keys"].get(self.name, {})
        pprint(data_key)

        # self.figure.add_trace(
        #     #graph_objs.Scatter(x=[], y=[], mode="lines+markers", name=self._scan_id)
        # )

    def event(self, document: Event):
        ...
        # if self.structure["plot_against"] == PlotAgainst.TIME:
        #     x = datetime.fromtimestamp(document["time"])
        # else:
        #     x = document["seq_num"]
        #
        # y = document["data"][self.structure["name"]]
        # trace = self.figure.data[-1]
        # trace.x += (x,)  # type: ignore
        # trace.y += (y,)  # type: ignore

    def event_page(self, document: EventPage):
        ...

        # if self.structure["plot_against"] == PlotAgainst.TIME:
        #     x = [datetime.fromtimestamp(time) for time in document["time"]]
        # else:
        #     x = document["seq_num"]
        #
        # y = document["data"][self.structure["name"]]
        # trace = self.figure.data[-1]
        # trace.x += tuple(x)  # type: ignore
        # trace.y += tuple(y)  # type: ignore

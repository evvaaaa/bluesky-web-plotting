from datetime import datetime
from plotly import graph_objs as go
from plotly.subplots import make_subplots
from event_model.documents import Event, RunStart, EventDescriptor, EventPage
from bluesky_web_plots.structures.scalar import PlotAgainst, Scalar
from .base_figure import BaseFigureCallback


class ScalarFigureCallback(BaseFigureCallback[Scalar]):
    structure: Scalar

    def __init__(self, name: str, structure: Scalar | None = None):
        if name and structure and name != structure["name"]:
            raise ValueError(
                f"Recieved different names from init argument {name} "
                f"and stucture {self.structure['name']}"
            )

        self.structure: Scalar = structure or Scalar(
            plot_against=PlotAgainst.SEQ_NUM, name=name
        )
        self.figure = make_subplots(shared_xaxes=True)
        self.figure.update_layout({"uirevision": "constant"})

    def run_start(self, document: RunStart):
        self._scan_id = document.get("scan_id", document["uid"][4:])

    def descriptor(self, document: EventDescriptor):
        data_key = document["data_keys"].get(self.structure["name"], {})

        self.figure.update_layout(
            dict(
                xaxis_title="Sequence Number"
                if self.structure["plot_against"] == PlotAgainst.SEQ_NUM
                else "Time",
                yaxis_title=data_key.get("units", "value"),
            )
        )

        self.figure.add_trace(
            go.Scatter(x=[], y=[], mode="lines+markers", name=f"plan {self._scan_id}")
        )

    def event(self, document: Event):
        if self.structure["plot_against"] == PlotAgainst.TIME:
            x = datetime.fromtimestamp(document["time"])
        else:
            x = document["seq_num"]

        y = document["data"][self.structure["name"]]
        trace = self.figure.data[-1]
        trace.x += (x,)  # type: ignore
        trace.y += (y,)  # type: ignore

    def event_page(self, document: EventPage):
        if self.structure["plot_against"] == PlotAgainst.TIME:
            x = [datetime.fromtimestamp(time) for time in document["time"]]
        else:
            x = document["seq_num"]

        y = document["data"][self.structure["name"]]
        trace = self.figure.data[-1]
        trace.x += tuple(x)  # type: ignore
        trace.y += tuple(y)  # type: ignore

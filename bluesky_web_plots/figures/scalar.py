from datetime import datetime
from plotly import graph_objs
from plotly.basedatatypes import BaseTraceType
from event_model.documents import DataKey, Event, RunStart, EventDescriptor
from bluesky_web_plots.structures.scalar import PlotAgainst, Scalar
from .base_figure import BaseFigure
from plotly import graph_objs


class ScalarFigure(BaseFigure[Scalar]):
    structure: Scalar

    def __init__(self, structure: Scalar | None = None):
        self.structure: Scalar = structure or Scalar(
            plot_against=PlotAgainst.SEQ_NUM, name=""
        )
        self._figure: graph_objs.Figure | None = None
        self.current_trace: int = 0
        self.scan_id = 0
        self.xs, self.xy = [], []

    def run_start(self, run_start: RunStart):
        self.scan_id = run_start.get("scan_id", 0)

    def descriptor(self, descriptor: EventDescriptor): ...

    def datakey(self, name: str, datakey: DataKey):
        self.structure["name"] = name

        if not self._figure:
            self._figure = graph_objs.Figure()
            self._figure.update_layout(
                title=f"Real-Time Plot for {self.structure['name']}",
                xaxis_title="Sequence Number"
                if self.structure["plot_against"] == PlotAgainst.SEQ_NUM
                else "Time (s)",
                yaxis_title=datakey.get("units", "value"),
            )

        self._figure.add_trace(
            graph_objs.Scatter(x=[], y=[], mode="lines+markers", name=self.scan_id)
        )

    def event(self, event: Event):
        if self.structure["plot_against"] == PlotAgainst.TIME:
            x = datetime.utcfromtimestamp(event["time"])
        else:
            x = event["seq_num"]

        y = event["data"][self.structure["name"]]
        trace = self._figure.data[-1]
        trace.x += (x,)
        trace.y += (y,)

from datetime import datetime
from plotly import graph_objs
from plotly.basedatatypes import BaseTraceType
from event_model.documents import DataKey, Event, RunStart
from bluesky_web_plots.structures.scalar import PlotAgainst, Scalar
from .base_figure import BaseFigure


class ScalarFigure(BaseFigure[Scalar]):
    def __init__(self, structure: Scalar | None = None, **kwargs):
        super().__init__(**kwargs)
        self.structure = structure
        self.current_trace: graph_objs.Scatter | None = None
        self.scan_id = 0
        self.xs, self.xy = [], []

    def run_start(self, run_start: RunStart):
        self.scan_id = run_start.get("scan_id", 0)

    def datakey(self, name: str, datakey: DataKey):
        if self.structure is None:
            self.structure = Scalar(name=name, plot_against=PlotAgainst.SEQ_NUM)

        self.update_layout(
            title=f"Real-Time Plot for {self.structure['name']}",
            xaxis_title="Sequence Number"
            if self.structure["plot_against"] == PlotAgainst.SEQ_NUM
            else "Time (s)",
            yaxis_title=datakey.get("units", "value"),
            template="plotly_dark",
        )

        self.current_trace = graph_objs.Scatter(
            x=[], y=[], mode="lines+markers", name=self.scan_id
        )
        self.add_trace(self.current_trace)

    def event(self, event: Event):
        if self.structure is None:
            return

        if self.structure["plot_against"] == PlotAgainst.TIME:
            x = datetime.utcfromtimestamp(event["time"])
        else:
            x = event["seq_num"]

        y = event["data"][self.structure["name"]]
        self.current_trace.y += (y,)
        self.current_trace.x += (x,)

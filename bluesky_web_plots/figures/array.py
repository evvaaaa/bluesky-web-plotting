from datetime import datetime
from plotly import graph_objs as go
from event_model.documents import Event, RunStart, EventDescriptor, EventPage
from bluesky_web_plots.structures.array import Array, View
from .base_figure import BaseFigureCallback


class ArrayFigureCallback(BaseFigureCallback[Array]):
    def __init__(self, name: str, structure: Array | None = None):
        if name and structure and name != structure["name"]:
            raise ValueError(
                f"Recieved different names from init argument {name} "
                f"and stucture {self.structure['name']}"
            )

        self.structure: Array = structure or Array(view=View.SLICE, name=name)

        self.figure = go.Figure()
        self.figure.update_layout({"uirevision": "constant"})
        self._scan_id = 0

    def run_start(self, document: RunStart):
        self._scan_id = document.get("scan_id", document["uid"][4:])

    def descriptor(self, document: EventDescriptor):
        data_key = document["data_keys"].get(self.structure["name"], {})
        shape = data_key["shape"]
        if len(shape) == 1 and self.structure["view"] == View.SLICE:
            self.figure.add_trace(go.Scatter(x=[], y=[], name=f"plan {self._scan_id}"))
        else:
            self.figure.add_trace(
                go.Surface(x=[], y=[], z=[], name=f"plan {self._scan_id}")
            )

    def event(self, document: Event):
        trace = self.figure.data[-1]
        received = document["data"][self.structure["name"]]
        if self.structure["view"] == View.SLICE:
            trace.x = tuple(range(len(received)))  # type: ignore
            trace.y = tuple(received)  # type: ignore
        else:
            trace.x += (datetime.fromtimestamp(document["time"]),)  # type: ignore
            for i, n in enumerate(received):
                trace.y += (i,)  # type: ignore
                trace.z += (n,)  # type: ignore

    def event_page(self, document: EventPage): ...

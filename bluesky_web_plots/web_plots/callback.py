from .server import PlotServer
from bluesky_web_plots.logger import logger
from typing import cast
from queue import Queue

from event_model.documents import (
    Document,
    EventDescriptor,
    RunStart,
    Event,
    DataKey,
    EventPage,
)
from bluesky_web_plots.figures.base_figure import BaseFigureCallback
from bluesky_web_plots.utils import deep_update, hinted_fields
from bluesky_web_plots.figures.scalar import ScalarFigureCallback
from bluesky_web_plots.figures.array import ArrayFigureCallback


class WebPlotCallback:
    def __init__(self, host: str = "0.0.0.0", port=8080, columns=2):
        self._server = PlotServer(host=host, port=port, columns=columns)

        self.document_queue: Queue[Document] = Queue()
        self._figures: dict[str, BaseFigureCallback] = {}
        self._structures: dict = {}

        logger.info(f"Starting gui at http://{host}:{port}")
        self._server.run()

    def __call__(self, name: str, document: Document):
        if name == "start":
            self.run_start(cast(RunStart, document))
        if name == "descriptor":
            self.descriptor(cast(EventDescriptor, document))
        if name == "event":
            self.event(cast(Event, document))

        self._server.updated_event.set()

    def run_start(self, run_start: RunStart):
        self._structures = deep_update(
            self._structures, run_start.get("hints", {}).get("WEB_PLOT_STRUCTURES", {})
        )

    def _new_figure_from_datakey(
        self, name: str, data_key: DataKey
    ) -> BaseFigureCallback | None:
        if data_key["dtype"] == "number":
            return ScalarFigureCallback(name, structure=self._structures.get(name))
        if data_key["dtype"] == "array":
            return ArrayFigureCallback(name, structure=self._structures.get(name))

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

    def event(self, event: Event):
        for name in event["data"]:
            if name in self._figures:
                self._figures[name].event(event)
            self._server.updated_plot_queue.put((name, self._figures[name].figure))

    def event_page(self, event_page: EventPage):
        for name in event_page["data"]:
            if name in self._figures:
                self._figures[name].event_page(event_page)
            self._server.updated_plot_queue.put((name, self._figures[name].figure))

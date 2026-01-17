import threading
from bluesky.callbacks.zmq import RemoteDispatcher
from .server import PlotServer
from bluesky_web_plots.logger import logger
from typing import cast

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


class PlotlyCallback:
    def __init__(
        self,
        zmq_host: str | None = None,
        zmq_port: int | None = None,
        plot_host: str = "0.0.0.0",
        plot_port=8080,
        columns=3,
    ):
        """A callback for plotting event document output through the web, with either simple,
        or complicated structures.

        Args:
            zmq_host (str | None):
                The ZMQ host to connect to for documents. If not provided then the callback can be ran directly
                as a RE.subscribe callback instead.
            zmq_port (str | None):
                The ZMQ port to connect to for documents. If not provided then the callback can be ran directly
                as a RE.subscribe callback instead.
            plot_host (str):
                The host that will be used for viewing the web interface.
            plot_port (str):
                The port that will be used for viewing the web interface.
            columns (int):
                The number of columns that the plots will be packed into in the web ui.
        """

        plot_host = plot_host.lstrip(
            "http://"
        )  # will fail if you try e.g "http://0.0.0.0"
        if zmq_host is not None:
            zmq_host = zmq_host.lstrip("tcp://")
        if zmq_port is None or zmq_host is None:
            self.ZMQ_URL = None
            logger.warning(
                "Creating a callback without a ZMQ stream... The plotter will slow down your run engine substantially for very large seq-num plans."
            )
        else:
            self.ZMQ_URL = f"{zmq_host}:{zmq_port}"

        self._server = PlotServer(
            as_a_service=self.ZMQ_URL is not None,
            host=plot_host,
            port=plot_port,
            columns=columns,
        )

        self._current_run_start: RunStart | None = None
        self._figures: dict[str, BaseFigureCallback] = {}
        self._structures: dict = {}

        logger.info(f"Starting gui at http://{plot_host}:{plot_port}")
        self.run()

    def _run(self):
        """Runs the callback as a service listening to ZMQ for event documents."""

        if self.ZMQ_URL is None:
            raise ValueError(
                "Cannot run as a service as the ZMQ host or port was not provided on init."
            )

        remote_dispatcher = RemoteDispatcher(self.ZMQ_URL)
        remote_dispatcher.subscribe(self)
        logger.info(f"Connected to {self.ZMQ_URL} Ready to Plot, Ctrl + C to Exit")
        try:
            remote_dispatcher.start()
        except KeyboardInterrupt:
            print("Exiting...")
            remote_dispatcher.stop()

    def run(self):
        threading.Thread(target=self._run, daemon=True).start()
        self._server.run()

    def __call__(self, name: str, document: Document):
        if name == "start":
            self.run_start(cast(RunStart, document))
        if name == "descriptor":
            self.descriptor(cast(EventDescriptor, document))
        if name == "event":
            self.event(cast(Event, document))

    def run_start(self, run_start: RunStart):
        self._structures = deep_update(
            self._structures, run_start.get("hints", {}).get("WEB_PLOT_STRUCTURES", {})
        )
        self._current_run_start = run_start

    def _new_figure_from_datakey(
        self, name: str, data_key: DataKey
    ) -> BaseFigureCallback | None:
        if data_key["dtype"] in ("number", "integer"):
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
                # If the service starts post run_start, but before descriptor
                # it'll work, but you'll get 0 as your data key. Not really an issue.
                if self._current_run_start:
                    new_figure.run_start(self._current_run_start)
                self._figures[name] = new_figure

        for figure in self._figures.values():
            figure.descriptor(descriptor)

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

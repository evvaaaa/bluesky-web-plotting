import multiprocessing
from queue import Queue
from typing import cast

from bluesky.callbacks.zmq import RemoteDispatcher
from event_model.documents import (
    DataKey,
    Document,
    Event,
    EventDescriptor,
    EventPage,
    RunStart,
)

from bluesky_web_plots.figures.array import ArrayFigureCallback
from bluesky_web_plots.figures.base_figure import BaseFigureCallback
from bluesky_web_plots.figures.scalar import ScalarFigureCallback
from bluesky_web_plots.logger import logger
from bluesky_web_plots.utils import deep_update, hinted_fields

from .server import PlotServer


class PlotlyCallback:
    def __init__(
        self,
        zmq_uri: str | None = None,
        plot_host: str = "0.0.0.0",
        plot_port=8080,
        columns=3,
        local_window_mode: bool = False,
    ):
        """A callback for plotting event document output through the web, with either simple,
        or complicated structures.

        If `zmq_uri` is not provided then it the window will open in local_window_mode mode as the
        callback is not running as a service.

        Args:
            zmq_uri (str | None):
                The ZMQ host to connect to for documents. If not provided then the callback
                can be ran directly as a RE.subscribe callback instead.
            plot_host (str):
                The host that will be used for viewing the web interface.
            plot_port (str):
                The port that will be used for viewing the web interface.
            columns (int):
                The number of columns that the plots will be packed into in the web ui.
            local_window_mode (bool):
                Spawn a local Qt5 editor.
        """

        self.PLOT_PORT = plot_port
        plot_host = plot_host.lstrip(
            "http://"
        )  # will fail if you try e.g "http://0.0.0.0"
        if zmq_uri is None:
            logger.warning(
                "Creating a callback without a ZMQ stream... The plotter will slow down your run engine substantially for very large seq-num plans."
            )
        else:
            # Ensure no "tcp://" prefix, this is added in the RemoteDispatcher
            zmq_uri = zmq_uri.lstrip("tcp://")

        self.ZMQ_URI = zmq_uri

        self._server = PlotServer(
            host=plot_host,
            port=plot_port,
            columns=columns,
        )

        self._current_run_start: RunStart | None = None
        self.document_queue: Queue[Document] = Queue()
        self._figures: dict[str, BaseFigureCallback] = {}
        self._structures: dict = {}

        # local_window_mode is for when the process is for creating a local window
        # a new one for each run whenever it's closed, mimicking best effort callback
        # and not relying on the browser process which may be slow from an abundance
        # of tabs, or a bad browser. The plots will still be viewable
        # from a normal browser.
        self._local_window_mode = local_window_mode
        self._local_window_process = multiprocessing.Process(
            target=self._create_local_window
        )

        logger.info(f"Starting gui at http://{plot_host}:{plot_port}")
        self._server.run()

    def _create_local_window(self):
        from PyQt5.QtCore import QUrl
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtWidgets import QApplication

        app = QApplication([])
        view = QWebEngineView()
        view.load(QUrl(f"http://localhost:{self.PLOT_PORT}"))
        view.show()
        app.exec_()

    def run(self):
        """Runs the callback as a service listening to ZMQ for event documents."""

        if self.ZMQ_URI is None:
            raise ValueError(
                "Cannot run as a service as the ZMQ host or port was not provided on init."
            )

        remote_dispatcher = RemoteDispatcher(self.ZMQ_URI)
        remote_dispatcher.subscribe(self)
        logger.info(f"Connected to {self.ZMQ_URI} Ready to Plot, Ctrl + C to Exit")
        try:
            remote_dispatcher.start()
        except KeyboardInterrupt:
            print("Exiting...")
            remote_dispatcher.stop()

        if self._local_window_mode:
            self._local_window_process.start()

    def __call__(self, name: str, document: Document):
        if self._local_window_mode and not self._local_window_process.is_alive():
            self._local_window_process.start()

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

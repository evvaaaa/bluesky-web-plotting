from pathlib import Path
import time
import plotly.graph_objects as go
import threading
from queue import Queue
from nicegui import app, ui
from bluesky_web_plots.logger import logger

from bluesky_web_plots import __version__


class PlotServer:
    def __init__(
        self, as_a_service: bool = True, host: str = "0.0.0.0", port=8080, columns=2
    ) -> None:
        self._as_a_service = as_a_service
        self.HOST = host
        self.PORT = port
        self._columns = columns
        self.updated_plot_queue: Queue[tuple[str, go.Figure]] = Queue()
        self._plots: dict[str, ui.plotly] = {}
        self._paused_figures: set[str] = set()

        self._non_plot_widgets = {}

    def run(self):
        if self._as_a_service:
            self.run_as_a_service()
        else:
            self.run_on_background_thread()

    def run_as_a_service(self):
        """If being ran as a service then this will block the thread."""

        ui.run(
            self.root,
            reload=False,
            host=self.HOST,
            port=self.PORT,
            dark=True,
            favicon=Path(__file__).parent / "bluesky-logo-dark.svg",
        )

    def run_on_background_thread(self):
        """If being ran as a callback then the plots will be displayed on a background thread."""

        started = threading.Event()
        app.on_startup(started.set)
        thread = threading.Thread(
            target=lambda: ui.run(
                self.root,
                reload=False,
                host=self.HOST,
                port=self.PORT,
                dark=True,
                favicon=Path(__file__).parent / "bluesky-logo-dark.svg",
            ),
            daemon=True,
        )
        thread.start()
        if not started.wait(timeout=5):
            raise RuntimeError("NiceGUI did not start in 5 seconds.")

    def add_widget(self, ui, name: str, figure: go.Figure):
        logger.info(f"Adding widget for plot: {name} {figure.data[0]['type']}")
        if name not in self._plots:
            non_plot_widgets = {}
            self._non_plot_widgets[name] = non_plot_widgets
            with self.div:
                self._non_plot_widgets["card"] = ui.card(align_items="center")
                with self._non_plot_widgets["card"]:
                    with ui.row():
                        ui.label(name)
                        non_plot_widgets["show_hide"] = ui.button(
                            text="HIDE", on_click=None
                        )
                        non_plot_widgets["pause_play"] = ui.button(
                            text="PAUSE",
                            on_click=None,
                        )
                    self._plots[name] = ui.plotly(figure)

            def pause_play_click(name):
                button = self._non_plot_widgets[name]["pause_play"]
                to_play = button.text == "PLAY"
                if to_play:
                    self._paused_figures.remove(name)
                    button.set_text("PAUSE")
                    self._plots[name].update()
                else:
                    self._paused_figures.add(name)
                    button.set_text("PLAY")

            non_plot_widgets["pause_play"].on_click(
                lambda name=name: pause_play_click(name)
            )

            def show_hide_click(name):
                button = self._non_plot_widgets[name]["show_hide"]
                to_show = button.text == "SHOW"
                self._plots[name].set_visibility(to_show)
                button.set_text("SHOW" if not to_show else "HIDE")

            non_plot_widgets["show_hide"].on_click(
                lambda name=name: show_hide_click(name)
            )

    @ui.refreshable
    def listen(self):
        while not self.updated_plot_queue.empty():
            name, figure = self.updated_plot_queue.get()
            if name not in self._plots:
                self.add_widget(ui, name, figure)
            if name not in self._paused_figures:
                self._plots[name].update()

    @ui.page("/plots")
    def root(self) -> None:
        ui.page_title("Bluesky Web Plots")
        ui.html(
            "<h1>Bluesky Web Plots</h1>",
            sanitize=False,
        )
        ui.label(
            f"https://github.com/evvaaaa/bluesky-web-plotting version {__version__}"
        ).classes("opacity-50")
        self.div = ui.element("div").classes(f"columns-{self._columns} w-full gap-2")

        ui.timer(1, self.listen)

import argparse

from bluesky_web_plots.web_plots.callback import WebPlotCallback


def main():
    parser = argparse.ArgumentParser(description="Bluesky Web Plots")
    parser.add_argument(
        "zmq_uri",
        type=str,
        help="ZMQ host to connect to for documents. Example 0.0.0.0:5578",
    )
    parser.add_argument(
        "--plot-host",
        type=str,
        default="0.0.0.0",
        help="Host for viewing the web interface.",
    )
    parser.add_argument(
        "--plot-port",
        type=int,
        default=8080,
        help="Port for viewing the web interface.",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=2,
        help="Number of columns for plots in the web UI.",
    )
    parser.add_argument(
        "--local-window-mode",
        action="store_true",
        help="Produce a local window for plots.",
    )
    args = parser.parse_args()

    WebPlotCallback(
        zmq_uri=args.zmq_uri,
        plot_host=args.plot_host,
        plot_port=args.plot_port,
        columns=args.columns,
        local_window_mode=bool(args.local_window_mode),
    ).run()


if __name__ == "__main__":
    main()

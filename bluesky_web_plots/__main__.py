import argparse

from bluesky_web_plots.web_plots.callback import PlotlyCallback


def main():
    parser = argparse.ArgumentParser(description="Bluesky Web Plots")
    parser.add_argument(
        "zmq_host", type=str, help="ZMQ host to connect to for documents."
    )
    parser.add_argument(
        "zmq_port", type=int, help="ZMQ port to connect to for documents."
    )
    parser.add_argument(
        "--plot-host",
        type=str,
        default="0.0.0.0",
        help="Host for viewing the web interface. (default 0.0.0.0)",
    )
    parser.add_argument(
        "--plot-port",
        type=int,
        default=8080,
        help="Port for viewing the web interface. (default 8080)",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=2,
        help="Number of columns for plots in the web UI. (default 2)",
    )
    args = parser.parse_args()

    PlotlyCallback(
        zmq_host=args.zmq_host,
        zmq_port=args.zmq_port,
        plot_host=args.plot_host,
        plot_port=args.plot_port,
        columns=args.columns,
    ).run()


if __name__ in ("__mp_main__", "__main__"):
    main()

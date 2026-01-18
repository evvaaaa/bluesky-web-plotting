import os
import signal
import time
from multiprocessing import Process

import pytest
import zmq
from bluesky.callbacks.zmq import Proxy, Publisher
from bluesky.run_engine import RunEngine

from bluesky_web_plots import PlotlyCallback

EXAMPLE_MODE = os.getenv("BLUESKY_WEB_PLOTS_EXAMPLE_MODE", "0") == "1"


@pytest.fixture(scope="session")
def zmq_proxy_subprocess():
    def start_proxy_and_dispatcher():
        proxy = Proxy(in_port=5577, out_port=5578)
        proxy.start()

    zmq_proxy = Process(target=start_proxy_and_dispatcher, daemon=True)
    try:
        zmq_proxy.start()
        time.sleep(1)
        if not zmq_proxy.is_alive():
            raise RuntimeError("ZMQ proxy subprocess failed to start.")
        yield zmq_proxy
    finally:
        if not zmq_proxy.is_alive():
            raise RuntimeError("ZMQ proxy died during test.")
        zmq_proxy.terminate()
        zmq_proxy.join(timeout=1)
        zmq_proxy.close()


@pytest.fixture(scope="function")
def zmq_proxy_run_engine(zmq_proxy_subprocess):
    RE = RunEngine()
    publisher = Publisher(address="127.0.0.1:5577")
    RE.subscribe(publisher)
    try:
        yield RE
    finally:
        publisher.close()


@pytest.fixture(scope="function")
def threaded_callback_run_engine():
    RE = RunEngine()
    RE.subscribe(PlotlyCallback())
    return RE


@pytest.fixture(scope="function")
def plot_subprocess():
    def start_plotly_callback():
        callback = PlotlyCallback(
            zmq_uri="127.0.0.1:5578", local_window_mode=EXAMPLE_MODE
        )

        def wait_for_local_window_close(signum, frame):
            while callback._local_window_process.is_alive():
                # For use in example mode, wait for the user to close
                # the local window.
                pass
            exit(0)

        if EXAMPLE_MODE:
            signal.signal(signal.SIGINT, wait_for_local_window_close)

        callback.run()

    zmq_callback = Process(target=start_plotly_callback)
    try:
        zmq_callback.start()
        time.sleep(1)
        if not zmq_callback.is_alive():
            raise RuntimeError("ZMQ Plot Callback subprocess failed to start.")
        yield zmq_callback
    finally:

        def wait_for_zmq_drain(out_address, timeout=2.0):
            ctx = zmq.Context()
            socket = ctx.socket(zmq.SUB)
            socket.connect(out_address)
            socket.setsockopt(zmq.SUBSCRIBE, b"")
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            last_msg_time = time.time()
            while True:
                socks = dict(poller.poll(timeout=100))
                if socket in socks and socks[socket] == zmq.POLLIN:
                    _ = socket.recv()
                    last_msg_time = time.time()
                elif time.time() - last_msg_time > timeout:
                    break
            socket.close()
            ctx.term()

        wait_for_zmq_drain("tcp://127.0.0.1:5578")
        if not zmq_callback.is_alive():
            raise RuntimeError("ZMQ Plot callback died during test.")

        if EXAMPLE_MODE:
            join_time = None
            os.kill(zmq_callback.pid, signal.SIGINT)  # type: ignore
        else:
            join_time = 1
            zmq_callback.terminate()
        zmq_callback.join(timeout=join_time)
        zmq_callback.close()

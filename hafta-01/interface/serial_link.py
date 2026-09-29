"""Serial port reader running in its own thread.

The GUI thread never blocks on the port: received lines are pushed into a
queue.Queue and the GUI drains it with Tk's after() timer.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Optional

import serial
import serial.tools.list_ports


def list_ports() -> list:
    """Returns (device, description) pairs, ST-LINK ports first."""
    ports = [(p.device, p.description) for p in serial.tools.list_ports.comports()]
    ports.sort(key=lambda p: (0 if "STLink" in p[1] or "STM" in p[1] else 1, p[0]))
    return ports


class SerialLink:
    ERROR = "__serial_error__"

    def __init__(self, rx_queue: "queue.Queue") -> None:
        self._q = rx_queue
        self._ser: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    @property
    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def open(self, port: str, baud: int = 115200) -> None:
        self.close()
        self._ser = serial.Serial(port, baud, timeout=0.05)
        self._ser.reset_input_buffer()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="serial-rx", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._ser is not None:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def send_line(self, text: str) -> None:
        if not self.is_open:
            raise RuntimeError("port kapali")
        self._ser.write((text + "\n").encode("ascii"))

    def _run(self) -> None:
        buf = b""
        while not self._stop.is_set():
            try:
                data = self._ser.read(self._ser.in_waiting or 1)
            except (serial.SerialException, OSError) as exc:
                self._q.put((self.ERROR, str(exc), time.monotonic()))
                return
            if not data:
                continue
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                text = line.decode("ascii", errors="replace").rstrip("\r")
                self._q.put((text, None, time.monotonic()))

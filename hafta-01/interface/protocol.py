"""Line protocol of the week-1 firmware (see hafta-01/CLAUDE.md).

Every message from the board is one text line ending with '\n'.
TEL and BTN lines are exactly 64 bytes (space padded); DUMP/CNT/ACK/ERR
lines have variable length. This module only parses text and never
touches the serial port, so it can be reused and tested on its own.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CSV_HEADER = "scenario,event_id,t0_us,t1_us,t2_us,t3_us,t4_us,status"
STAGE_NAMES = ("t1-t0", "t2-t1", "t3-t2", "t4-t3")
STAGE_LABELS = (
    "t1-t0  ISR -> ButtonTask",
    "t2-t1  yanit hazirlama",
    "t3-t2  TX kuyrugu + UART baslatma",
    "t4-t3  hat suresi + TC",
)
MSG_LEN = 64
U32 = 0xFFFFFFFF

_EVENT_ROW = re.compile(r"^S\d+,\d+,")


@dataclass
class Tel:
    seq: int
    scenario: str
    tick_ms: int
    length: int


@dataclass
class Btn:
    event_id: int
    scenario: str
    length: int


@dataclass
class Ack:
    text: str


@dataclass
class Err:
    text: str


@dataclass
class DumpHeader:
    raw: str


@dataclass
class EventRow:
    raw: str
    scenario: str
    event_id: int
    t: list  # five Optional[int] timestamps in us, None = not taken
    status: str

    def stage_us(self, i: int) -> Optional[int]:
        a, b = self.t[i], self.t[i + 1]
        if a is None or b is None:
            return None
        return (b - a) & U32  # same mod 2^32 rule as the firmware

    @property
    def r_us(self) -> Optional[int]:
        if self.t[0] is None or self.t[4] is None:
            return None
        return (self.t[4] - self.t[0]) & U32

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass
class Counters:
    raw: str
    values: dict


@dataclass
class DumpEnd:
    pass


@dataclass
class Unknown:
    raw: str


def _opt_int(text: str) -> Optional[int]:
    text = text.strip()
    return int(text) if text else None


def parse_event_row(line: str) -> Optional[EventRow]:
    parts = line.strip().split(",")
    if len(parts) != 8:
        return None
    try:
        return EventRow(
            raw=line.strip(),
            scenario=parts[0],
            event_id=int(parts[1]),
            t=[_opt_int(p) for p in parts[2:7]],
            status=parts[7].strip(),
        )
    except ValueError:
        return None


def parse_line(line: str):
    """Turns one received line into a message object."""
    length = len(line) + 1  # '\n' was stripped by the reader
    s = line.strip()
    try:
        if s.startswith("TEL,"):
            _, seq, scn, tick = s.split(",")
            return Tel(int(seq), scn, int(tick), length)
        if s.startswith("BTN,"):
            _, eid, scn, _state = s.split(",")
            return Btn(int(eid), scn, length)
    except ValueError:
        return Unknown(s)
    if s.startswith("ACK,"):
        return Ack(s[4:])
    if s.startswith("ERR,"):
        return Err(s[4:])
    if s == CSV_HEADER:
        return DumpHeader(s)
    if s.startswith("CNT,"):
        values = {}
        for item in s[4:].split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                values[k] = v
        return Counters(s, values)
    if s == "END":
        return DumpEnd()
    if _EVENT_ROW.match(s):
        row = parse_event_row(s)
        if row is not None:
            return row
    return Unknown(s)


@dataclass
class DumpResult:
    header: str
    rows: list = field(default_factory=list)
    counters: Optional[Counters] = None

    @property
    def scenario(self) -> Optional[str]:
        return self.rows[0].scenario if self.rows else None


class DumpCollector:
    """Collects header, event rows and the CNT line until END arrives."""

    def __init__(self) -> None:
        self._cur: Optional[DumpResult] = None

    @property
    def active(self) -> bool:
        return self._cur is not None

    def feed(self, msg) -> Optional[DumpResult]:
        if isinstance(msg, DumpHeader):
            self._cur = DumpResult(header=msg.raw)
            return None
        if self._cur is None:
            return None
        if isinstance(msg, EventRow):
            self._cur.rows.append(msg)
        elif isinstance(msg, Counters):
            self._cur.counters = msg
        elif isinstance(msg, DumpEnd):
            done, self._cur = self._cur, None
            return done
        return None


def load_event_csv(path: Path) -> list:
    """Reads a measurements/Sx.csv file written by the interface."""
    rows = []
    with open(path, newline="", encoding="ascii") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None or ",".join(header) != CSV_HEADER:
            raise ValueError(f"{path.name}: unexpected header")
        for rec in reader:
            row = parse_event_row(",".join(rec))
            if row is not None:
                rows.append(row)
    return rows

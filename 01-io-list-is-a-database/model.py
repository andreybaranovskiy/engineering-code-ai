"""Typed records for I&C engineering data: instrument index, IO list, cable schedule.

Standard library only (Python 3.10+). Every value is parsed and typed once, at the
boundary, so the rules never deal with strings that might be numbers.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


def _num(value: str) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def _text(value: str) -> str:
    return (value or "").strip()


@dataclass(frozen=True)
class Instrument:
    """One row of the instrument index: the master record for a tag."""
    tag: str
    service: str
    signal: str          # AI, AO, DI, DO
    lrv: float | None    # lower range value
    urv: float | None    # upper range value
    units: str
    system: str          # DCS or SIS
    loop_class: str      # BPCS or SIF
    is_barrier: bool     # intrinsically safe field device
    alarm_ll: float | None
    alarm_l: float | None
    alarm_h: float | None
    alarm_hh: float | None


@dataclass(frozen=True)
class IOPoint:
    """One row of the IO list: where a signal lands in the control system."""
    tag: str
    system: str
    cabinet: str
    card: str
    card_type: str       # AI, AO, DI, DO
    card_is: bool        # card or barrier supports IS loops
    channel: int
    lrv: float | None
    urv: float | None
    units: str


@dataclass(frozen=True)
class Cable:
    """One row of the cable schedule."""
    cable: str
    tag: str
    pairs: int
    pairs_used: int
    from_: str
    to: str
    length_m: float | None


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_index(path: Path) -> list[Instrument]:
    return [
        Instrument(
            tag=_text(r["tag"]), service=_text(r["service"]), signal=_text(r["signal"]),
            lrv=_num(r["lrv"]), urv=_num(r["urv"]), units=_text(r["units"]),
            system=_text(r["system"]), loop_class=_text(r["loop_class"]),
            is_barrier=_text(r["is"]).upper() == "Y",
            alarm_ll=_num(r["ll"]), alarm_l=_num(r["l"]),
            alarm_h=_num(r["h"]), alarm_hh=_num(r["hh"]),
        )
        for r in _rows(path)
    ]


def load_io(path: Path) -> list[IOPoint]:
    return [
        IOPoint(
            tag=_text(r["tag"]), system=_text(r["system"]), cabinet=_text(r["cabinet"]),
            card=_text(r["card"]), card_type=_text(r["card_type"]),
            card_is=_text(r["card_is"]).upper() == "Y", channel=int(r["channel"]),
            lrv=_num(r["lrv"]), urv=_num(r["urv"]), units=_text(r["units"]),
        )
        for r in _rows(path)
    ]


def load_cables(path: Path) -> list[Cable]:
    return [
        Cable(
            cable=_text(r["cable"]), tag=_text(r["tag"]), pairs=int(r["pairs"]),
            pairs_used=int(r["pairs_used"]), from_=_text(r["from"]), to=_text(r["to"]),
            length_m=_num(r["length_m"]),
        )
        for r in _rows(path)
    ]


@dataclass(frozen=True)
class Project:
    index: list[Instrument]
    io: list[IOPoint]
    cables: list[Cable]
    channels_per_card: int = 16

    @classmethod
    def load(cls, folder: Path) -> "Project":
        return cls(
            index=load_index(folder / "instrument_index.csv"),
            io=load_io(folder / "io_list.csv"),
            cables=load_cables(folder / "cable_schedule.csv"),
        )

"""Typed records for I&C engineering data: instrument index, IO list, cable schedule.

Every value is parsed and typed once, at the boundary. A bad value fails with the file, row and column.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

INDEX_COLUMNS = ["tag", "service", "signal", "lrv", "urv", "units", "system", "loop_class", "is", "ll", "l", "h", "hh"]
IO_COLUMNS = ["tag", "system", "cabinet", "card", "card_type", "card_is", "channel", "lrv", "urv", "units"]
CABLE_COLUMNS = ["cable", "tag", "pairs", "pairs_used", "from", "to", "length_m"]


class DataError(ValueError):
    """A register could not be read: missing file, missing column or a value of the wrong type."""


@dataclass(frozen=True)
class Instrument:
    tag: str
    service: str
    signal: str          # AI, AO, DI, DO
    lrv: float | None
    urv: float | None
    units: str
    system: str          # e.g. DCS or SIS
    loop_class: str      # BPCS or SIF
    is_barrier: bool     # intrinsically safe field device
    alarm_ll: float | None
    alarm_l: float | None
    alarm_h: float | None
    alarm_hh: float | None


@dataclass(frozen=True)
class IOPoint:
    tag: str
    system: str
    cabinet: str
    card: str
    card_type: str
    card_is: bool
    channel: int
    lrv: float | None
    urv: float | None
    units: str


@dataclass(frozen=True)
class Cable:
    cable: str
    tag: str
    pairs: int
    pairs_used: int
    from_: str
    to: str
    length_m: float | None


@dataclass(frozen=True)
class Config:
    tag_pattern: str = r"^\d{3}-[A-Z]{2,4}-\d{3,4}[A-Z]?$"
    spare_min: float = 0.20
    channels_per_card: int = 16
    safety_system: str = "SIS"


@dataclass(frozen=True)
class Project:
    index: list[Instrument]
    io: list[IOPoint]
    cables: list[Cable]
    config: Config = field(default_factory=Config)

    @classmethod
    def load(cls, index: Path, io: Path, cables: Path, config: Config | None = None) -> "Project":
        return cls(load_index(index), load_io(io), load_cables(cables), config or Config())

    @classmethod
    def load_folder(cls, folder: Path, config: Config | None = None) -> "Project":
        folder = Path(folder)
        return cls.load(folder / "instrument_index.csv", folder / "io_list.csv", folder / "cable_schedule.csv", config)


class _Row:
    """Typed access to one CSV row, with errors that say where the problem is."""

    def __init__(self, path: Path, line: int, data: dict[str, str]):
        self.path, self.line, self.data = path, line, data

    def _where(self, col):
        return f"{self.path.name} line {self.line}, column '{col}'"

    def text(self, col):
        return (self.data.get(col) or "").strip()

    def num(self, col):
        v = self.text(col).replace(",", "")
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            raise DataError(f"{self._where(col)}: '{self.text(col)}' is not a number") from None

    def int_(self, col):
        v = self.num(col)
        if v is None or v != int(v):
            raise DataError(f"{self._where(col)}: '{self.text(col)}' is not a whole number")
        return int(v)

    def flag(self, col):
        return self.text(col).upper() in ("Y", "YES", "TRUE", "1")


def _rows(path: Path, required: list[str]):
    path = Path(path)
    if not path.exists():
        raise DataError(f"file not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = [h.strip().lower() for h in (reader.fieldnames or [])]
        missing = [c for c in required if c not in header]
        if missing:
            raise DataError(f"{path.name}: missing column(s) {', '.join(missing)}; expected {', '.join(required)}")
        reader.fieldnames = header
        for n, r in enumerate(reader, start=2):
            if any((v or "").strip() for v in r.values()):
                yield _Row(path, n, r)


def load_index(path: Path) -> list[Instrument]:
    return [Instrument(r.text("tag"), r.text("service"), r.text("signal").upper(), r.num("lrv"), r.num("urv"),
                       r.text("units"), r.text("system"), r.text("loop_class").upper(), r.flag("is"),
                       r.num("ll"), r.num("l"), r.num("h"), r.num("hh"))
            for r in _rows(path, INDEX_COLUMNS)]


def load_io(path: Path) -> list[IOPoint]:
    return [IOPoint(r.text("tag"), r.text("system"), r.text("cabinet"), r.text("card"), r.text("card_type").upper(),
                    r.flag("card_is"), r.int_("channel"), r.num("lrv"), r.num("urv"), r.text("units"))
            for r in _rows(path, IO_COLUMNS)]


def load_cables(path: Path) -> list[Cable]:
    return [Cable(r.text("cable"), r.text("tag"), r.int_("pairs"), r.int_("pairs_used"), r.text("from"),
                  r.text("to"), r.num("length_m"))
            for r in _rows(path, CABLE_COLUMNS)]

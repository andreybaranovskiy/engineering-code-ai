"""Validation rules. Each rule: Project -> list[Finding]. Rules only read; they never fix data."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable

from .model import Project

ERROR, WARNING = "ERROR", "WARNING"


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    tag: str
    message: str


def r01_duplicate_tags(p: Project) -> list[Finding]:
    """Duplicate tags in the instrument index."""
    counts = Counter(i.tag for i in p.index)
    return [Finding("R01", ERROR, t, f"tag appears {n} times in the instrument index") for t, n in counts.items() if n > 1]


def r02_tag_format(p: Project) -> list[Finding]:
    """Tag does not follow the configured naming convention."""
    rx = re.compile(p.config.tag_pattern)
    return [Finding("R02", WARNING, i.tag, f"tag does not match the convention {p.config.tag_pattern}")
            for i in p.index if not rx.match(i.tag)]


def r03_orphan_io(p: Project) -> list[Finding]:
    """IO point with no instrument in the index."""
    known = {i.tag for i in p.index}
    return [Finding("R03", ERROR, io.tag, "IO point has no instrument in the index") for io in p.io if io.tag not in known]


def r04_unallocated_instrument(p: Project) -> list[Finding]:
    """Instrument with no IO allocation."""
    allocated = {io.tag for io in p.io}
    return [Finding("R04", ERROR, i.tag, "instrument has no IO allocation") for i in p.index if i.tag not in allocated]


def r05_range_mismatch(p: Project) -> list[Finding]:
    """Analog range differs between index and IO list."""
    by_tag = {i.tag: i for i in p.index}
    return [Finding("R05", ERROR, io.tag, f"range {io.lrv:g} to {io.urv:g} in IO list, {by_tag[io.tag].lrv:g} to {by_tag[io.tag].urv:g} in index")
            for io in p.io if io.tag in by_tag and by_tag[io.tag].signal in ("AI", "AO")
            and None not in (io.lrv, io.urv, by_tag[io.tag].lrv, by_tag[io.tag].urv)
            and (by_tag[io.tag].lrv, by_tag[io.tag].urv) != (io.lrv, io.urv)]


def r06_units_mismatch(p: Project) -> list[Finding]:
    """Engineering units differ between index and IO list."""
    by_tag = {i.tag: i for i in p.index}
    return [Finding("R06", ERROR, io.tag, f"units '{io.units}' in IO list, '{by_tag[io.tag].units}' in index")
            for io in p.io if io.tag in by_tag and by_tag[io.tag].signal in ("AI", "AO")
            and io.units.lower() != by_tag[io.tag].units.lower()]


def _alarms(i):
    return [("LL", i.alarm_ll), ("L", i.alarm_l), ("H", i.alarm_h), ("HH", i.alarm_hh)]


def r07_alarm_outside_range(p: Project) -> list[Finding]:
    """Alarm set point outside the instrument range."""
    return [Finding("R07", ERROR, i.tag, f"{n} alarm {v:g} {i.units} outside range {i.lrv:g} to {i.urv:g}")
            for i in p.index if i.lrv is not None and i.urv is not None
            for n, v in _alarms(i) if v is not None and not (i.lrv <= v <= i.urv)]


def r08_alarm_order(p: Project) -> list[Finding]:
    """Alarms not in the order LL < L < H < HH."""
    out = []
    for i in p.index:
        vals = [(n, v) for n, v in _alarms(i) if v is not None]
        out += [Finding("R08", ERROR, i.tag, f"{n1} ({v1:g}) is not below {n2} ({v2:g})")
                for (n1, v1), (n2, v2) in zip(vals, vals[1:]) if v1 >= v2]
    return out


def r09_signal_vs_card(p: Project) -> list[Finding]:
    """Signal type does not match the IO card type."""
    by_tag = {i.tag: i for i in p.index}
    return [Finding("R09", ERROR, io.tag, f"{by_tag[io.tag].signal} signal on a {io.card_type} card {io.card}")
            for io in p.io if io.tag in by_tag and by_tag[io.tag].signal != io.card_type]


def r10_double_allocated_channel(p: Project) -> list[Finding]:
    """Same card channel allocated to more than one tag."""
    seen = defaultdict(list)
    for io in p.io:
        seen[(io.system, io.cabinet, io.card, io.channel)].append(io.tag)
    return [Finding("R10", ERROR, ", ".join(t), f"channel {k[3]} of {k[1]}/{k[2]} used by {len(t)} tags")
            for k, t in seen.items() if len(t) > 1]


def r11_spare_capacity(p: Project) -> list[Finding]:
    """IO card spare capacity below the configured minimum."""
    used = Counter((io.system, io.cabinet, io.card) for io in p.io)
    n_ch, smin = p.config.channels_per_card, p.config.spare_min
    return [Finding("R11", WARNING, card, f"{cab}/{card}: {n}/{n_ch} channels used, {1 - n / n_ch:.0%} spare (minimum {smin:.0%})")
            for (sysname, cab, card), n in used.items() if 1 - n / n_ch < smin]


def r12_sif_on_bpcs(p: Project) -> list[Finding]:
    """Safety instrumented function not on the safety system."""
    s = p.config.safety_system
    return [Finding("R12", ERROR, i.tag, f"SIF loop assigned to {i.system}, expected {s}")
            for i in p.index if i.loop_class == "SIF" and i.system != s]


def r13_system_mismatch(p: Project) -> list[Finding]:
    """Control system differs between index and IO list."""
    by_tag = {i.tag: i for i in p.index}
    return [Finding("R13", ERROR, io.tag, f"index says {by_tag[io.tag].system}, IO list says {io.system}")
            for io in p.io if io.tag in by_tag and by_tag[io.tag].system != io.system]


def r14_is_device_on_non_is_card(p: Project) -> list[Finding]:
    """Intrinsically safe field device on a non-IS card."""
    by_tag = {i.tag: i for i in p.index}
    return [Finding("R14", ERROR, io.tag, f"IS field device on non-IS card {io.card}")
            for io in p.io if io.tag in by_tag and by_tag[io.tag].is_barrier and not io.card_is]


def r15_cable_checks(p: Project) -> list[Finding]:
    """Cable to an unknown tag, too many pairs used, or allocated IO with no cable."""
    known, cabled = {i.tag for i in p.index}, {c.tag for c in p.cables}
    out = [Finding("R15", ERROR, c.tag, f"cable {c.cable} refers to unknown tag") for c in p.cables if c.tag not in known]
    out += [Finding("R15", ERROR, c.tag, f"cable {c.cable}: {c.pairs_used} pairs used, only {c.pairs} available")
            for c in p.cables if c.pairs_used > c.pairs]
    out += [Finding("R15", WARNING, io.tag, "allocated IO point has no field cable")
            for io in p.io if io.tag in known and io.tag not in cabled]
    return out


RULES: list[Callable[[Project], list[Finding]]] = [
    r01_duplicate_tags, r02_tag_format, r03_orphan_io, r04_unallocated_instrument, r05_range_mismatch,
    r06_units_mismatch, r07_alarm_outside_range, r08_alarm_order, r09_signal_vs_card, r10_double_allocated_channel,
    r11_spare_capacity, r12_sif_on_bpcs, r13_system_mismatch, r14_is_device_on_non_is_card, r15_cable_checks,
]


def validate(p: Project, skip: set[str] | None = None) -> list[Finding]:
    skip = {s.upper() for s in (skip or set())}
    findings = [f for rule in RULES if rule.__name__[:3].upper() not in skip for f in rule(p)]
    return sorted(findings, key=lambda f: (f.severity != ERROR, f.rule, f.tag))

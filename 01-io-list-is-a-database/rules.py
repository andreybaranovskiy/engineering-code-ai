"""Validation rules for I&C engineering data.

Each rule is a plain function: Project -> list[Finding]. Adding a rule means writing one
function and registering it in RULES. Rules never modify data; they only report.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable

from model import Project

ERROR, WARNING = "ERROR", "WARNING"
TAG_PATTERN = re.compile(r"^\d{3}-[A-Z]{2,4}-\d{3,4}[A-Z]?$")   # e.g. 100-PT-1001
SPARE_MIN = 0.20                                                   # 20 % spare per card


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    tag: str
    message: str


def r01_duplicate_tags(p: Project) -> list[Finding]:
    counts = Counter(i.tag for i in p.index)
    return [Finding("R01", ERROR, t, f"tag appears {n} times in the instrument index")
            for t, n in counts.items() if n > 1]


def r02_tag_format(p: Project) -> list[Finding]:
    return [Finding("R02", WARNING, i.tag, "tag does not follow the AAA-XX-NNNN convention")
            for i in p.index if not TAG_PATTERN.match(i.tag)]


def r03_orphan_io(p: Project) -> list[Finding]:
    known = {i.tag for i in p.index}
    return [Finding("R03", ERROR, io.tag, "IO point has no instrument in the index")
            for io in p.io if io.tag not in known]


def r04_unallocated_instrument(p: Project) -> list[Finding]:
    allocated = {io.tag for io in p.io}
    return [Finding("R04", ERROR, i.tag, "instrument has no IO allocation")
            for i in p.index if i.tag not in allocated]


def r05_range_mismatch(p: Project) -> list[Finding]:
    by_tag = {i.tag: i for i in p.index}
    out = []
    for io in p.io:
        i = by_tag.get(io.tag)
        if i and i.signal in ("AI", "AO") and (i.lrv, i.urv) != (io.lrv, io.urv):
            out.append(Finding("R05", ERROR, io.tag,
                               f"range {io.lrv}-{io.urv} in IO list, {i.lrv}-{i.urv} in index"))
    return out


def r06_units_mismatch(p: Project) -> list[Finding]:
    by_tag = {i.tag: i for i in p.index}
    return [Finding("R06", ERROR, io.tag, f"units '{io.units}' in IO list, '{by_tag[io.tag].units}' in index")
            for io in p.io if io.tag in by_tag and by_tag[io.tag].signal in ("AI", "AO")
            and io.units != by_tag[io.tag].units]


def _alarms(i):
    return [("LL", i.alarm_ll), ("L", i.alarm_l), ("H", i.alarm_h), ("HH", i.alarm_hh)]


def r07_alarm_outside_range(p: Project) -> list[Finding]:
    out = []
    for i in p.index:
        if i.lrv is None or i.urv is None:
            continue
        for name, value in _alarms(i):
            if value is not None and not (i.lrv <= value <= i.urv):
                out.append(Finding("R07", ERROR, i.tag,
                                   f"{name} alarm {value} {i.units} outside range {i.lrv}-{i.urv}"))
    return out


def r08_alarm_order(p: Project) -> list[Finding]:
    out = []
    for i in p.index:
        values = [(n, v) for n, v in _alarms(i) if v is not None]
        for (n1, v1), (n2, v2) in zip(values, values[1:]):
            if v1 >= v2:
                out.append(Finding("R08", ERROR, i.tag, f"{n1} ({v1}) is not below {n2} ({v2})"))
    return out


def r09_signal_vs_card(p: Project) -> list[Finding]:
    by_tag = {i.tag: i for i in p.index}
    return [Finding("R09", ERROR, io.tag, f"{by_tag[io.tag].signal} signal on a {io.card_type} card {io.card}")
            for io in p.io if io.tag in by_tag and by_tag[io.tag].signal != io.card_type]


def r10_double_allocated_channel(p: Project) -> list[Finding]:
    seen = defaultdict(list)
    for io in p.io:
        seen[(io.system, io.cabinet, io.card, io.channel)].append(io.tag)
    return [Finding("R10", ERROR, ", ".join(tags), f"channel {key[3]} of {key[2]} used by {len(tags)} tags")
            for key, tags in seen.items() if len(tags) > 1]


def r11_spare_capacity(p: Project) -> list[Finding]:
    used = Counter((io.system, io.cabinet, io.card) for io in p.io)
    out = []
    for (system, cabinet, card), n in used.items():
        spare = 1 - n / p.channels_per_card
        if spare < SPARE_MIN:
            out.append(Finding("R11", WARNING, card,
                               f"{cabinet}/{card}: {n}/{p.channels_per_card} channels used, "
                               f"{spare:.0%} spare (minimum {SPARE_MIN:.0%})"))
    return out


def r12_sif_on_bpcs(p: Project) -> list[Finding]:
    return [Finding("R12", ERROR, i.tag, f"SIF loop assigned to {i.system}, expected SIS")
            for i in p.index if i.loop_class == "SIF" and i.system != "SIS"]


def r13_system_mismatch(p: Project) -> list[Finding]:
    by_tag = {i.tag: i for i in p.index}
    return [Finding("R13", ERROR, io.tag, f"index says {by_tag[io.tag].system}, IO list says {io.system}")
            for io in p.io if io.tag in by_tag and by_tag[io.tag].system != io.system]


def r14_is_device_on_non_is_card(p: Project) -> list[Finding]:
    by_tag = {i.tag: i for i in p.index}
    return [Finding("R14", ERROR, io.tag, f"IS field device on non-IS card {io.card}")
            for io in p.io if io.tag in by_tag and by_tag[io.tag].is_barrier and not io.card_is]


def r15_cable_checks(p: Project) -> list[Finding]:
    known = {i.tag for i in p.index}
    cabled = {c.tag for c in p.cables}
    out = [Finding("R15", ERROR, c.tag, f"cable {c.cable} refers to unknown tag")
           for c in p.cables if c.tag not in known]
    out += [Finding("R15", ERROR, c.tag, f"cable {c.cable}: {c.pairs_used} pairs used, only {c.pairs} available")
            for c in p.cables if c.pairs_used > c.pairs]
    out += [Finding("R15", WARNING, io.tag, "allocated IO point has no field cable")
            for io in p.io if io.tag in known and io.tag not in cabled]
    return out


RULES: list[Callable[[Project], list[Finding]]] = [
    r01_duplicate_tags, r02_tag_format, r03_orphan_io, r04_unallocated_instrument,
    r05_range_mismatch, r06_units_mismatch, r07_alarm_outside_range, r08_alarm_order,
    r09_signal_vs_card, r10_double_allocated_channel, r11_spare_capacity, r12_sif_on_bpcs,
    r13_system_mismatch, r14_is_device_on_non_is_card, r15_cable_checks,
]


def validate(p: Project) -> list[Finding]:
    findings = [f for rule in RULES for f in rule(p)]
    return sorted(findings, key=lambda f: (f.severity != ERROR, f.rule, f.tag))

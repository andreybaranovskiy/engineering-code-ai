"""Loop sheets generated from the registers. Derived documents: regenerate them, never edit them."""
from __future__ import annotations

from .model import Project


def _f(v):
    return "-" if v is None else f"{v:g}"


def loop_sheet(p: Project, tag: str) -> str:
    inst = next(i for i in p.index if i.tag == tag)
    io = next((x for x in p.io if x.tag == tag), None)
    lines = [
        f"# Loop sheet {inst.tag}", "",
        f"**Service:** {inst.service}  ",
        f"**Signal:** {inst.signal} · **System:** {inst.system} · **Loop class:** {inst.loop_class} · "
        f"**IS:** {'yes' if inst.is_barrier else 'no'}", "",
        "| Range | Units | LL | L | H | HH |", "|---|---|---|---|---|---|",
        f"| {_f(inst.lrv)} – {_f(inst.urv)} | {inst.units or '-'} | {_f(inst.alarm_ll)} | {_f(inst.alarm_l)} | "
        f"{_f(inst.alarm_h)} | {_f(inst.alarm_hh)} |", "", "## Signal path", "",
    ]
    for c in (c for c in p.cables if c.tag == tag):
        lines.append(f"- Cable **{c.cable}**: {c.from_} → {c.to}, {c.pairs_used}/{c.pairs} pairs, {_f(c.length_m)} m")
    if io:
        lines.append(f"- Termination: **{io.system}** cabinet {io.cabinet}, card {io.card} "
                     f"({io.card_type}{', IS' if io.card_is else ''}), channel {io.channel}")
    else:
        lines.append("- Termination: **NOT ALLOCATED**")
    return "\n".join(lines) + "\n"

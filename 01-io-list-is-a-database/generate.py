"""Generate a loop sheet per tag from the three registers.

The loop sheet is derived: it is regenerated whenever the source data changes, never
edited by hand. If the sheet is wrong, the register is wrong.
"""
from __future__ import annotations

from model import Project


def loop_sheet(p: Project, tag: str) -> str:
    inst = next(i for i in p.index if i.tag == tag)
    io = next((x for x in p.io if x.tag == tag), None)
    cables = [c for c in p.cables if c.tag == tag]

    def fmt(v):
        return "-" if v is None else f"{v:g}"

    lines = [
        f"# Loop sheet {inst.tag}",
        "",
        f"**Service:** {inst.service}  ",
        f"**Signal:** {inst.signal} · **System:** {inst.system} · **Loop class:** {inst.loop_class} · "
        f"**IS:** {'yes' if inst.is_barrier else 'no'}",
        "",
        "| Range | Units | LL | L | H | HH |",
        "|---|---|---|---|---|---|",
        f"| {fmt(inst.lrv)} – {fmt(inst.urv)} | {inst.units or '-'} | {fmt(inst.alarm_ll)} | "
        f"{fmt(inst.alarm_l)} | {fmt(inst.alarm_h)} | {fmt(inst.alarm_hh)} |",
        "",
        "## Signal path",
        "",
    ]
    for c in cables:
        lines.append(f"- Cable **{c.cable}**: {c.from_} → {c.to}, {c.pairs_used}/{c.pairs} pairs, "
                     f"{fmt(c.length_m)} m")
    if io:
        lines.append(f"- Termination: **{io.system}** cabinet {io.cabinet}, card {io.card} "
                     f"({io.card_type}{', IS' if io.card_is else ''}), channel {io.channel}")
    else:
        lines.append("- Termination: **NOT ALLOCATED**")
    return "\n".join(lines) + "\n"

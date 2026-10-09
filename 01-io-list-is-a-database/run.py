"""Validate the sample project and generate loop sheets.

    python run.py            # report findings, write loop sheets to out/
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from generate import loop_sheet
from model import Project
from rules import ERROR, RULES, validate

HERE = Path(__file__).parent


def main() -> int:
    p = Project.load(HERE / "data")
    findings = validate(p)

    print(f"{len(p.index)} instruments, {len(p.io)} IO points, {len(p.cables)} cables, {len(RULES)} rules\n")
    for f in findings:
        print(f"{f.severity:<8}{f.rule}  {f.tag:<14} {f.message}")
    totals = Counter(f.severity for f in findings)
    print(f"\n{totals[ERROR]} errors, {totals['WARNING']} warnings")

    out = HERE / "out"
    out.mkdir(exist_ok=True)
    for inst in {i.tag: i for i in p.index}.values():
        (out / f"{inst.tag}.md").write_text(loop_sheet(p, inst.tag), encoding="utf-8")
    print(f"loop sheets written to {out}/")
    return 1 if totals[ERROR] else 0


if __name__ == "__main__":
    sys.exit(main())

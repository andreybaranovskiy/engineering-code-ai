"""iolint command line.

    iolint check [FOLDER] [--index F --io F --cables F] [--format text|json|csv] [--fail-on error|warning|never]
    iolint loopsheets [FOLDER] --out DIR
    iolint rules
    iolint example DIR
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from dataclasses import asdict
from importlib import resources
from pathlib import Path

from . import __version__
from .generate import loop_sheet
from .model import Config, DataError, Project
from .rules import ERROR, RULES, WARNING, validate


def _project(a) -> Project:
    cfg = Config(**{k: v for k, v in (("tag_pattern", a.tag_pattern), ("spare_min", a.spare),
                                       ("channels_per_card", a.channels), ("safety_system", a.safety_system))
                    if v is not None})
    folder = Path(a.folder)
    return Project.load(Path(a.index) if a.index else folder / "instrument_index.csv",
                        Path(a.io) if a.io else folder / "io_list.csv",
                        Path(a.cables) if a.cables else folder / "cable_schedule.csv", cfg)


def cmd_check(a) -> int:
    p = _project(a)
    findings = validate(p, skip=set(a.skip.split(",")) if a.skip else None)
    totals = Counter(f.severity for f in findings)
    if a.format == "json":
        json.dump({"instruments": len(p.index), "io_points": len(p.io), "cables": len(p.cables),
                   "errors": totals[ERROR], "warnings": totals[WARNING],
                   "findings": [asdict(f) for f in findings]}, sys.stdout, indent=2)
        print()
    elif a.format == "csv":
        w = csv.writer(sys.stdout)
        w.writerow(["rule", "severity", "tag", "message"])
        w.writerows([f.rule, f.severity, f.tag, f.message] for f in findings)
    else:
        print(f"{len(p.index)} instruments, {len(p.io)} IO points, {len(p.cables)} cables, {len(RULES)} rules\n")
        for f in findings:
            print(f"{f.severity:<8}{f.rule}  {f.tag:<14} {f.message}")
        print(f"\n{totals[ERROR]} errors, {totals[WARNING]} warnings")
    if a.fail_on == "never":
        return 0
    if a.fail_on == "warning":
        return 1 if findings else 0
    return 1 if totals[ERROR] else 0


def cmd_loopsheets(a) -> int:
    p = _project(a)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tags = list(dict.fromkeys(i.tag for i in p.index))
    for t in tags:
        (out / f"{t.replace('/', '_')}.md").write_text(loop_sheet(p, t), encoding="utf-8")
    print(f"{len(tags)} loop sheets written to {out}")
    return 0


def cmd_rules(a) -> int:
    for r in RULES:
        print(f"{r.__name__[:3].upper()}  {(r.__doc__ or '').strip()}")
    return 0


def cmd_example(a) -> int:
    dest = Path(a.dir)
    dest.mkdir(parents=True, exist_ok=True)
    src = resources.files("iolint") / "example"
    for name in ("instrument_index.csv", "io_list.csv", "cable_schedule.csv"):
        with resources.as_file(src / name) as f:
            shutil.copy(f, dest / name)
    print(f"Sample registers (fictional, with deliberate errors) written to {dest}\nTry: iolint check {dest}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="iolint", description="Check instrument index, IO list and cable schedule for consistency.")
    ap.add_argument("--version", action="version", version=f"iolint {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def data_args(sp):
        sp.add_argument("folder", nargs="?", default=".", help="folder with instrument_index.csv, io_list.csv, cable_schedule.csv")
        sp.add_argument("--index", help="instrument index CSV (overrides FOLDER)")
        sp.add_argument("--io", help="IO list CSV (overrides FOLDER)")
        sp.add_argument("--cables", help="cable schedule CSV (overrides FOLDER)")
        sp.add_argument("--tag-pattern", help="regex for valid tags (default: AAA-XX-NNNN)")
        sp.add_argument("--spare", type=float, help="minimum spare fraction per card (default 0.20)")
        sp.add_argument("--channels", type=int, help="channels per IO card (default 16)")
        sp.add_argument("--safety-system", help="name of the safety system for SIF loops (default SIS)")

    c = sub.add_parser("check", help="validate the registers")
    data_args(c)
    c.add_argument("--format", choices=["text", "json", "csv"], default="text")
    c.add_argument("--fail-on", choices=["error", "warning", "never"], default="error", help="exit code 1 when ... (default error)")
    c.add_argument("--skip", help="comma-separated rule ids to skip, e.g. R02,R11")
    c.set_defaults(fn=cmd_check)

    l = sub.add_parser("loopsheets", help="generate a Markdown loop sheet per tag")
    data_args(l)
    l.add_argument("--out", default="loop_sheets")
    l.set_defaults(fn=cmd_loopsheets)

    sub.add_parser("rules", help="list the rules").set_defaults(fn=cmd_rules)
    e = sub.add_parser("example", help="write sample registers to try iolint on")
    e.add_argument("dir", nargs="?", default="iolint-example")
    e.set_defaults(fn=cmd_example)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except DataError as err:
        print(f"iolint: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

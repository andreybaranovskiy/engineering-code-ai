# iolint

**Consistency checks for the instrument index, IO list and cable schedule.**

The errors that cost most at loop check usually sit *between* registers: a range that differs between the index and the IO list, an IO point with no instrument, a safety loop wired to the DCS, an intrinsically safe device on a non-IS card. `iolint` reads the three registers as CSV and checks them against each other in under a second.

From the article *[Your IO list is a database: engineering data as code](https://www.linkedin.com/in/andrey-baranovskiy/recent-activity/articles/)* by Andrey Baranovskiy, CEng.

## Install

Python 3.10 or later; no other dependencies.

```
pip install "git+https://github.com/andreybaranovskiy/engineering-code-ai#subdirectory=iolint"
```

## Try it in 30 seconds

```
iolint example demo          # writes three sample registers (fictional, with deliberate errors)
iolint check demo            # 12 errors, 1 warning
iolint loopsheets demo --out demo/loop_sheets
iolint rules                 # what each rule checks
```

## Use it on your project

Export your registers to CSV, in one folder:

| file | required columns |
|---|---|
| `instrument_index.csv` | tag, service, signal, lrv, urv, units, system, loop_class, is, ll, l, h, hh |
| `io_list.csv` | tag, system, cabinet, card, card_type, card_is, channel, lrv, urv, units |
| `cable_schedule.csv` | cable, tag, pairs, pairs_used, from, to, length_m |

`signal` and `card_type` are AI/AO/DI/DO; `loop_class` is BPCS or SIF; `is` and `card_is` are Y/N.
If your files have other names, pass them explicitly: `iolint check --index a.csv --io b.csv --cables c.csv`.

```
iolint check my_project
iolint check my_project --tag-pattern "^\d{3}-[A-Z]+-\d{4}$" --channels 32 --spare 0.15
iolint check my_project --format csv > findings.csv        # or --format json
iolint check my_project --skip R02,R11                     # skip rules
```

`check` exits with code 1 when it finds errors (`--fail-on warning|never` to change that), so it can gate a document issue the way tests gate a software release. A value it cannot read (for example a range typed as "0 to 10") stops it with the file, line and column.

## The rules

| | checks |
|---|---|
| R01 | duplicate tags in the index |
| R02 | tag naming convention (configurable) |
| R03 | IO point with no instrument |
| R04 | instrument with no IO allocation |
| R05 | analog range differs between index and IO list |
| R06 | units differ between index and IO list |
| R07 | alarm set point outside the instrument range |
| R08 | alarm order LL < L < H < HH |
| R09 | signal type vs IO card type |
| R10 | channel allocated twice |
| R11 | card spare capacity below the minimum (configurable) |
| R12 | SIF loop not on the safety system |
| R13 | control system differs between index and IO list |
| R14 | IS field device on a non-IS card |
| R15 | cable to an unknown tag, pairs over-used, IO with no cable |

## Use it from Python

```python
from iolint import Project, Config, validate
p = Project.load_folder("my_project", Config(channels_per_card=32))
for f in validate(p):
    print(f.rule, f.severity, f.tag, f.message)
```

## Limits

It checks consistency, not engineering. A wrong value that agrees in all three registers passes. Rules encode common project assumptions; review them against your project's specification. All sample data is fictional.

MIT licence · © 2026 Andrey Baranovskiy

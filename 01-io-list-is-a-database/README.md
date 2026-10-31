# 01 — Your IO list is a database

Companion code for the article [*"Your IO list is a database: engineering data as code"*](https://www.linkedin.com/in/andrey-baranovskiy/recent-activity/articles/) by Andrey Baranovskiy.

Plain Python 3.10+, standard library only. All data is fictional (an inlet separator, "Unit 100").

```
python run.py              # validate data/*.csv, print findings, write loop sheets to out/
python -m unittest -v      # 16 tests: one per rule + a clean-project test
```

| file | purpose |
|---|---|
| `model.py` | typed records; parses the three CSV registers once |
| `rules.py` | 15 validation rules, each `Project -> list[Finding]` |
| `generate.py` | loop sheet generator (derived document) |
| `run.py` | report + generation; exits 1 when errors are found |
| `data/` | sample instrument index, IO list and cable schedule with deliberate errors |

To try it on your project: export your registers to CSV with the same column names (or change the loaders in `model.py`), then run `python run.py`.

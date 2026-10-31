# Engineering × Code × AI

Companion code for a series of long-form articles, published every 4 weeks, by **Andrey Baranovskiy, CEng**: practical software and AI for instrumentation, control and ICT/ELV engineering.

Articles: published every 4 weeks at [andreybaranovskiy.com/articles](https://andreybaranovskiy.com/articles) and in the LinkedIn newsletter Engineering + Code + AI.

| # | Article | Folder | Published |
|---|---|---|---|
| 01 | Your IO list is a database: engineering data as code | [`01-io-list-is-a-database`](01-io-list-is-a-database) | 10 Oct 2026 |
| 02 | LLMs reading P&IDs and datasheets: a measured test | [`02-llms-reading-pids-and-datasheets`](02-llms-reading-pids-and-datasheets) | 7 Nov 2026 |

## Tools

- **[iolint](iolint)**: the checks from article 01 as an installable command-line tool.
  `pip install "git+https://github.com/andreybaranovskiy/engineering-code-ai#subdirectory=iolint"`, then `iolint example demo && iolint check demo`.

## Running the code

Each folder is self-contained, with its own README. Most need only Python 3.10+:

```
cd 01-io-list-is-a-database
python run.py
python -m unittest -v
```

## Notes

- All data in this repository is **fictional**. Nothing here describes any employer's or client's project, data or tools.
- The code is written to be read and adapted, not as a finished product. Review it before using it on project data.
- Licence: MIT (see `LICENSE`).

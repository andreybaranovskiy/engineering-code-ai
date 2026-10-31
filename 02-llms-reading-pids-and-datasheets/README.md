# 02 · LLMs reading P&IDs and datasheets: a measured test

Companion code for the article
[LLMs reading P&IDs and datasheets: a measured test](https://andreybaranovskiy.com/articles/llms-reading-pids-and-datasheets).

A synthetic test set of vendor datasheets and P&ID sheets with known answers, a script that asks a
vision-capable model to read them into structured records, deterministic checks that decide which
extracted values a person must look at, and a scorer. All data is fictional.

## What is here

| path | what it is |
|---|---|
| `testset/datasheets/` | 12 single-tag datasheets (3 scanned, no text layer) and one four-tag sheet as PDF and as a fax |
| `testset/pids/` | 3 P&ID sheets (2 clean, 1 dense and scanned), each also cut into 4 overlapping tiles, plus the dense sheet printed at 35 % and 25 % |
| `testset/truth.json` | the answer key, with the trap each document carries |
| `testset/make_testset*.py` | how the test set was generated (needs `reportlab` and `pillow`) |
| `data/instrument_index.csv` | the instrument index the extracted values are checked against (from article 01, plus area 200) |
| `extract.py` | builds the requests; runs them live or writes an OpenAI Batch file; imports batch results |
| `checks.py` | the checks: value in its evidence, value in the document, sanity, index cross-check, run-to-run agreement |
| `score.py` | scores the saved answers against the key and reports what the checks caught |
| `test_checks.py` | tests for the checks |
| `results/raw/` | all 124 model answers from the run reported in the article (gpt-5.4-mini and gpt-5.5, two runs each, 31 Oct 2026) |
| `results/summary.md`, `results/errors.csv` | the scored results, and every wrong value with its evidence |

## Reproduce the scores (no API key needed)

```
python score.py
python -m unittest -v
```

Python 3.10+, standard library only. `pdftotext` (poppler) is used if installed, for the
"value is in the document" check; without it that check is skipped.

## Run the models yourself

```
export OPENAI_API_KEY=...
python extract.py live --model gpt-5.4-mini --runs 2      # answers go to results/raw/gpt-5.4-mini/
python score.py
```

Or, at half the price, write a Batch API file per model, submit it, and import the output:

```
python extract.py batch --model gpt-5.5 --runs 2 > batch.jsonl
# upload batch.jsonl with purpose=batch, create a batch for /v1/responses, download the output file, then:
python extract.py import batch_output.jsonl
```

Swap in your own documents by adding them to `testset/` and to `truth.json`. Replace
`data/instrument_index.csv` with an export of your own index.

## Notes

- The prompts are in `extract.py`. They say what an engineer would say: report the calibrated range,
  not the sensor limits; the current revision; null when the sheet says TBC; copy the evidence.
- Model answers vary from run to run. Your numbers will not match the article exactly; the pattern should.
- A clean score on this test set does not mean a model is safe on your documents. Build a test set from
  your own document types first. That is the real point of the article.

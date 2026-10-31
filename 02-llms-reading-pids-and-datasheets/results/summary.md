# Results

## Datasheets

Tier 1: 12 single-tag datasheets (3 of them scans), 8 fields each. Tier 2: one four-tag datasheet, as a PDF and as a fax. Two runs per model, reasoning effort low.

| model | tier | values | correct | wrong | caught by checks | caught by checks + second run | silent errors | correct values flagged: register findings | correct values flagged: noise |
|---|---|---|---|---|---|---|---|---|---|
| gpt-5.4-mini | 1 | 192 | 192 (100.0 %) | 0 | 0 | 0 | 0 | 50 | 0 |
| gpt-5.4-mini | 2 | 128 | 117 (91.4 %) | 11 | 10 | 11 | 0 | 4 | 21 |
| gpt-5.5 | 1 | 192 | 190 (99.0 %) | 2 | 2 | 2 | 0 | 50 | 0 |
| gpt-5.5 | 2 | 128 | 128 (100.0 %) | 0 | 0 | 0 | 0 | 4 | 16 |

- gpt-5.4-mini, tier 1: of 0 wrong values, the model listed 0 as uncertain; the other model disagreed on 0.
- gpt-5.4-mini, tier 2: of 11 wrong values, the model listed 10 as uncertain; the other model disagreed on 11.
- gpt-5.5, tier 1: of 2 wrong values, the model listed 0 as uncertain; the other model disagreed on 2.
- gpt-5.5, tier 2: of 0 wrong values, the model listed 0 as uncertain; the other model disagreed on 0.

### Wrong values per document (both runs)

| document | trap | gpt-5.4-mini | gpt-5.5 |
|---|---|---|---|
| DS-01-100-PT-1001.pdf | none: the control sheet | 0 | 0 |
| DS-02-100-PT-1002.pdf | sensor limits (-1...40 bar) printed above the calibrated range | 0 | 0 |
| DS-03-100-LT-1003.pdf | probe length 2000 mm next to the 1500 mm range | 0 | 2 |
| DS-04-100-LT-1004.pdf | scanned page: no text layer, slight skew and noise | 0 | 0 |
| DS-05-100-FT-1005.pdf | Rev A range struck through but still in the text layer; Rev B value beside it | 0 | 0 |
| DS-06-100-TT-1006.pdf | ambient temperature range printed above the calibrated range | 0 | 0 |
| DS-07-100-PDT-1007.pdf | range in kPa; the index holds it as 0-2 bar | 0 | 0 |
| DS-08-100-AT-1010.pdf | scanned page; output has no HART, unlike its neighbours | 0 | 0 |
| DS-09-100-PT-1011.pdf | a real discrepancy: the index says 0-25 barg; the datasheet is right | 0 | 0 |
| DS-10-100-PT-1012.pdf | German/English sheet with decimal commas; tag is PT1012 in the index | 0 | 0 |
| DS-11-100-PT-1013.pdf | scanned page; the tag is not in the instrument index | 0 | 0 |
| DS-12-100-FT-1015.pdf | range not yet known (TBC); the right answer is no number at all | 0 | 0 |
| DS-20-200-PT-2001-2004.pdf | four tags in columns; ditto marks; units in the row header; sensor URL row; old range in a footnote | 0 | 0 |
| DS-21-200-PT-2001-2004-fax.pdf | the same sheet as a fax: ~100 dpi, 1-bit, skewed, speckled, JPEG | 11 | 0 |

## P&IDs

Tier 1: 2 clean sheets, 25 instruments, 17 settings, 1 deleted instrument. Tier 2: a dense scanned sheet, 34 instruments, 14 settings, 2 deleted. Tier 3: the same dense sheet printed smaller. Two runs per model.

| model | tier | input | instruments found | false instruments | deleted reported | settings right | settings wrong or missing | settings put on the wrong instrument |
|---|---|---|---|---|---|---|---|---|
| gpt-5.4-mini | 1 | whole sheet | 50/50 | 0 | 0 | 34/34 | 0 | 0 |
| gpt-5.4-mini | 1 | 4 tiles | 50/50 | 0 | 0 | 34/34 | 0 | 2 |
| gpt-5.4-mini | 2 | whole sheet (printed at 50 %) | 65/68 | 0 | 0 | 28/28 | 0 | 0 |
| gpt-5.4-mini | 2 | 4 tiles (printed at 50 %) | 66/68 | 3 | 0 | 28/28 | 0 | 0 |
| gpt-5.4-mini | 3 | whole sheet (printed at 35 %) | 64/68 | 0 | 0 | 28/28 | 0 | 0 |
| gpt-5.4-mini | 3 | whole sheet (printed at 25 %) | 33/68 | 11 | 0 | 22/28 | 6 | 0 |
| gpt-5.5 | 1 | whole sheet | 50/50 | 0 | 0 | 34/34 | 0 | 0 |
| gpt-5.5 | 1 | 4 tiles | 50/50 | 0 | 0 | 34/34 | 0 | 2 |
| gpt-5.5 | 2 | whole sheet (printed at 50 %) | 68/68 | 0 | 0 | 28/28 | 0 | 0 |
| gpt-5.5 | 2 | 4 tiles (printed at 50 %) | 67/68 | 1 | 0 | 26/28 | 2 | 0 |
| gpt-5.5 | 3 | whole sheet (printed at 35 %) | 68/68 | 0 | 0 | 28/28 | 0 | 0 |
| gpt-5.5 | 3 | whole sheet (printed at 25 %) | 58/68 | 10 | 0 | 14/28 | 14 | 4 |

### Two readings of each sheet, compared

A tag or setting goes to review when the two readings disagree. Silent = wrong in both readings.

| model | tier | readings compared | errors in either reading | sent to review | silent | correct items sent to review |
|---|---|---|---|---|---|---|
| gpt-5.4-mini | 1 | run 1 vs run 2, whole sheet | 0 | 0 | 0 | 0 |
| gpt-5.4-mini | 1 | whole sheet vs tiles, run 1 | 1 | 1 | 0 | 0 |
| gpt-5.4-mini | 2 | run 1 vs run 2, whole sheet | 3 | 3 | 0 | 0 |
| gpt-5.4-mini | 2 | whole sheet vs tiles, run 1 | 1 | 1 | 0 | 0 |
| gpt-5.4-mini | 3 (35 %) | run 1 vs run 2, whole sheet | 4 | 4 | 0 | 0 |
| gpt-5.4-mini | 3 (25 %) | run 1 vs run 2, whole sheet | 43 | 28 | 15 | 0 |
| gpt-5.5 | 1 | run 1 vs run 2, whole sheet | 0 | 0 | 0 | 0 |
| gpt-5.5 | 1 | whole sheet vs tiles, run 1 | 1 | 1 | 0 | 0 |
| gpt-5.5 | 2 | run 1 vs run 2, whole sheet | 0 | 0 | 0 | 0 |
| gpt-5.5 | 2 | whole sheet vs tiles, run 1 | 0 | 0 | 0 | 0 |
| gpt-5.5 | 3 (35 %) | run 1 vs run 2, whole sheet | 0 | 0 | 0 | 0 |
| gpt-5.5 | 3 (25 %) | run 1 vs run 2, whole sheet | 40 | 31 | 9 | 0 |

## Tokens

| model | requests | input tokens | output tokens (of which reasoning) |
|---|---|---|---|
| gpt-5.4-mini | 62 | 117,534 | 30,371 (13,501) |
| gpt-5.5 | 62 | 117,534 | 21,739 (2,882) |

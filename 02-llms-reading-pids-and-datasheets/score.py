"""Score the saved answers in results/raw/ against testset/truth.json, and measure what the checks catch.

  python score.py                 # prints the summary and writes results/summary.md and results/errors.csv

No API key needed: it reads the answers saved by extract.py.
"""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from checks import check_datasheet, compare, document_text, load_index, norm_text, unit

HERE = Path(__file__).parent
RAW = HERE / "results" / "raw"
TRUTH = json.loads((HERE / "testset" / "truth.json").read_text())
FIELDS = ["tag", "lrv", "urv", "units", "output_signal", "ex_protection", "process_connection", "wetted_material"]


def load(model, name, run):
    p = RAW / model / f"{name}.run{run}.json"
    return json.loads(p.read_text())["answer"] if p.exists() else None


def correct(field, got, want):
    wants = want if isinstance(want, list) else [want]
    for w in wants:
        if w is None or got is None:
            if w is None and got is None:
                return True
            continue
        if field in ("lrv", "urv"):
            if abs(float(got) - float(w)) < 1e-9:
                return True
        elif field == "units":
            if unit(got) == unit(w):
                return True
        elif field == "tag":
            if got.strip().upper() == w:
                return True
        elif norm_text(got) == norm_text(w):
            return True
    return False


def models():
    return sorted(p.name for p in RAW.iterdir() if p.is_dir()) if RAW.exists() else []


# --------------------------------------------------------------------------- datasheets


EMPTY = {**{f: {"value": None, "evidence": ""} for f in FIELDS}, "uncertain": []}


def records(model, run, texts):
    """(document, tier, layout, truth, extracted record) for every tag on every datasheet."""
    for d in TRUTH["datasheets"]:
        yield d["file"], d.get("tier", 1), d["layout"], d["fields"], load(model, d["file"], run)
    for d in TRUTH.get("datasheets_multi", []):
        ans = load(model, d["file"], run)
        if ans is None:
            continue
        by_tag = {(r["tag"]["value"] or "").strip().upper(): r for r in ans["instruments"]}
        for t in d["records"]:
            yield d["file"], d.get("tier", 2), "M", t, by_tag.get(t["tag"], EMPTY)


def score_datasheets(out, err_rows):
    index = load_index()
    texts = {}
    for d in TRUTH["datasheets"] + TRUTH.get("datasheets_multi", []):
        texts[d["file"]] = document_text(HERE / "testset" / "datasheets" / d["file"])
    ms = models()
    out.append("## Datasheets\n")
    out.append("Tier 1: 12 single-tag datasheets (3 of them scans), 8 fields each. "
               "Tier 2: one four-tag datasheet, as a PDF and as a fax. Two runs per model, reasoning effort low.\n")
    header = ("| model | tier | values | correct | wrong | caught by checks | caught by checks + second run | "
              "silent errors | correct values flagged: register findings | correct values flagged: noise |")
    out += [header, "|---" * (header.count("|") - 1) + "|"]
    per_doc = defaultdict(Counter)
    notes = []
    for m in ms:
        other = [x for x in ms if x != m]
        for tier in (1, 2):
            c = Counter()
            for r in (1, 2):
                twin = {(doc, t["tag"]): rec for doc, _, _, t, rec in records(m, 3 - r, texts)}
                oth = {(doc, t["tag"]): rec for doc, _, _, t, rec in records(other[0], r, texts)} if other else {}
                for doc, tr, layout, truth, rec in records(m, r, texts):
                    if tr != tier or rec is None:
                        continue
                    flags = check_datasheet(rec, texts[doc], index)
                    record_level = any(w.startswith("X1") for w in flags.get("tag", []))
                    tw = twin.get((doc, truth["tag"]))
                    disagree = set(compare(rec, tw)) if tw else set()
                    ot = oth.get((doc, truth["tag"]))
                    model_disagree = set(compare(rec, ot)) if ot else set()
                    uncertain = set(rec.get("uncertain", []))
                    for f in FIELDS:
                        got = rec[f]["value"]
                        ok = correct(f, got, truth[f])
                        flagged = bool(flags.get(f)) or record_level
                        c["values"] += 1
                        if ok:
                            c["correct"] += 1
                            reasons = flags.get(f, []) + (["X1"] if record_level else [])
                            if any(w.startswith("X") for w in reasons):
                                c["finding"] += 1
                            elif reasons or f in disagree:
                                c["noise"] += 1
                            continue
                        c["wrong"] += 1
                        per_doc[doc][m] += 1
                        c["caught"] += flagged
                        c["caught_runs"] += flagged or f in disagree
                        c["silent"] += not (flagged or f in disagree)
                        c["uncertain_on_wrong"] += f in uncertain
                        c["model_disagree_on_wrong"] += f in model_disagree
                        err_rows.append(dict(model=m, run=r, tier=tier, document=doc, layout=layout, tag=truth["tag"],
                                             field=f, extracted=got, evidence=rec[f]["evidence"], truth=truth[f],
                                             checks="; ".join(flags.get(f, [])) + ("; X1 record" if record_level else ""),
                                             runs_disagree=f in disagree, model_said_uncertain=f in uncertain,
                                             models_disagree=f in model_disagree))
            if not c["values"]:
                continue
            out.append(f"| {m} | {tier} | {c['values']} | {c['correct']} ({100 * c['correct'] / c['values']:.1f} %) | "
                       f"{c['wrong']} | {c['caught']} | {c['caught_runs']} | {c['silent']} | {c['finding']} | {c['noise']} |")
            notes.append(f"- {m}, tier {tier}: of {c['wrong']} wrong values, the model listed {c['uncertain_on_wrong']} as "
                         f"uncertain; the other model disagreed on {c['model_disagree_on_wrong']}.")
    out += [""] + notes + [""]
    out.append("### Wrong values per document (both runs)\n")
    out.append("| document | trap | " + " | ".join(ms) + " |")
    out.append("|---|---|" + "---|" * len(ms))
    for d in TRUTH["datasheets"] + TRUTH.get("datasheets_multi", []):
        out.append(f"| {d['file']} | {d['trap']} | " + " | ".join(str(per_doc[d["file"]][m]) for m in ms) + " |")
    out.append("")


# --------------------------------------------------------------------------- P&IDs


def pid_tag(t, area):
    """Normalise a P&ID tag; add the sheet's area prefix in code when the model could not see the note."""
    t = re.sub(r"\s+", "-", t.strip().upper())
    m = re.fullmatch(r"(?:(\d{3})-)?([A-Z]{1,4})-?(\d{4})", t)
    if not m:
        return t, False
    return f"{m.group(1) or area}-{m.group(2)}-{m.group(3)}", m.group(1) is None


def pid_answer(model, run, sheet, tiled):
    """Merged instrument list for a sheet: one answer, or the union of the four tiles."""
    names = sheet["tiles"] if tiled else [sheet["file"]]
    merged, no_prefix = {}, 0
    area = sheet["file"].split("-")[1]  # PID-200-001 -> 200, as the title block says
    for n in names:
        a = load(model, n, run)
        if a is None:
            return None, 0
        for ins in a["instruments"]:
            tag, missing = pid_tag(ins["tag"], area)
            no_prefix += missing
            sps = merged.setdefault(tag, {})
            for s in ins["setpoints"]:
                sps[s["name"].strip().upper()] = s["value"]
    return merged, no_prefix


def score_pids(out):
    ms = models()
    out.append("## P&IDs\n")
    out.append("Tier 1: 2 clean sheets, 25 instruments, 17 settings, 1 deleted instrument. "
               "Tier 2: a dense scanned sheet, 34 instruments, 14 settings, 2 deleted. "
               "Tier 3: the same dense sheet printed smaller. Two runs per model.\n")
    out.append("| model | tier | input | instruments found | false instruments | deleted reported | "
               "settings right | settings wrong or missing | settings put on the wrong instrument |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    groups = [("1", [p for p in TRUTH["pids"] if p.get("tier", 1) == 1], "", (False, True)),
              ("2", [p for p in TRUTH["pids"] if p.get("tier") == 2], " (printed at 50 %)", (False, True))]
    groups += [("3", [p], f" (printed at {p['scale']} %)", (False,)) for p in TRUTH["pids"] if p.get("tier") == 3]
    for m in ms:
        for tier, sheets, label, modes in groups:
            for tiled in modes:
                c = Counter()
                for r in (1, 2):
                    for sheet in sheets:
                        got, _ = pid_answer(m, r, sheet, tiled)
                        if got is None:
                            continue
                        want = {t["tag"]: t["setpoints"] for t in sheet["tags"]}
                        c["runs"] += 1
                        c["found"] += len(set(got) & set(want))
                        c["want"] += len(want)
                        c["false"] += len(set(got) - set(want) - set(sheet["must_not_report"]))
                        c["deleted"] += len(set(got) & set(sheet["must_not_report"]))
                        for tag, sps in want.items():
                            for k, v in sps.items():
                                c["sp_total"] += 1
                                if tag in got and k in got[tag] and abs(got[tag][k] - v) < 1e-9:
                                    c["sp_ok"] += 1
                                else:
                                    c["sp_bad"] += 1
                        for tag, sps in got.items():
                            for k in sps:
                                if tag in want and k not in want[tag]:
                                    c["sp_extra"] += 1
                if c["runs"]:
                    out.append(f"| {m} | {tier} | {'4 tiles' if tiled else 'whole sheet'}{label} | {c['found']}/{c['want']} | "
                               f"{c['false']} | {c['deleted']} | {c['sp_ok']}/{c['sp_total']} | {c['sp_bad']} | {c['sp_extra']} |")
    out.append("")


def pid_two_readings(out):
    """Read every sheet twice and compare. Whatever the two readings disagree on goes to a person.
    An error survives only if both readings make it."""
    out.append("### Two readings of each sheet, compared\n")
    out.append("A tag or setting goes to review when the two readings disagree. Silent = wrong in both readings.\n")
    out.append("| model | tier | readings compared | errors in either reading | sent to review | silent | correct items sent to review |")
    out.append("|---|---|---|---|---|---|---|")
    pairs = [("run 1 vs run 2, whole sheet", (False, 1), (False, 2)),
             ("whole sheet vs tiles, run 1", (False, 1), (True, 1))]
    groups = [("1", [p for p in TRUTH["pids"] if p.get("tier", 1) == 1], pairs),
              ("2", [p for p in TRUTH["pids"] if p.get("tier") == 2], pairs)]
    groups += [(f"3 ({p['scale']} %)", [p], pairs[:1]) for p in TRUTH["pids"] if p.get("tier") == 3]
    for m in models():
        for tier, sheets, prs in groups:
            for label, (ta, ra), (tb, rb) in prs:
                c = Counter()
                for sheet in sheets:
                    a, _ = pid_answer(m, ra, sheet, ta)
                    b, _ = pid_answer(m, rb, sheet, tb)
                    if a is None or b is None:
                        continue
                    want = {t["tag"]: t["setpoints"] for t in sheet["tags"]}
                    items = lambda x: {(t, None) for t in x} | {(t, (k, v)) for t, sp in x.items() for k, v in sp.items()}
                    truth, ia, ib = items(want), items(a), items(b)
                    wrong_a, wrong_b = (truth ^ ia), (truth ^ ib)   # missing or extra, per reading
                    review = ia ^ ib                                 # what the readings disagree on
                    errors = wrong_a | wrong_b
                    c["errors"] += len(errors)
                    c["review"] += len(errors & review)
                    c["silent"] += len(errors - review)
                    c["false_review"] += len(review - errors)
                if c:
                    out.append(f"| {m} | {tier} | {label} | {c['errors']} | {c['review']} | {c['silent']} | {c['false_review']} |")
    out.append("")


def usage(out):
    out.append("## Tokens\n")
    out.append("| model | requests | input tokens | output tokens (of which reasoning) |")
    out.append("|---|---|---|---|")
    for m in models():
        n = i = o = rsn = 0
        for p in (RAW / m).glob("*.json"):
            u = json.loads(p.read_text())["usage"]
            n += 1; i += u.get("input_tokens", 0); o += u.get("output_tokens", 0)
            rsn += (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
        out.append(f"| {m} | {n} | {i:,} | {o:,} ({rsn:,}) |")
    out.append("")


def main():
    out, err_rows = ["# Results\n"], []
    score_datasheets(out, err_rows)
    score_pids(out)
    pid_two_readings(out)
    usage(out)
    text = "\n".join(out)
    (HERE / "results" / "summary.md").write_text(text)
    with open(HERE / "results" / "errors.csv", "w", newline="") as f:
        if err_rows:
            w = csv.DictWriter(f, fieldnames=list(err_rows[0]))
            w.writeheader(); w.writerows(err_rows)
    print(text)


if __name__ == "__main__":
    main()

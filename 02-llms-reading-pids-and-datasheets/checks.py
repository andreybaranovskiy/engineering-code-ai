"""Deterministic checks on what a model extracted from a datasheet.

None of these checks knows the right answer. They only ask whether the answer is consistent:
with itself, with the document, with the instrument index, and with a second reading.
A value that fails any check goes to a person; a value that passes goes into the register.
"""
import csv
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).parent

# --------------------------------------------------------------------------- normalising

UNITS = {
    "barg": "barg", "bar g": "barg", "bar(g)": "barg", "bar.g": "barg", "bar gauge": "barg",
    "bar": "bar", "kpa": "kPa", "mpa": "MPa", "psi": "psi", "psig": "psig", "mbar": "mbar",
    "mm": "mm", "m": "m", "ppm": "ppm", "ppm h2s": "ppm", "ppmv": "ppm",
    "degc": "degC", "°c": "degC", "deg c": "degC", "c": "degC",
    "sm3/h": "Sm3/h", "sm³/h": "Sm3/h", "sm3/hr": "Sm3/h", "nm3/h": "Nm3/h",
}
# unit -> (quantity, factor to the base unit of that quantity)
CONVERT = {"barg": ("gauge pressure", 1.0), "psig": ("gauge pressure", 0.0689476),
           "bar": ("pressure", 1.0), "kPa": ("pressure", 0.01), "MPa": ("pressure", 10.0),
           "mbar": ("pressure", 0.001), "psi": ("pressure", 0.0689476),
           "mm": ("length", 1.0), "m": ("length", 1000.0), "degC": ("temperature", 1.0),
           "ppm": ("concentration", 1.0), "Sm3/h": ("std flow", 1.0)}


def unit(u):
    if u is None:
        return None
    return UNITS.get(u.strip().lower().replace("³", "3"), u.strip())


def norm_text(s):
    """Spelling-insensitive form of a text value: case, spaces, dashes and inch marks ignored."""
    if s is None:
        return None
    s = s.lower().replace("½", "1/2").replace("¼", "1/4").replace("¾", "3/4")
    s = s.replace("″", '"').replace("”", '"').replace("inch", '"').replace("in.", '"')
    return re.sub(r"[\s\-–—_.,;:()]", "", s)


def number_forms(x):
    """The ways a number may be printed: 50000, 50 000, 50,000, 50.000 and 16 / 16,0 / 16.0."""
    if x is None:
        return set()
    forms = {f"{x:g}", f"{x:.1f}", f"{x:.1f}".replace(".", ",")}
    if float(x).is_integer() and abs(x) >= 1000:
        i = int(x)
        forms |= {f"{i:,}", f"{i:,}".replace(",", " "), f"{i:,}".replace(",", ".")}
    return forms


# --------------------------------------------------------------------------- the checks


def load_index(path=HERE / "data" / "instrument_index.csv"):
    with open(path, newline="") as f:
        return {r["tag"]: r for r in csv.DictReader(f)}


def document_text(pdf):
    """The PDF's text layer, or '' if it has none (a scan) or pdftotext is not installed."""
    if not shutil.which("pdftotext"):
        return ""
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    return text if text.strip() else ""


def check_datasheet(rec, doc_text, index):
    """Return {field: [reasons]} for every field that should go to a person."""
    flags = {}

    def flag(field, why):
        flags.setdefault(field, []).append(why)

    v = {k: rec[k]["value"] for k in rec if k != "uncertain"}
    ev = {k: rec[k]["evidence"] for k in rec if k != "uncertain"}

    for field, value in v.items():
        if value is None:
            # N1. A datasheet always states these. An empty one is a gap for a person, not a pass.
            #     (Added after the first run: the small model returned unreadable ditto cells as empty.)
            flag(field, "N1 required value missing")
            continue
        # E1. The value must appear in the text the model says it came from.
        e = ev[field] or ""
        if isinstance(value, (int, float)):
            if not any(f in e for f in number_forms(value)):
                flag(field, "E1 value not in its evidence")
        elif norm_text(value) not in norm_text(e):
            flag(field, "E1 value not in its evidence")
        # E2. The value must appear somewhere in the document (only possible with a text layer).
        if doc_text.strip():
            if isinstance(value, (int, float)):
                found = any(f in doc_text for f in number_forms(value))
            else:
                found = norm_text(value) in norm_text(doc_text)
            if not found:
                flag(field, "E2 value not found in document")

    # S1-S3. Sanity of the record on its own.
    if (v["lrv"] is None) != (v["urv"] is None):
        flag("lrv" if v["lrv"] is None else "urv", "S1 only one end of the range given")
    if v["lrv"] is not None and v["urv"] is not None and v["lrv"] >= v["urv"]:
        flag("urv", "S2 LRV not below URV")
    if v["units"] is not None and unit(v["units"]) not in CONVERT:
        flag("units", f"S3 unknown units '{v['units']}'")
    if v["tag"] and not re.fullmatch(r"\d{3}-[A-Z]{1,4}-\d{4}", v["tag"]):
        flag("tag", "S4 tag does not follow AAA-XX-NNNN")

    # X1-X3. Cross-check against the instrument index (the register from article 01).
    row = index.get(v["tag"] or "")
    if row is None:
        flag("tag", "X1 tag not in instrument index")
    elif v["urv"] is not None and v["units"]:
        u_doc, u_idx = unit(v["units"]), unit(row["units"])
        if u_doc in CONVERT and u_idx in CONVERT and CONVERT[u_doc][0] == CONVERT[u_idx][0]:
            k = CONVERT[u_doc][1] / CONVERT[u_idx][1]
            for end in ("lrv", "urv"):
                if row[end] != "" and abs(v[end] * k - float(row[end])) > 1e-6 * max(1, abs(float(row[end]))):
                    flag(end, f"X2 {end.upper()} {v[end]} {v['units']} differs from index {row[end]} {row['units']}")
        else:
            flag("units", f"X3 units '{v['units']}' not comparable with index '{row['units']}'")
    return flags


def compare(rec_a, rec_b):
    """Fields where two readings of the same document disagree."""
    out = []
    for field in rec_a:
        if field == "uncertain":
            continue
        a, b = rec_a[field]["value"], rec_b[field]["value"]
        same = (a == b) if not isinstance(a, str) or not isinstance(b, str) else norm_text(a) == norm_text(b)
        if not same:
            out.append(field)
    return out

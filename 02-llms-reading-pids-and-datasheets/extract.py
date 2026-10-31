"""Ask a vision-capable model to read datasheets and P&IDs into structured records.

Standard library only. Two ways to run it:

  python extract.py live  --model gpt-5.4-mini      # calls the OpenAI Responses API now (needs OPENAI_API_KEY)
  python extract.py batch --model gpt-5.5 --runs 2 > batch-gpt-5.5.jsonl
                                                    # writes an OpenAI Batch API input file instead (half price;
                                                    # one model per batch file)
  python extract.py import batch_output.jsonl       # splits a finished batch into results/raw/

Every answer is saved as results/raw/<model>/<document>.run<N>.json, so scoring never needs the API.
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
TESTSET = HERE / "testset"
RAW = HERE / "results" / "raw"

# --------------------------------------------------------------------------- prompts

DATASHEET_PROMPT = """You read one instrument datasheet and return the values it states.

Rules:
- Report what the document says. Do not convert units, round, or fill a gap from general knowledge.
- The range is the calibrated (set) range of this tag. It is not the sensor limits, the probe length,
  the ambient temperature or the pressure rating.
- If a value has been superseded (struck through, or replaced by a later revision), report the current one.
- If the document does not state a value, or says TBC/TBA/later, return null.
- For every value, copy the exact text you took it from into `evidence`.
- List in `uncertain` the names of any fields you are not sure about."""

MULTI_NOTE = """
- This sheet may cover several tags, one per column. Return one record per tag.
- Where a cell refers to another column (a ditto mark, "as col. 2"), resolve it to the actual value."""

PID_PROMPT = """You read one P&ID sheet (or part of one) and list the instruments on it.

Rules:
- An instrument is a tag balloon: function letters above a loop number (e.g. PT over 1001).
- Report the full tag. If the notes say tags carry an area prefix, add it (e.g. 100-PT-1001).
- Do not report instruments that are crossed out, clouded as deleted, or marked DELETED.
- Do not report line numbers, equipment numbers or drawing numbers as instruments.
- For each instrument, list the alarm, trip or set-pressure settings printed beside it
  (e.g. PAH 8.0 barg -> name PAH, value 8.0, units barg). Empty list if none.
- If part of the sheet is cut off, report only what you can read."""


def _field(kind):
    return {"type": "object", "additionalProperties": False, "required": ["value", "evidence"],
            "properties": {"value": {"type": [kind, "null"]}, "evidence": {"type": "string"}}}


DATASHEET_FIELDS = ["tag", "lrv", "urv", "units", "output_signal", "ex_protection",
                    "process_connection", "wetted_material"]
DATASHEET_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": DATASHEET_FIELDS + ["uncertain"],
    "properties": {**{f: _field("number" if f in ("lrv", "urv") else "string") for f in DATASHEET_FIELDS},
                   "uncertain": {"type": "array", "items": {"type": "string", "enum": DATASHEET_FIELDS}}},
}

MULTI_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["instruments"],
    "properties": {"instruments": {"type": "array", "items": DATASHEET_SCHEMA}},
}

PID_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["instruments"],
    "properties": {"instruments": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["tag", "setpoints"],
        "properties": {
            "tag": {"type": "string"},
            "setpoints": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["name", "value", "units"],
                "properties": {"name": {"type": "string"}, "value": {"type": "number"},
                               "units": {"type": ["string", "null"]}}}}}}}},
}

# --------------------------------------------------------------------------- requests


def documents(tier=None):
    """(kind, file name, path) for every document in the test set, or in one tier of it."""
    truth = json.loads((TESTSET / "truth.json").read_text())
    want = lambda d: tier is None or d.get("tier", 1) == tier
    for d in truth["datasheets"]:
        if want(d):
            yield "datasheet", d["file"], TESTSET / "datasheets" / d["file"]
    for d in truth.get("datasheets_multi", []):
        if want(d):
            yield "datasheet_multi", d["file"], TESTSET / "datasheets" / d["file"]
    for p in truth["pids"]:
        if want(p):
            yield "pid", p["file"], TESTSET / "pids" / p["file"]
            for t in p["tiles"]:
                yield "pid", t, TESTSET / "pids" / t


def request_body(kind, name, path, model, effort="low"):
    data = base64.b64encode(path.read_bytes()).decode()
    if kind == "datasheet":
        doc = {"type": "input_file", "filename": name, "file_data": f"data:application/pdf;base64,{data}"}
        prompt, schema, sname = DATASHEET_PROMPT, DATASHEET_SCHEMA, "datasheet"
    elif kind == "datasheet_multi":
        doc = {"type": "input_file", "filename": name, "file_data": f"data:application/pdf;base64,{data}"}
        prompt, schema, sname = DATASHEET_PROMPT + MULTI_NOTE, MULTI_SCHEMA, "datasheet_multi"
    else:
        doc = {"type": "input_image", "image_url": f"data:image/png;base64,{data}", "detail": "high"}
        prompt, schema, sname = PID_PROMPT, PID_SCHEMA, "pid_instruments"
    return {
        "model": model,
        "reasoning": {"effort": effort},
        "input": [{"role": "system", "content": prompt},
                  {"role": "user", "content": [doc, {"type": "input_text", "text": "Extract the data."}]}],
        "text": {"format": {"type": "json_schema", "name": sname, "schema": schema, "strict": True}},
    }


def output_json(response):
    """The structured answer from a Responses API reply, plus token usage."""
    text = "".join(c.get("text", "") for item in response.get("output", []) if item.get("type") == "message"
                   for c in item.get("content", []) if c.get("type") == "output_text")
    return json.loads(text), response.get("usage", {})


def save(model, name, run, answer, usage):
    out = RAW / model / f"{name}.run{run}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"answer": answer, "usage": usage}, indent=2, ensure_ascii=False))


# --------------------------------------------------------------------------- commands


def cmd_live(a):
    key = os.environ["OPENAI_API_KEY"]
    for run in range(1, a.runs + 1):
        for kind, name, path in documents(a.tier):
            body = json.dumps(request_body(kind, name, path, a.model, a.effort)).encode()
            req = urllib.request.Request("https://api.openai.com/v1/responses", data=body, headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                answer, usage = output_json(json.load(r))
            save(a.model, name, run, answer, usage)
            print(f"{a.model} run {run}: {name}", file=sys.stderr)


def cmd_batch(a):
    for model in [a.model]:
        for run in range(1, a.runs + 1):
            for kind, name, path in documents(a.tier):
                print(json.dumps({"custom_id": f"{model}|{run}|{name}", "method": "POST", "url": "/v1/responses",
                                  "body": request_body(kind, name, path, model, a.effort)}))


def cmd_import(a):
    n = bad = 0
    for line in Path(a.file).read_text().splitlines():
        rec = json.loads(line)
        model, run, name = rec["custom_id"].split("|")
        resp = (rec.get("response") or {}).get("body") or {}
        if rec.get("error") or resp.get("status") != "completed":
            bad += 1
            print(f"FAILED {rec['custom_id']}: {rec.get('error') or resp.get('status')}", file=sys.stderr)
            continue
        answer, usage = output_json(resp)
        save(model, name, int(run), answer, usage)
        n += 1
    print(f"imported {n} answers, {bad} failed", file=sys.stderr)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("live"); s.add_argument("--model", required=True); s.add_argument("--tier", type=int)
    s.add_argument("--runs", type=int, default=1); s.add_argument("--effort", default="low")
    s = sub.add_parser("batch"); s.add_argument("--model", required=True); s.add_argument("--tier", type=int)
    s.add_argument("--runs", type=int, default=2); s.add_argument("--effort", default="low")
    s = sub.add_parser("import"); s.add_argument("file")
    a = p.parse_args()
    {"live": cmd_live, "batch": cmd_batch, "import": cmd_import}[a.cmd](a)


if __name__ == "__main__":
    main()

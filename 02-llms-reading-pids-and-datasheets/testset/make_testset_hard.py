"""Tier 2 of the test set: documents as they really arrive.

- DS-20: one datasheet for four tags, one per column, with ditto marks, units in the row header,
  sensor limits beside the range, and a revised range whose old value survives in a footnote.
- DS-21: the same sheet as a fax-quality scan (low resolution, JPEG, skewed, speckled).
- PID-200-001: a dense compressor P&ID with 36 instruments, printed small and scanned.

Run after make_testset.py; it adds tier-2 entries to truth.json. Needs reportlab and Pillow.
"""
import io
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from make_testset import FONT, FONT_B, text_c, tiles

HERE = Path(__file__).parent
random.seed(11)

DITTO = '"'
COLS = ["200-PT-2001", "200-PT-2002", "200-PT-2003", "200-PT-2004"]
ROWS = [
    ("Tag number", COLS),
    ("Service", ["Suction pressure", "Interstage pressure", "Discharge pressure", "Seal gas pressure"]),
    ("Sensor limits URL (bar)", ["40", "100", "400", "100"]),
    ("Calibrated range (barg)", ["0 - 16", "0 - 40", "0 - 100 △1", "as col. 2"]),
    ("Output signal", ["4-20 mA HART", "as col. 1", DITTO, "Foundation Fieldbus"]),
    ("Hazardous area", ["Ex ia IIC T4 Ga", DITTO, DITTO, "Ex d IIC T6 Gb"]),
    ("Process connection", ['1/2" NPT F', DITTO, '3/4" NPT F', '1/2" NPT F']),
    ("Wetted parts", ["SS316L", DITTO, "Inconel 625", "SS316L"]),
]
FOOTNOTE = "△1  Rev 1: col. 3 calibrated range changed from 0 - 60 barg (Rev 0) after compressor re-rate."
TRUTH = [
    dict(tag="200-PT-2001", lrv=0, urv=16, units="barg", output_signal="4-20 mA HART",
         ex_protection="Ex ia IIC T4 Ga", process_connection='1/2" NPT F', wetted_material="SS316L"),
    dict(tag="200-PT-2002", lrv=0, urv=40, units="barg", output_signal="4-20 mA HART",
         ex_protection="Ex ia IIC T4 Ga", process_connection='1/2" NPT F', wetted_material="SS316L"),
    dict(tag="200-PT-2003", lrv=0, urv=100, units="barg", output_signal="4-20 mA HART",
         ex_protection="Ex ia IIC T4 Ga", process_connection='3/4" NPT F', wetted_material=["Inconel 625", "Alloy 625"]),
    dict(tag="200-PT-2004", lrv=0, urv=40, units="barg", output_signal=["Foundation Fieldbus", "FOUNDATION Fieldbus", "FF"],
         ex_protection="Ex d IIC T6 Gb", process_connection='1/2" NPT F', wetted_material="SS316L"),
]


def multi_pdf(path):
    c = canvas.Canvas(str(path), pagesize=landscape(A4))
    c.setAuthor("Andrey Baranovskiy"); c.setTitle("Datasheet 200-PT-2001..2004 (fictional test document)")
    w, h = landscape(A4)
    c.setFont("DVB", 14); c.drawString(40, h - 50, "NORVALE INSTRUMENTS   -   Pressure Transmitters   -   Form ID-01M   Rev 1")
    c.setFont("DV", 9); c.drawString(40, h - 68, "Project: Gas Compression Unit 200 (fictional)    Doc no: GCU-200-IN-DS-0007")
    x0, y = 40, h - 100
    widths = [190, 140, 140, 140, 140]
    for label, vals in ROWS:
        x = x0
        for i, cell in enumerate([label] + vals):
            c.rect(x, y - 6, widths[i], 22)
            c.setFont("DVB" if i == 0 else "DV", 9)
            c.drawString(x + 6, y + 1, cell)
            x += widths[i]
        y -= 22
    c.setFont("DV", 8); c.drawString(40, y - 14, FOOTNOTE)
    c.drawString(40, y - 28, 'Ditto (") and "as col. n" mean the value in the column to the left / in column n applies.')
    c.setFont("DV", 7); c.drawString(40, 30, "Fictional test document for 'Engineering + Code + AI', article 02. Not a real product.")
    c.showPage(); c.save()


def multi_scan(path):
    """Fax quality: drawn at ~100 dpi, skewed, speckled, JPEG-compressed, saved as an image-only PDF."""
    W, H = 1170, 830  # A4 landscape at ~100 dpi
    img = Image.new("L", (W, H), 255)
    g = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 12); fb = ImageFont.truetype(FONT_B, 15)
    g.text((40, 30), "NORVALE INSTRUMENTS  -  Pressure Transmitters  -  Form ID-01M  Rev 1", font=fb, fill=0)
    g.text((40, 55), "Project: Gas Compression Unit 200 (fictional)   Doc no: GCU-200-IN-DS-0007", font=f, fill=0)
    widths = [260, 200, 200, 200, 200]
    y = 90
    for label, vals in ROWS:
        x = 40
        for i, cell in enumerate([label] + vals):
            g.rectangle((x, y, x + widths[i], y + 30), outline=0)
            g.text((x + 6, y + 8), cell, font=f, fill=0)
            x += widths[i]
        y += 30
    g.text((40, y + 12), FOOTNOTE, font=f, fill=0)
    g.text((40, y + 32), 'Ditto (") and "as col. n" mean the value in the column to the left / in column n applies.', font=f, fill=0)
    img = img.rotate(2.0, resample=Image.BICUBIC, fillcolor=255)
    px = img.load()
    for _ in range(14000):
        px[random.randrange(W), random.randrange(H)] = random.choice((0, 60, 120))
    img = img.filter(ImageFilter.GaussianBlur(0.6)).point(lambda v: 0 if v < 150 else 255)  # fax: 1-bit look
    buf = io.BytesIO(); img.convert("L").save(buf, "JPEG", quality=30)
    Image.open(buf).save(path, "PDF", resolution=100, author="Andrey Baranovskiy",
                         title="Datasheet 200-PT-2001..2004 (fictional, fax copy)")


# ---------------------------------------------------------------- dense P&ID
LETTERS = ["PT", "PI", "TT", "TI", "FT", "LT", "PDT", "VT", "ZT", "LG", "TE", "PIT"]


def dense_pid(path, scale=0.5):
    W, H = 4800, 3400  # drawn large, then printed small
    img = Image.new("L", (W, H), 255)
    g = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 26); fs = ImageFont.truetype(FONT, 21); fb = ImageFont.truetype(FONT_B, 34)
    g.rectangle((40, 40, W - 40, H - 40), outline=0, width=6)
    # title block and notes
    tx, ty = W - 1400, H - 380
    g.rectangle((tx, ty, W - 40, H - 40), outline=0, width=4)
    g.text((tx + 25, ty + 25), "EXAMPLE ENERGY CO.  -  GAS COMPRESSION UNIT 200", font=f, fill=0)
    g.text((tx + 25, ty + 90), "1ST AND 2ND STAGE COMPRESSION K-201", font=fb, fill=0)
    g.text((tx + 25, ty + 160), "DWG No. PID-200-001   SHEET 1 OF 1   REV 2", font=f, fill=0)
    g.text((tx + 25, ty + 210), "FICTIONAL TEST DRAWING - NOT FOR CONSTRUCTION", font=fs, fill=0)
    g.text((80, H - 380), "NOTES", font=fb, fill=0)
    for i, n in enumerate(["1. ALL INSTRUMENT TAGS ARE PREFIXED WITH AREA No. 200 (e.g. PT 2001 = 200-PT-2001).",
                           "2. ITEMS IN CLOUDS MARKED HOLD ARE PENDING VENDOR DATA AND REMAIN IN SCOPE.",
                           "3. PRESSURES IN barg, TEMPERATURES IN °C."]):
        g.text((80, H - 320 + i * 40), n, font=fs, fill=0)
    # process: scrubber -> 1st stage -> cooler -> scrubber -> 2nd stage -> cooler
    eq = [("V-201", 400), ("K-201A", 1150), ("E-201", 1900), ("V-202", 2650), ("K-201B", 3400), ("E-202", 4150)]
    my = 1600
    g.line((60, my, W - 60, my), fill=0, width=6)
    for name, x in eq:
        if name.startswith("V"):
            g.rounded_rectangle((x - 120, my - 330, x + 120, my + 330), radius=110, outline=0, width=5, fill=255)
        elif name.startswith("K"):
            g.polygon([(x - 160, my - 200), (x + 160, my - 110), (x + 160, my + 110), (x - 160, my + 200)], outline=0, width=5, fill=255)
        else:
            g.ellipse((x - 150, my - 150, x + 150, my + 150), outline=0, width=5, fill=255)
            g.line((x - 150, my - 150, x + 150, my + 150), fill=0, width=3)
        text_c(g, (x, my + 380), name, fb)
    for i, ln in enumerate(['12"-PG-2001-B1A', '10"-PG-2004-D1A', '10"-PG-2007-D1A', '8"-PG-2010-E1A', '8"-PG-2013-E1A']):
        g.text((eq[i][1] + 180, my + 12), ln, font=fs, fill=0)
    # balloons: three bands above and below the main line, 6 per band
    balloons, setpoints = [], {}
    used = set()
    num = 2001
    bands = [my - 1200, my - 820, my - 460, my + 560, my + 900, my + 1240]
    r = 52
    for b, y in enumerate(bands):
        for k in range(6):
            x = 300 + k * 740 + (b % 3) * 170
            letters = LETTERS[(b * 6 + k) % len(LETTERS)]
            tag = f"{letters}-{num}"
            while tag in used:
                num += 1; tag = f"{letters}-{num}"
            used.add(tag)
            balloons.append((letters, str(num), x, y))
            num += 1
    sp_texts = {}
    for i, (letters, n, x, y) in enumerate(balloons):
        if letters in ("PT", "TT", "LT", "PDT", "VT", "PIT", "FT") and i % 2 == 0:
            if letters in ("PT", "PIT"):
                sps = [("PAH", 10 + i * 0.5), ("PAHH", 12 + i * 0.5)]
                u = "barg"
            elif letters == "TT":
                sps = [("TAH", 120 + i)]; u = "°C"
            elif letters == "LT":
                sps = [("LAH", 900 + i * 10), ("LAL", 200)]; u = "mm"
            elif letters == "PDT":
                sps = [("PDAH", 0.5)]; u = "bar"
            elif letters == "FT":
                sps = [("FAL", 2000 + i * 100)]; u = "Sm3/h"
            else:
                sps = [("VAH", 7.1), ("VAHH", 11.2)]; u = "mm/s"
            sp_texts[(letters, n)] = [(a, round(v, 1), u) for a, v in sps]
    deleted = {balloons[7][:2], balloons[26][:2]}
    hold = {balloons[15][:2]}
    for letters, n, x, y in balloons:
        g.ellipse((x - r, y - r, x + r, y + r), outline=0, width=4, fill=255)
        if (letters, n) in (balloons[3][:2], balloons[20][:2], balloons[31][:2]):
            g.line((x - r, y, x + r, y), fill=0, width=3)  # control room
        text_c(g, (x, y - 16), letters, f); text_c(g, (x, y + 18), n, f)
        y2 = my - 60 if y < my else my + 60
        step = 18 if y < my else -18
        for yy in range(y + (r if y < my else -r), y2, step):
            g.line((x, yy, x, yy + step // 2), fill=0, width=3)
        sy = y - r
        for a, v, u in sp_texts.get((letters, n), []):
            g.text((x + r + 12, sy), f"{a} {v:g} {u}", font=fs, fill=0); sy += 28
        if (letters, n) in deleted:
            g.line((x - r - 12, y - r - 12, x + r + 12, y + r + 12), fill=0, width=4)
            g.line((x - r - 12, y + r + 12, x + r + 12, y - r - 12), fill=0, width=4)
            g.text((x - r, y + r + 14), "DELETED REV 2", font=fs, fill=0)
        if (letters, n) in hold:
            g.text((x - r, y + r + 14), "HOLD", font=fb, fill=0)
            g.rectangle((x - r - 30, y - r - 30, x + r + 30, y + r + 60), outline=0, width=2)
    # printed small and scanned: half size, speckle, JPEG
    sw, sh = int(W * scale), int(H * scale)
    small = img.resize((sw, sh), Image.LANCZOS)
    px = small.load()
    for _ in range(int(25000 * (scale / 0.5) ** 2)):
        px[random.randrange(sw), random.randrange(sh)] = random.choice((80, 140, 190))
    buf = io.BytesIO(); small.save(buf, "JPEG", quality=40)
    out = Image.open(buf).convert("L"); out.save(path)
    tags = []
    for letters, n, x, y in balloons:
        if (letters, n) in deleted:
            continue
        tags.append({"tag": f"200-{letters}-{n}",
                     "setpoints": {a: v for a, v, u in sp_texts.get((letters, n), [])}})
    return out, tags, [f"200-{a}-{b}" for a, b in deleted]


def sweep(truth, tags, deleted):
    """Tier 3: the dense sheet printed smaller and smaller, to find where reading breaks."""
    truth["pids"] = [p for p in truth["pids"] if p.get("tier") != 3]
    for pct in (35, 25):
        fn = f"PID-200-001-s{pct}.png"
        dense_pid(HERE / "pids" / fn, scale=pct / 100)
        truth["pids"].append(dict(file=fn, tier=3, scale=pct, tiles=[], tags=tags, must_not_report=deleted))


def main():
    truth = json.loads((HERE / "truth.json").read_text())
    for d in truth["datasheets"]:
        d.setdefault("tier", 1)
    for p in truth["pids"]:
        p.setdefault("tier", 1)
    truth["datasheets_multi"] = []
    multi_pdf(HERE / "datasheets" / "DS-20-200-PT-2001-2004.pdf")
    multi_scan(HERE / "datasheets" / "DS-21-200-PT-2001-2004-fax.pdf")
    for fn, trap in [("DS-20-200-PT-2001-2004.pdf", "four tags in columns; ditto marks; units in the row header; sensor URL row; old range in a footnote"),
                     ("DS-21-200-PT-2001-2004-fax.pdf", "the same sheet as a fax: ~100 dpi, 1-bit, skewed, speckled, JPEG")]:
        truth["datasheets_multi"].append(dict(file=fn, tier=2, trap=trap, records=TRUTH))
    img, tags, deleted = dense_pid(HERE / "pids" / "PID-200-001.png")
    ts = tiles(img, "PID-200-001.png")
    truth["pids"] = [p for p in truth["pids"] if p["file"] != "PID-200-001.png"]
    truth["pids"].append(dict(file="PID-200-001.png", tier=2, tiles=ts, tags=tags, must_not_report=deleted))
    sweep(truth, tags, deleted)
    (HERE / "truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False))
    print(f"tier 2: 2 multi-tag datasheets (4 tags each), dense P&ID with {len(tags)} instruments, "
          f"{sum(len(t['setpoints']) for t in tags)} settings, {len(deleted)} deleted")


def sweep_only():
    """Add tier 3 without regenerating tiers 1 and 2."""
    truth = json.loads((HERE / "truth.json").read_text())
    base = next(p for p in truth["pids"] if p["file"] == "PID-200-001.png")
    random.seed(23)
    sweep(truth, base["tags"], base["must_not_report"])
    (HERE / "truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False))
    print("tier 3: PID-200-001 at 35 % and 25 % scale")


if __name__ == "__main__":
    import sys
    sweep_only() if "--sweep-only" in sys.argv else main()

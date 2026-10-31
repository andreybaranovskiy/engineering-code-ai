"""Build the synthetic test set: 12 vendor datasheets (PDF) and 2 P&ID sheets (PNG), plus the answer key.

Everything here is fictional: the inlet separator from article 01, invented vendors, invented values.
Each document carries the kind of trap real documents carry; the trap is listed next to it in truth.json.

Needs reportlab and Pillow (pip install reportlab pillow). The generated files are committed, so you only
need this script if you want to change the test set.
"""
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
pdfmetrics.registerFont(TTFont("DV", FONT))
pdfmetrics.registerFont(TTFont("DVB", FONT_B))
random.seed(7)

# ---------------------------------------------------------------- datasheets
# Each entry: what is printed on the sheet, and what the right answer is.
# truth values may be a list of acceptable spellings; None means "the document does not give it".
DATASHEETS = [
    dict(file="DS-01-100-PT-1001.pdf", layout="A", tag="100-PT-1001", service="Inlet separator pressure",
         rows=[("Calibrated range", "0 to 10 barg"), ("Output signal", "4-20 mA HART"),
               ("Hazardous area", "Ex ia IIC T4 Ga"), ("Process connection", '1/2" NPT F'),
               ("Wetted parts", "SS316L")],
         truth=dict(lrv=0, urv=10, units="barg", output_signal="4-20 mA HART", ex_protection="Ex ia IIC T4 Ga",
                    process_connection='1/2" NPT F', wetted_material="SS316L"),
         trap="none: the control sheet"),
    dict(file="DS-02-100-PT-1002.pdf", layout="B", tag="100-PT-1002", service="Inlet separator pressure (trip)",
         rows=[("Sensor limits (URL)", "-1 ... 40 bar"), ("Calibrated range", "0 ... 10 barg"),
               ("Output", "4-20 mA HART, SIL 2"), ("Ex protection", "Ex ia IIC T4 Ga"),
               ("Process connection", '1/2" NPT F'), ("Wetted material", "Hastelloy C276")],
         truth=dict(lrv=0, urv=10, units="barg", output_signal=["4-20 mA HART", "4-20 mA HART, SIL 2"],
                    ex_protection="Ex ia IIC T4 Ga", process_connection='1/2" NPT F',
                    wetted_material=["Hastelloy C276", "Hastelloy C-276"]),
         trap="sensor limits (-1...40 bar) printed above the calibrated range"),
    dict(file="DS-03-100-LT-1003.pdf", layout="A", tag="100-LT-1003", service="Inlet separator level",
         rows=[("Measuring principle", "Guided wave radar"), ("Probe length", "2000 mm"),
               ("Calibrated range", "0 to 1500 mm above bottom reference"), ("Output signal", "4-20 mA HART"),
               ("Hazardous area", "Ex d IIC T6 Gb"), ("Process connection", '2" ASME B16.5 Cl.300 RF'),
               ("Wetted parts", "SS316L / PTFE")],
         truth=dict(lrv=0, urv=1500, units="mm", output_signal="4-20 mA HART", ex_protection="Ex d IIC T6 Gb",
                    process_connection='2" ASME B16.5 Cl.300 RF', wetted_material=["SS316L / PTFE", "SS316L/PTFE"]),
         trap="probe length 2000 mm next to the 1500 mm range"),
    dict(file="DS-04-100-LT-1004.pdf", layout="C", tag="100-LT-1004", service="Inlet separator level (trip)",
         rows=[("Measuring principle", "Guided wave radar"), ("Calibrated range", "0 to 1500 mm"),
               ("Output signal", "4-20 mA HART"), ("Hazardous area", "Ex ia IIC T4 Ga"),
               ("Process connection", '2" ASME B16.5 Cl.300 RF'), ("Wetted parts", "SS316L")],
         truth=dict(lrv=0, urv=1500, units="mm", output_signal="4-20 mA HART", ex_protection="Ex ia IIC T4 Ga",
                    process_connection='2" ASME B16.5 Cl.300 RF', wetted_material="SS316L"),
         trap="scanned page: no text layer, slight skew and noise"),
    dict(file="DS-05-100-FT-1005.pdf", layout="B", tag="100-FT-1005", service="Gas outlet flow",
         rows=[("Meter type", "Ultrasonic, 4-path"), ("Calibrated range", "STRIKE:0 ... 40 000 Sm³/h|0 ... 50 000 Sm³/h  (Rev B)"),
               ("Output", "4-20 mA HART"), ("Ex protection", "Ex d IIC T4 Gb"),
               ("Process connection", '8" ASME B16.5 Cl.300 RF'), ("Wetted material", "Duplex 2205")],
         truth=dict(lrv=0, urv=50000, units="Sm3/h", output_signal="4-20 mA HART", ex_protection="Ex d IIC T4 Gb",
                    process_connection='8" ASME B16.5 Cl.300 RF', wetted_material="Duplex 2205"),
         trap="Rev A range struck through but still in the text layer; Rev B value beside it"),
    dict(file="DS-06-100-TT-1006.pdf", layout="A", tag="100-TT-1006", service="Gas outlet temperature",
         rows=[("Element", "Pt100, 4-wire, class A"), ("Ambient temperature", "-40 to +85 °C"),
               ("Calibrated range", "-20 to 120 °C"), ("Output signal", "4-20 mA HART"),
               ("Hazardous area", "Ex d IIC T6 Gb"), ("Process connection", '1" ASME B16.5 Cl.300 RF'),
               ("Thermowell material", "SS316")],
         truth=dict(lrv=-20, urv=120, units="degC", output_signal="4-20 mA HART", ex_protection="Ex d IIC T6 Gb",
                    process_connection='1" ASME B16.5 Cl.300 RF', wetted_material="SS316"),
         trap="ambient temperature range printed above the calibrated range"),
    dict(file="DS-07-100-PDT-1007.pdf", layout="B", tag="100-PDT-1007", service="Filter differential pressure",
         rows=[("Calibrated range", "0 ... 200 kPa"), ("Static pressure rating", "250 bar"),
               ("Output", "4-20 mA HART"), ("Ex protection", "Ex ia IIC T4 Ga"),
               ("Process connection", '1/4" NPT F'), ("Wetted material", "SS316L")],
         truth=dict(lrv=0, urv=200, units="kPa", output_signal="4-20 mA HART", ex_protection="Ex ia IIC T4 Ga",
                    process_connection='1/4" NPT F', wetted_material="SS316L"),
         trap="range in kPa; the index holds it as 0-2 bar"),
    dict(file="DS-08-100-AT-1010.pdf", layout="C", tag="100-AT-1010", service="Gas H2S analyser",
         rows=[("Sensor", "Electrochemical, H2S"), ("Calibrated range", "0 to 50 ppm H2S"),
               ("Output signal", "4-20 mA"), ("Hazardous area", "Ex d IIC T4 Gb"),
               ("Process connection", '3/4" NPT M'), ("Wetted parts", "SS316")],
         truth=dict(lrv=0, urv=50, units="ppm", output_signal="4-20 mA", ex_protection="Ex d IIC T4 Gb",
                    process_connection='3/4" NPT M', wetted_material="SS316"),
         trap="scanned page; output has no HART, unlike its neighbours"),
    dict(file="DS-09-100-PT-1011.pdf", layout="A", tag="100-PT-1011", service="Condensate pump discharge",
         rows=[("Calibrated range", "0 to 40 barg"), ("Output signal", "4-20 mA HART"),
               ("Hazardous area", "Ex ia IIC T4 Ga"), ("Process connection", '1/2" NPT F'),
               ("Wetted parts", "SS316L")],
         truth=dict(lrv=0, urv=40, units="barg", output_signal="4-20 mA HART", ex_protection="Ex ia IIC T4 Ga",
                    process_connection='1/2" NPT F', wetted_material="SS316L"),
         trap="a real discrepancy: the index says 0-25 barg; the datasheet is right"),
    dict(file="DS-10-100-PT-1012.pdf", layout="B", tag="100-PT-1012", service="Fuel gas pressure",
         rows=[("Messbereich / Measuring range", "0,0 ... 16,0 bar g"), ("Max. Betriebsdruck / Max. working pressure", "100 bar"),
               ("Ausgang / Output", "4-20 mA HART"), ("Ex-Schutz / Ex protection", "Ex ia IIC T4 Ga"),
               ("Prozessanschluss / Process connection", "G 1/2 B"), ("Werkstoff / Wetted material", "AISI 316L (1.4404)")],
         truth=dict(lrv=0, urv=16, units="barg", output_signal="4-20 mA HART", ex_protection="Ex ia IIC T4 Ga",
                    process_connection="G 1/2 B", wetted_material=["AISI 316L (1.4404)", "AISI 316L", "316L (1.4404)", "1.4404"]),
         trap="German/English sheet with decimal commas; tag is PT1012 in the index"),
    dict(file="DS-11-100-PT-1013.pdf", layout="C", tag="100-PT-1013", service="Separator inlet pressure",
         rows=[("Calibrated range", "0 to 10 barg"), ("Output signal", "4-20 mA HART"),
               ("Hazardous area", "Ex ia IIC T4 Ga"), ("Process connection", '1/2" NPT F'),
               ("Wetted parts", "SS316L")],
         truth=dict(lrv=0, urv=10, units="barg", output_signal="4-20 mA HART", ex_protection="Ex ia IIC T4 Ga",
                    process_connection='1/2" NPT F', wetted_material="SS316L"),
         trap="scanned page; the tag is not in the instrument index"),
    dict(file="DS-12-100-FT-1015.pdf", layout="A", tag="100-FT-1015", service="Fuel gas flow",
         rows=[("Meter type", "Vortex"), ("Calibrated range", "TBC (Process) Sm³/h"), ("Output signal", "4-20 mA HART"),
               ("Hazardous area", "Ex d IIC T4 Gb"), ("Process connection", '4" ASME B16.5 Cl.300 RF'),
               ("Wetted parts", "SS316L")],
         truth=dict(lrv=None, urv=None, units="Sm3/h", output_signal="4-20 mA HART", ex_protection="Ex d IIC T4 Gb",
                    process_connection='4" ASME B16.5 Cl.300 RF', wetted_material="SS316L"),
         trap="range not yet known (TBC); the right answer is no number at all"),
]

VENDORS = {"A": ("NORVALE INSTRUMENTS", "Instrument Data Sheet", "Form ID-01"),
           "B": ("Kessler Messtechnik GmbH", "Order confirmation / technical data", "KM-TD"),
           "C": ("ARGENT PROCESS CONTROLS", "DATA SHEET", "APC-DS")}

COMMON = [("Project", "Inlet Separation Facility (fictional)"), ("Client", "Example Energy Co."),
          ("Quantity", "1"), ("Enclosure", "IP66 / IP67"), ("Power supply", "Loop powered, 10.5 - 42 V DC"),
          ("Ambient design", "Desert, 55 °C max, 100 % RH")]


def ds_pdf(d):
    """Layouts A and B: real PDFs with a text layer."""
    path = HERE / "datasheets" / d["file"]
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setAuthor("Andrey Baranovskiy")
    c.setTitle(f"Datasheet {d['tag']} (fictional test document)")
    w, h = A4
    vendor, title, form = VENDORS[d["layout"]]
    if d["layout"] == "A":
        c.setFont("DVB", 15); c.drawString(40, h - 55, vendor)
        c.setFont("DV", 10); c.drawString(40, h - 72, f"{title}  ·  {form}  ·  Rev 0")
        c.rect(40, h - 140, w - 80, 55)
        c.setFont("DV", 9)
        c.drawString(48, h - 102, f"Tag number:  {d['tag']}")
        c.drawString(48, h - 118, f"Service:  {d['service']}")
        c.drawString(330, h - 102, "Doc no:  ISF-100-IN-DS-%s" % d["file"][3:5])
        c.drawString(330, h - 118, "Line / equipment:  V-100")
        y = h - 170
        rows = COMMON[:2] + d["rows"] + COMMON[2:]
        for i, (k, v) in enumerate(rows):
            c.rect(40, y - 6, 200, 20); c.rect(240, y - 6, w - 280, 20)
            c.setFont("DV", 9); c.drawString(46, y, f"{i + 1:>2}  {k}")
            c.drawString(246, y, v)
            y -= 20
    else:  # B: vendor order confirmation, key/value, units style of a German vendor
        c.setFillGray(0.2); c.rect(0, h - 70, w, 70, fill=1, stroke=0); c.setFillGray(1)
        c.setFont("DVB", 16); c.drawString(40, h - 42, vendor)
        c.setFont("DV", 9); c.drawString(40, h - 58, title)
        c.setFillGray(0)
        c.setFont("DV", 9)
        c.drawString(40, h - 95, f"Pos. 10   Kunden-TAG / customer tag: {d['tag']}")
        c.drawString(40, h - 110, f"Messstelle / service: {d['service']}")
        c.drawString(40, h - 125, f"Bestell-Nr. / order no.: 4711-{d['file'][3:5]}-0815   Rev. B")
        y = h - 160
        rows = d["rows"] + COMMON[2:]
        for k, v in rows:
            c.setFont("DVB", 9); c.drawString(40, y, k)
            c.setFont("DV", 9)
            if v.startswith("STRIKE:"):
                old, new = v[7:].split("|")
                c.drawString(300, y, old)
                tw = pdfmetrics.stringWidth(old, "DV", 9)
                c.setLineWidth(0.8); c.line(298, y + 3, 302 + tw, y + 3)
                c.drawString(310 + tw, y, new)
            else:
                c.drawString(300, y, v)
            c.setLineWidth(0.3); c.line(40, y - 5, w - 40, y - 5)
            y -= 19
        c.setFont("DV", 7.5)
        c.drawString(40, 60, "Rev. B: calibrated range changed on customer request. Supersedes Rev. A.")
    c.setFont("DV", 7); c.drawString(40, 30, "Fictional test document for 'Engineering + Code + AI', article 02. Not a real product.")
    c.showPage(); c.save()


def ds_scan(d):
    """Layout C: drawn as an image, skewed and noised, saved as an image-only PDF (no text layer)."""
    W, H = 1240, 1754  # A4 at 150 dpi
    img = Image.new("L", (W, H), 255)
    g = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 21); fb = ImageFont.truetype(FONT_B, 30)
    vendor, title, form = VENDORS["C"]
    g.text((80, 90), vendor, font=fb, fill=0)
    g.text((80, 135), f"{title}   {form}   REV 1", font=f, fill=0)
    g.rectangle((80, 190, W - 80, 290), outline=0, width=2)
    g.text((95, 205), f"TAG No. {d['tag']}", font=f, fill=0)
    g.text((95, 245), f"SERVICE  {d['service'].upper()}", font=f, fill=0)
    y = 330
    for k, v in COMMON[:2] + d["rows"] + COMMON[2:]:
        g.rectangle((80, y, 520, y + 42), outline=0, width=1)
        g.rectangle((520, y, W - 80, y + 42), outline=0, width=1)
        g.text((92, y + 9), k.upper(), font=f, fill=0)
        g.text((532, y + 9), v, font=f, fill=0)
        y += 42
    g.text((80, H - 90), "Fictional test document for 'Engineering + Code + AI', article 02.", font=ImageFont.truetype(FONT, 15), fill=0)
    img = img.rotate(random.uniform(-1.2, 1.2), resample=Image.BICUBIC, fillcolor=250, expand=False)
    px = img.load()
    for _ in range(9000):  # speckle
        x, yy = random.randrange(W), random.randrange(H)
        px[x, yy] = random.choice((0, 90, 160))
    img = img.filter(ImageFilter.GaussianBlur(0.7))
    img = img.point(lambda v: min(255, int(v * 0.93 + 14)))  # grey paper
    img.save(HERE / "datasheets" / d["file"], "PDF", resolution=150, author="Andrey Baranovskiy",
             title=f"Datasheet {d['tag']} (fictional test document, scanned)")


# ---------------------------------------------------------------- P&IDs
# Balloons: (letters, number, x, y, kind, setpoint lines). kind: "field", "dcs" (line through), "shared" (circle in square)
PID1 = dict(file="PID-100-001.png", title="INLET SEPARATOR V-100", sheet="PID-100-001", balloons=[
    ("PT", "1001", 1180, 520, "field", ["PAH 8.0 barg", "PAL 2.0 barg"]),
    ("PIC", "1001", 1180, 300, "shared", []),
    ("PV", "1001", 1700, 640, "valve", []),
    ("PT", "1002", 1450, 520, "field", ["PAHH 9.5 barg"]),
    ("LT", "1003", 720, 860, "field", ["LAH 1200 mm", "LAL 300 mm"]),
    ("LIC", "1003", 720, 640, "shared", []),
    ("LV", "1003", 1600, 1600, "valve", []),
    ("LT", "1004", 720, 1400, "field", ["LAHH 1400 mm", "LALL 100 mm"]),
    ("FT", "1005", 2100, 520, "field", ["FAH 45000 Sm3/h"]),
    ("TT", "1006", 2420, 520, "field", ["TAH 95 °C"]),
    ("PDT", "1007", 2750, 520, "field", ["PDAH 1.5 bar"]),
    ("AT", "1010", 2950, 760, "field", ["AAH 10 ppm", "AAHH 20 ppm"]),
    ("XV", "1008", 300, 1150, "valve", []),
    ("ZSO", "1008", 170, 830, "field", []),
    ("ZSC", "1008", 430, 830, "field", []),
], deleted=[("TI", "1018", 2300, 950)])

PID2 = dict(file="PID-100-002.png", title="CONDENSATE PUMPS AND FUEL GAS", sheet="PID-100-002", balloons=[
    ("LT", "1019", 600, 760, "field", ["LAH 800 mm", "LAL 200 mm"]),
    ("LIC", "1019", 600, 540, "shared", []),
    ("LV", "1019", 1350, 1300, "valve", []),
    ("LG", "1020", 560, 1230, "local", []),
    ("PT", "1011", 1650, 980, "field", ["PAH 20 barg"]),
    ("PI", "1014", 1900, 1180, "local", []),
    ("TI", "1021", 1050, 1180, "local", []),
    ("PT", "1012", 2350, 520, "field", ["PAH 12 barg"]),
    ("PCV", "1012", 2650, 640, "valve", []),
    ("PSV", "1023", 2950, 470, "valve", ["SET 16 barg"]),
], deleted=[])


def text_c(g, xy, s, font, fill=0):
    x, y = xy
    l, t, r, b = g.textbbox((0, 0), s, font=font)
    g.text((x - (r - l) / 2, y - (b - t) / 2 - t), s, font=font, fill=fill)


def pid_png(p):
    W, H = 3307, 2339  # A3 at 200 dpi
    img = Image.new("L", (W, H), 255)
    g = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 22); fs = ImageFont.truetype(FONT, 18); fb = ImageFont.truetype(FONT_B, 28)
    fl = ImageFont.truetype(FONT, 20)
    g.rectangle((40, 40, W - 40, H - 40), outline=0, width=4)
    # title block
    tx, ty = W - 1000, H - 300
    g.rectangle((tx, ty, W - 40, H - 40), outline=0, width=3)
    g.line((tx, ty + 70, W - 40, ty + 70), fill=0, width=2)
    g.text((tx + 20, ty + 18), "EXAMPLE ENERGY CO.  -  INLET SEPARATION FACILITY", font=f, fill=0)
    g.text((tx + 20, ty + 90), "PIPING & INSTRUMENTATION DIAGRAM", font=fs, fill=0)
    g.text((tx + 20, ty + 125), p["title"], font=fb, fill=0)
    g.text((tx + 20, ty + 185), f"DWG No. {p['sheet']}     SHEET 1 OF 1     REV B", font=f, fill=0)
    g.text((tx + 20, ty + 225), "FICTIONAL TEST DRAWING - NOT FOR CONSTRUCTION", font=fs, fill=0)
    # notes
    nx, ny = 80, H - 300
    g.text((nx, ny), "NOTES", font=fb, fill=0)
    for i, n in enumerate(["1. ALL INSTRUMENT TAGS ARE PREFIXED WITH AREA No. 100 (e.g. PT 1001 = 100-PT-1001).",
                           "2. ALARM AND TRIP SETTINGS SHOWN ARE PRELIMINARY; SEE ALARM & TRIP SCHEDULE.",
                           "3. DIMENSIONS IN mm UNLESS NOTED.  PRESSURES IN barg."]):
        g.text((nx, ny + 45 + i * 34), n, font=fs, fill=0)

    if p is PID1:
        # vessel
        g.rounded_rectangle((900, 1000, 2000, 1300), radius=150, outline=0, width=4)
        text_c(g, (1450, 1150), "V-100  INLET SEPARATOR", fb)
        text_c(g, (1450, 1195), "3000 ID x 9000 T/T", fs)
        # inlet line with XV
        g.line((80, 1150, 900, 1150), fill=0, width=4)
        g.text((90, 1160), '10"-P-1001-A3B', font=fl, fill=0)
        g.polygon([(270, 1130), (270, 1170), (330, 1130), (330, 1170)], outline=0, width=3)
        # gas outlet
        g.line((1450, 1000, 1450, 640), fill=0, width=4); g.line((1450, 640, 3200, 640), fill=0, width=4)
        g.text((2950, 600), "TO FLARE / EXPORT", font=fs, fill=0)
        g.text((1470, 900), '8"-PG-1002-A3B', font=fl, fill=0)
        g.polygon([(1670, 620), (1670, 660), (1730, 620), (1730, 660)], outline=0, width=3)
        # liquid outlet
        g.line((1450, 1300, 1450, 1600), fill=0, width=4); g.line((1450, 1600, 3200, 1600), fill=0, width=4)
        g.text((2700, 1610), '4"-P-1003-A3B  TO PID-100-002', font=fl, fill=0)
        g.polygon([(1570, 1580), (1570, 1620), (1630, 1580), (1630, 1620)], outline=0, width=3)
        # level bridle
        g.line((850, 1050, 900, 1050), fill=0, width=3); g.line((850, 1250, 900, 1250), fill=0, width=3)
        g.line((850, 1050, 850, 1250), fill=0, width=3)
    else:
        g.rounded_rectangle((700, 900, 1100, 1100), radius=100, outline=0, width=4)
        text_c(g, (900, 1000), "V-101 CONDENSATE DRUM", f)
        g.line((80, 1000, 700, 1000), fill=0, width=4); g.text((90, 1010), '4"-P-1003-A3B FROM PID-100-001', font=fl, fill=0)
        g.line((900, 1100, 900, 1300), fill=0, width=4); g.line((900, 1300, 2000, 1300), fill=0, width=4)
        g.ellipse((1550, 1240, 1650, 1360), outline=0, width=4); g.text((1540, 1380), "P-101A/B", font=f, fill=0)
        g.line((2000, 1300, 3200, 1300), fill=0, width=4); g.text((2600, 1310), '3"-P-1010-A3B  TO EXPORT', font=fl, fill=0)
        g.polygon([(1320, 1280), (1320, 1320), (1380, 1280), (1380, 1320)], outline=0, width=3)
        g.line((2000, 640, 3200, 640), fill=0, width=4); g.text((2010, 650), '2"-FG-1012-B1A  FUEL GAS', font=fl, fill=0)
        g.polygon([(2620, 620), (2620, 660), (2680, 620), (2680, 660)], outline=0, width=3)
        g.line((2950, 640, 2950, 450), fill=0, width=3)

    r = 48
    for letters, num, x, y, kind, sps in p["balloons"]:
        if kind == "valve":
            # valve tag in a balloon above the valve symbol
            g.ellipse((x - r, y - 160 - r, x + r, y - 160 + r), outline=0, width=3)
            text_c(g, (x, y - 172), letters, f); text_c(g, (x, y - 145), num, f)
            g.line((x, y - 160 + r, x, y - 20), fill=0, width=2)
            sy = y - 160 - r - 30
            for s in sps:
                g.text((x + r + 10, sy), s, font=fs, fill=0); sy += 24
            continue
        if kind == "shared":
            g.rectangle((x - r, y - r, x + r, y + r), outline=0, width=3)
        g.ellipse((x - r, y - r, x + r, y + r), outline=0, width=3)
        if kind in ("shared", "dcs"):
            g.line((x - r, y, x + r, y), fill=0, width=2)
        text_c(g, (x, y - 14), letters, f); text_c(g, (x, y + 15), num, f)
        # dashed signal line down to the process
        for yy in range(y + r, min(y + r + 110, H), 14):
            g.line((x, yy, x, yy + 7), fill=0, width=2)
        sy = y - r
        for s in sps:
            g.text((x + r + 10, sy), s, font=fs, fill=0); sy += 24
    for letters, num, x, y in p["deleted"]:
        g.ellipse((x - r, y - r, x + r, y + r), outline=0, width=3)
        text_c(g, (x, y - 14), letters, f); text_c(g, (x, y + 15), num, f)
        g.line((x - r - 10, y - r - 10, x + r + 10, y + r + 10), fill=0, width=3)
        g.line((x - r - 10, y + r + 10, x + r + 10, y - r - 10), fill=0, width=3)
        # revision cloud
        for a in range(0, 360, 24):
            cx = x + 95 * math.cos(math.radians(a)); cy = y + 95 * math.sin(math.radians(a))
            g.arc((cx - 22, cy - 22, cx + 22, cy + 22), 0, 360, fill=0, width=2)
        g.text((x + 110, y - 10), "DELETED (REV B)", font=fs, fill=0)
        g.polygon([(x + 110, y + 40), (x + 135, y + 40), (x + 122, y + 18)], outline=0, width=2)
        g.text((x + 118, y + 22), "B", font=ImageFont.truetype(FONT, 12), fill=0)
    img.save(HERE / "pids" / p["file"])
    return img


def tiles(img, name, n=2, overlap=0.12):
    """Cut a sheet into n x n overlapping tiles; small text is easier to read at tile scale."""
    W, H = img.size
    tw, th = int(W / n * (1 + overlap)), int(H / n * (1 + overlap))
    out = []
    for i in range(n):
        for j in range(n):
            x0 = min(int(i * W / n), W - tw); y0 = min(int(j * H / n), H - th)
            fn = f"{name[:-4]}-tile{j}{i}.png"
            img.crop((x0, y0, x0 + tw, y0 + th)).save(HERE / "pids" / fn)
            out.append(fn)
    return out


def main():
    truth = {"datasheets": [], "pids": []}
    for d in DATASHEETS:
        (ds_scan if d["layout"] == "C" else ds_pdf)(d)
        truth["datasheets"].append(dict(file=d["file"], layout=d["layout"], trap=d["trap"],
                                        fields=dict(tag=d["tag"], **d["truth"])))
    for p in (PID1, PID2):
        img = pid_png(p)
        ts = tiles(img, p["file"])
        tags = []
        for letters, num, *_rest in p["balloons"]:
            sps = _rest[-1]
            tag = {"tag": f"100-{letters}-{num}", "setpoints": {}}
            for s in sps:
                k, v, *u = s.split()
                tag["setpoints"][k] = float(v)
            tags.append(tag)
        truth["pids"].append(dict(file=p["file"], tiles=ts, tags=tags,
                                  must_not_report=[f"100-{a}-{b}" for a, b, *_ in p["deleted"]]))
    (HERE / "truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False))
    print(f"{len(truth['datasheets'])} datasheets, {len(truth['pids'])} P&IDs, "
          f"{sum(len(p['tags']) for p in truth['pids'])} P&ID tags")


if __name__ == "__main__":
    main()

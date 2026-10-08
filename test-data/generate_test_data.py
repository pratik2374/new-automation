"""
Generate FAKE, look-alike NJ prelim-state application packets for pipeline testing.

All people, addresses, companies, account numbers and signatures are invented.
Layouts mimic the document types seen in the walkthrough videos:
  combined pack (utility form + ADI form), DocuSign-style audit trail,
  electric bill (clean PDF or phone-photo scan), 50-page PPA contract,
  signature forms, 11x17 design set, roof-summary site report.

Run:  python generate_test_data.py
Output: ./jobs/<job_id>/raw/*   (what the specialist downloads)
        ./jobs/<job_id>/expected/*  (the 5 finished docs + ground-truth JSON)
"""
import io
import json
import os
import random
import shutil

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "jobs")
W, H = letter
TABLOID = (1224, 792)  # 17x11 landscape in points

SCRIPT_FONT = "SigScript"
for cand in (r"C:\Windows\Fonts\segoesc.ttf", r"C:\Windows\Fonts\Inkfree.ttf"):
    if os.path.exists(cand):
        pdfmetrics.registerFont(TTFont(SCRIPT_FONT, cand))
        break
else:
    SCRIPT_FONT = "Helvetica-Oblique"

CYAN = HexColor("#bfe8f5")
NAVY = HexColor("#1d3557")
GREY = HexColor("#555555")
INK = HexColor("#1b3a8c")

# ----------------------------------------------------------------------------
# Static fictional parties
# ----------------------------------------------------------------------------
INSTALLER = dict(
    name="Sunridge Solar LLC", contact="Dana Whitcomb", addr="900 Harbor Mill Road",
    city="Brindle", state="NJ", zip="07000", phone="(732) 555-0142",
    dept_email="nj.incentives@sunridge-solar.example",
    cust_service_email="customer.care@sunridge-solar.example",
    license="13VH-0099-4417", license_exp="03/31/2027",
)
FINANCE = dict(
    name="HarborLight Solar Finance LLC dba LightHarbor", short="LightHarbor",
    contact="Marcus Ellery", addr="55 Lantern Street, Suite 300", city="Charlotte",
    state="NC", zip="28203", phone="(855) 555-0188",
    old_email="utility@lightharbor.example",  # outdated in templates
    new_email="nj.incentives@lightharbor.example",
)
PANEL = dict(mfr="NOVASUN", model="NS DUO BLK ML-G10 410", watts=410)
INVERTER = dict(mfr="InverTech", model="IT7600H-US", qty=1, ac_kw=7.6, ac_a=32, eff=0.97)

LOREM = [
    "The Parties agree that the System shall remain the property of the Owner for the duration of the Term.",
    "The Customer shall provide reasonable access to the Premises for installation, inspection and maintenance.",
    "Production estimates are projections only and are not a guarantee of actual energy output.",
    "Charges are calculated per kilowatt-hour delivered by the System as measured by the production meter.",
    "Either Party may assign this Agreement to a qualified successor upon written notice to the other Party.",
    "The Owner will maintain commercially reasonable insurance covering the System throughout the Term.",
    "Any dispute arising under this Agreement shall first be addressed through good-faith negotiation.",
    "The Customer shall not alter, relocate or obstruct the System without prior written consent of the Owner.",
    "Notices required under this Agreement shall be delivered in writing to the addresses stated in the Order Form.",
    "This Agreement is governed by the laws of the State in which the Premises are located.",
    "Force majeure events excuse performance for the duration of the event and a reasonable restoration period.",
    "The Customer acknowledges receipt of the disclosure statement and the notice of cancellation rights.",
    "Taxes, fees and assessments attributable to the System are allocated as set forth in the schedule of charges.",
    "Upon expiration of the Term the Customer may renew, purchase the System at fair market value, or request removal.",
]

# ----------------------------------------------------------------------------
# Job definitions (ground truth lives here)
# ----------------------------------------------------------------------------
def roof_rows(rows):
    """rows: list of dicts for roofs; pad to 6 like the real site report."""
    out = list(rows)
    while len(out) < 6:
        out.append(None)
    return out


JOBS = {
    # 1 ---------------------------------------------------------------------
    "job01_clean": dict(
        title="Baseline: 14 panels, 2 arrays, no problems",
        customer=dict(first="Alanna", last="Whitfield", email="alanna.whitfield77@mailbox.example",
                      phone="+19735550117"),
        ebill_name="ALANNA WHITFIELD", ebill_style="clean_pdf",
        site=dict(addr="41 Sycamore Court", city="Ridgemont", state="NJ", zip="07999"),
        utility=dict(name="Meridian Electric", short="MEC", acct="70536 92000 5", meter="701175788",
                     tariff="Residential"),
        price=31450.00, kw_contract=5.740, kw_design=5.740,
        arrays_design=[
            dict(roof=1, pitch=18, az=329, access=81, tsrf=57, modules=8, util=2998, actual=2610),
            dict(roof=2, pitch=18, az=149, access=82, tsrf=79, modules=6, util=3080, actual=2717),
        ],
        sitereport_modules_override=None,
        envelope="445966AC-E889-4D1C-83CF-01AFD3793974", envelope_disclosure=None,
        sign_date="06-18-26", sign_date_long="Jun 18, 2026", audit_last_date="06/18/2026",
        adi_blank_finance_date=True, adi_blank_customer_date=False,
        chatter=["6/25/26 - No increase or decrease in system size. LR prelim state approval pending."],
        name_clarification=False,
    ),
    # 2 ---------------------------------------------------------------------
    "job02_three_arrays_name_mismatch": dict(
        title="3 arrays / 24 panels (state tool lumps them), e-bill name differs (maiden name)",
        customer=dict(first="Imogen", last="Tarrant", email="imogen.tarrant@mailbox.example",
                      phone="+19085550163"),
        ebill_name="IMOGEN HALLORAN", ebill_style="photo",
        site=dict(addr="9 Chestwood Street", city="Lakemont", state="NJ", zip="07874"),
        utility=dict(name="Garden State Power & Light", short="GSPL", acct="100 144 107 170",
                     meter="GS-4471920", tariff="Residential"),
        price=47980.00, kw_contract=9.840, kw_design=9.840,
        arrays_design=[
            dict(roof=1, pitch=22, az=281, access=72, tsrf=61, modules=9, util=3364, actual=3142),
            dict(roof=2, pitch=19, az=101, access=70, tsrf=58, modules=4, util=1796, actual=1721),
            dict(roof=3, pitch=20, az=191, access=88, tsrf=80, modules=11, util=4736, actual=4529),
        ],
        sitereport_modules_override=None,
        envelope="B2C1F7A0-31D4-4E52-9A6B-7D8E1C0F4A22", envelope_disclosure=None,
        sign_date="06-09-26", sign_date_long="Jun 9, 2026", audit_last_date="06/10/2026",
        adi_blank_finance_date=True, adi_blank_customer_date=False,
        chatter=["6/12/26 - No change in system size."],
        name_clarification=True,
    ),
    # 3 ---------------------------------------------------------------------
    "job03_defects": dict(
        title="Deliberate defects: DC mismatch, stale site report, audit date off, wrong DocuSign ID, missing date",
        customer=dict(first="Corinne", last="Delacroix", email="c.delacroix@mailbox.example",
                      phone="+18565550190"),
        ebill_name="CORINNE DELACROIX", ebill_style="photo_blur",
        site=dict(addr="302 Alder Lane", city="Pinebrook", state="NJ", zip="07058"),
        utility=dict(name="Meridian Electric", short="MEC", acct="70611 48320 9", meter="701190334",
                     tariff="Residential"),
        price=30120.00, kw_contract=6.150, kw_design=5.740,
        arrays_design=[
            dict(roof=1, pitch=25, az=180, access=90, tsrf=84, modules=8, util=3402, actual=3199),
            dict(roof=2, pitch=25, az=270, access=84, tsrf=70, modules=6, util=2540, actual=2310),
        ],
        # stale site report still shows 16 modules (2 extra on roof 2)
        sitereport_modules_override={2: 8},
        envelope="9F0E5D14-77AB-4B3C-A1D2-5E6F70819AB3",
        envelope_disclosure="1C2D3E4F-0A1B-4C5D-8E9F-A0B1C2D3E4F5",
        sign_date="06-18-26", sign_date_long="Jun 18, 2026", audit_last_date="06/15/2026",
        adi_blank_finance_date=True, adi_blank_customer_date=True,
        chatter=["6/20/26 - DC increased from 5.74 kW to 6.15 kW per change order. Designs NOT yet updated."],
        name_clarification=False,
    ),
}


def derive(job):
    d = job["arrays_design"]
    for a in d:
        a["size_kw"] = round(a["modules"] * PANEL["watts"] / 1000, 3)
    job["panels_design"] = sum(a["modules"] for a in d)
    job["kw_from_arrays"] = round(sum(a["size_kw"] for a in d), 3)
    # site report arrays (may be stale)
    sr = []
    for a in d:
        b = dict(a)
        ov = (job["sitereport_modules_override"] or {}).get(a["roof"])
        if ov:
            ratio = ov / a["modules"]
            b["modules"] = ov
            b["size_kw"] = round(ov * PANEL["watts"] / 1000, 3)
            b["util"] = int(a["util"] * ratio)
            b["actual"] = int(a["actual"] * ratio)
        sr.append(b)
    job["arrays_sitereport"] = sr
    job["full_name"] = f'{job["customer"]["first"]} {job["customer"]["last"]}'
    job["site_line"] = f'{job["site"]["addr"]}, {job["site"]["city"]}, {job["site"]["state"]} {job["site"]["zip"]}'
    return job


# ----------------------------------------------------------------------------
# Drawing helpers
# ----------------------------------------------------------------------------
def new_pdf(path, size=letter):
    return canvas.Canvas(path, pagesize=size)


def txt(c, x, y, s, font="Helvetica", size=9, color=black):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawString(x, y, s)
    c.setFillColor(black)


def para(c, x, y, s, width, font="Helvetica", size=9, leading=None, color=black):
    leading = leading or size * 1.3
    c.setFont(font, size)
    c.setFillColor(color)
    for line in simpleSplit(s, font, size, width):
        c.drawString(x, y, line)
        y -= leading
    c.setFillColor(black)
    return y


def field(c, x, y, label, value, w=200, size=9):
    """underlined fill-in field: label then value on a line"""
    txt(c, x, y + 10, label, "Helvetica", 6.5, GREY)
    c.setStrokeColor(HexColor("#999999"))
    c.line(x, y - 3, x + w, y - 3)
    if value:
        txt(c, x + 2, y, value, "Helvetica-Bold", size)


def bar(c, x, y, w, h, label):
    c.setFillColor(CYAN)
    c.rect(x, y, w, h, stroke=0, fill=1)
    c.setFillColor(black)
    txt(c, x + 4, y + 4, label, "Helvetica-Bold", 9)


def sig(c, x, y, name, color=INK, size=18, rot=3):
    c.saveState()
    c.setFillColor(color)
    c.translate(x, y)
    c.rotate(rot)
    c.setFont(SCRIPT_FONT, size)
    c.drawString(0, 0, name)
    c.restoreState()


def footer(c, left, page=None, total=None):
    c.setFont("Helvetica", 7)
    c.setFillColor(GREY)
    c.drawString(40, 24, left)
    if page:
        c.drawRightString(W - 40, 24, f"Page {page} of {total}")
    c.setFillColor(black)


def envelope_header(c, env):
    txt(c, 40, H - 24, f"DocuSign Envelope ID: {env}", "Helvetica", 7, GREY)


def bytes_to_reader(b):
    return PdfReader(io.BytesIO(b))


def build(fn, *a, **k):
    buf = io.BytesIO()
    fn(buf, *a, **k)
    return buf.getvalue()


def write_pages(path, readers_pages):
    w = PdfWriter()
    for pg in readers_pages:
        w.add_page(pg)
    with open(path, "wb") as f:
        w.write(f)


def pages_of(pdf_bytes):
    return list(bytes_to_reader(pdf_bytes).pages)


# ----------------------------------------------------------------------------
# ADI form (2 pages) -- also used (with edits) in the final packet
# ----------------------------------------------------------------------------
def adi_pdf(job, final):
    def go(buf):
        c = canvas.Canvas(buf, pagesize=letter)
        cu, s = job["customer"], job["site"]
        fin_email = FINANCE["new_email"] if final else FINANCE["old_email"]
        # --- page 1
        txt(c, 150, H - 40, "Administratively Determined Incentive (ADI) Program", "Helvetica-Bold", 12)
        txt(c, 195, H - 56, "ADI Registration Certification Form", "Helvetica-Bold", 11)
        y = H - 90
        bar(c, 40, y, W - 80, 16, "A: Premise Contact and System Location (Where will the system be installed?)")
        y -= 22
        field(c, 44, y, "First Name", cu["first"], 160); field(c, 260, y, "Last Name", cu["last"], 160); y -= 26
        field(c, 44, y, "Installation Address", s["addr"], 260); y -= 26
        field(c, 44, y, "City", s["city"], 150); field(c, 220, y, "State", s["state"], 40)
        field(c, 290, y, "Zip Code", s["zip"], 90); y -= 26
        field(c, 44, y, "Email", cu["email"], 260); y -= 34
        bar(c, 40, y, W - 80, 16, "B: Primary Contact (SREC-II Owner) (Who will be issued the NJ Certification Number?)")
        y -= 22
        field(c, 44, y, "Company Name", FINANCE["name"], 330); field(c, 400, y, "Contact Person", FINANCE["contact"], 130); y -= 26
        field(c, 44, y, "Address", FINANCE["addr"], 260); y -= 26
        field(c, 44, y, "City", FINANCE["city"], 150); field(c, 220, y, "State", FINANCE["state"], 40)
        field(c, 290, y, "Zip Code", FINANCE["zip"], 90); y -= 26
        field(c, 44, y, "Email", fin_email, 260); y -= 34
        bar(c, 40, y, W - 80, 16, "C: Solar Installer / Developer")
        y -= 22
        field(c, 44, y, "Company Name", INSTALLER["name"], 260); field(c, 330, y, "Contact Person", INSTALLER["contact"], 150); y -= 26
        field(c, 44, y, "Address", INSTALLER["addr"], 260); y -= 26
        field(c, 44, y, "City", INSTALLER["city"], 150); field(c, 220, y, "State", INSTALLER["state"], 40)
        field(c, 290, y, "Zip Code", INSTALLER["zip"], 90); y -= 26
        field(c, 44, y, "Email", INSTALLER["dept_email"], 260); y -= 34
        bar(c, 40, y, W - 80, 16, "D: Certification and Signatures")
        y -= 14
        y = para(c, 44, y, "The undersigned warrants, certifies and represents that 1) the information provided in this form is "
                 "true and correct; 2) for behind-the-meter systems the annual output will not exceed 100% of the "
                 "premise's historic annual usage; 3) the installer will provide manuals for operation and maintenance; "
                 "4) the system will be installed in accordance with all applicable rules and policies; 5) the premise "
                 "contact is the Customer of Record for the utility account; 6) permission is given to review electric "
                 "account information; 7) information may be subject to public records requests.",
                 W - 90, size=7.5)
        footer(c, "ADI Registration Certification Form - page 1 of 2")
        c.showPage()
        # --- page 2
        txt(c, 40, H - 50, "D (continued): Certification and Signatures", "Helvetica-Bold", 10)
        y = para(c, 40, H - 70, "I agree that this document and all notices and disclosures made or given relating to it may be "
                 "created, executed, delivered and retained electronically and that the electronic signatures appearing "
                 "on this document have the same legal effect as a handwritten signature. A signature verification "
                 "sheet must be submitted with this document if signatures are signed electronically. The information "
                 "provided is true and accurate to the best of my knowledge; I am aware that false statements are "
                 "subject to punishment.", W - 80, size=9)
        sy = y - 70
        cols = [(60, "Primary Contact (SREC-II Owner)", FINANCE["contact"], "Marcus Ellery",
                 "" if (job["adi_blank_finance_date"] and not final) else job["sign_date"]),
                (235, "Solar Installer/Developer", INSTALLER["contact"], INSTALLER["contact"], job["sign_date"]),
                (410, "Premise Contact (if different)", job["full_name"], job["full_name"],
                 "" if (job["adi_blank_customer_date"] and not final) else job["sign_date_long"])]
        for x, title, pname, signame, date in cols:
            txt(c, x, sy + 36, title, "Helvetica-Bold", 8.5)
            txt(c, x, sy, "Signature:", size=8)
            c.line(x + 42, sy - 2, x + 150, sy - 2)
            sig(c, x + 44, sy + 2, signame, size=15)
            txt(c, x, sy - 18, "Print Name:", size=8)
            txt(c, x + 45, sy - 18, pname if title.startswith("Primary") is False else "", "Helvetica", 9)
            if title.startswith("Primary"):
                # Real forms often miss the printed name for the finance signer
                txt(c, x + 45, sy - 18, "" if not final else "Marcus Ellery", "Helvetica", 9)
            c.line(x + 45, sy - 20, x + 150, sy - 20)
            txt(c, x, sy - 36, "Date:", size=8)
            if date:
                txt(c, x + 45, sy - 36, date, "Helvetica", 9)
            c.line(x + 45, sy - 38, x + 150, sy - 38)
        footer(c, "ADI Registration Certification Form - page 2 of 2")
        c.showPage()
        c.save()
    return build(go)


# ----------------------------------------------------------------------------
# Raw doc 1: combined pack (utility interconnection form pages + ADI + filler)
# ----------------------------------------------------------------------------
def generic_form_page(c, job, title, n, total):
    txt(c, 40, H - 50, title, "Helvetica-Bold", 13)
    cu, s = job["customer"], job["site"]
    y = H - 90
    for lab, val in [("Customer Name", job["full_name"]), ("Service Address", job["site_line"]),
                     ("Utility Account No.", job["utility"]["acct"]), ("Meter No.", job["utility"]["meter"]),
                     ("System Size (kW DC)", f'{job["kw_design"]:.3f}'), ("Installer", INSTALLER["name"])]:
        field(c, 44, y, lab, val, 400)
        y -= 30
    y -= 10
    for _ in range(8):
        y = para(c, 44, y, random.choice(LOREM), W - 90, size=9) - 6
    footer(c, "Utility interconnection application (net metering)", n, total)


def build_combined_pack(path, job):
    random.seed(11)
    adi = pages_of(adi_pdf(job, final=False))
    util = []
    for i in (1, 2):
        def go(buf, i=i):
            c = canvas.Canvas(buf, pagesize=letter)
            generic_form_page(c, job, f"Utility Interconnection Application - Part {i}", i, 6)
            c.showPage(); c.save()
        util += pages_of(build(go))
    tail = []
    for i, ttl in ((5, "Customer Authorization"), (6, "Installer Certification")):
        def go(buf, i=i, ttl=ttl):
            c = canvas.Canvas(buf, pagesize=letter)
            generic_form_page(c, job, ttl, i, 6)
            c.showPage(); c.save()
        tail += pages_of(build(go))
    write_pages(path, util + adi + tail)


# ----------------------------------------------------------------------------
# Raw doc 2: DocuSign-style audit trail ("Combined Pack_AuditTrail.pdf")
# ----------------------------------------------------------------------------
def build_audit_trail(path, job):
    m, d, y = job["audit_last_date"].split("/")
    def go(buf):
        c = canvas.Canvas(buf, pagesize=letter)
        txt(c, 40, H - 50, "Certificate of Completion", "Helvetica-Bold", 16)
        txt(c, 40, H - 70, f"Envelope Id: {job['envelope']}", size=9)
        rows = [("Subject", "Please sign: Combined Pack"), ("Source Envelope", "Document Pages: 6"),
                ("Status", "Completed"), ("Envelope Originator", FINANCE["contact"]),
                ("Time Zone", "(UTC-05:00) Eastern Time (US & Canada)")]
        yy = H - 100
        for k, v in rows:
            txt(c, 40, yy, k, "Helvetica-Bold", 9); txt(c, 190, yy, v, size=9); yy -= 16
        yy -= 14
        txt(c, 40, yy, "Record Tracking", "Helvetica-Bold", 11); yy -= 18
        signers = [(job["full_name"], job["customer"]["email"], "Sent", f"{m}/{int(d)-1 if int(d)>1 else d}/{y} 3:12 PM", "Signed", f"{m}/{d}/{y} 9:41 AM"),
                   (INSTALLER["contact"], INSTALLER["dept_email"], "Sent", f"{m}/{d}/{y} 9:42 AM", "Signed", f"{m}/{d}/{y} 10:05 AM"),
                   (FINANCE["contact"], FINANCE["new_email"], "Sent", f"{m}/{d}/{y} 10:06 AM", "Signed", f"{m}/{d}/{y} 11:30 AM")]
        for name, em, _, sent, _, signed in signers:
            txt(c, 40, yy, name, "Helvetica-Bold", 9); txt(c, 190, yy, em, size=8.5); yy -= 13
            txt(c, 60, yy, f"Sent: {sent}", size=8); txt(c, 250, yy, f"Signed: {signed}", size=8); yy -= 22
        yy -= 10
        txt(c, 40, yy, "Envelope Summary Events", "Helvetica-Bold", 11); yy -= 16
        for ev, ts in [("Envelope Sent", f"{m}/{d}/{y} 9:40 AM"), ("Certified Delivered", f"{m}/{d}/{y} 9:41 AM"),
                       ("Signing Complete", f"{m}/{d}/{y} 11:30 AM"), ("Completed", f"{m}/{d}/{y} 11:30 AM")]:
            txt(c, 40, yy, ev, size=9); txt(c, 250, yy, ts, size=9); yy -= 14
        footer(c, "Certificate generated electronically (fictional test data)")
        c.showPage(); c.save()
    write_pages(path, pages_of(build(go)))


# ----------------------------------------------------------------------------
# Raw doc 3: electric bill (clean PDF or phone photo)
# ----------------------------------------------------------------------------
def bill_image(job, blur=False):
    img = Image.new("RGB", (1000, 1300), "white")
    dr = ImageDraw.Draw(img)
    try:
        f_b = ImageFont.truetype("arialbd.ttf", 30); f = ImageFont.truetype("arial.ttf", 24); f_s = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        f_b = f = f_s = ImageFont.load_default()
    dr.rectangle([0, 0, 1000, 110], fill=(18, 61, 117))
    dr.text((40, 30), job["utility"]["name"].upper(), fill="white", font=f_b)
    dr.text((700, 40), "Billing Statement", fill="white", font=f)
    dr.text((40, 140), f"Account Number: {job['utility']['acct']}", fill="black", font=f_b)
    dr.text((40, 190), f"Meter Number: {job['utility']['meter']}", fill="black", font=f)
    dr.text((40, 240), "Billing Period: Apr 27, 2026 - May 28, 2026", fill="black", font=f)
    dr.text((40, 300), job["ebill_name"], fill="black", font=f_b)
    dr.text((40, 335), job["site"]["addr"].upper(), fill="black", font=f)
    dr.text((40, 365), f"{job['site']['city'].upper()}, {job['site']['state']} {job['site']['zip']}", fill="black", font=f)
    dr.rectangle([620, 140, 960, 330], outline=(18, 61, 117), width=3)
    dr.text((640, 160), "Amount Due", fill="black", font=f); dr.text((640, 200), "$ 187.42", fill="black", font=f_b)
    dr.text((640, 260), "Due Date: Jun 16, 2026", fill="black", font=f)
    y = 430
    for lab, v in [("Previous balance", "$ 0.00"), ("Payments received", "- $ 0.00"), ("Delivery charges", "$ 74.10"),
                   ("Supply charges", "$ 113.32"), ("Rate class", job["utility"]["tariff"]), ("Total", "$ 187.42")]:
        dr.text((60, y), lab, fill="black", font=f); dr.text((700, y), v, fill="black", font=f); y += 44
    for i in range(14):
        dr.text((40, 760 + i * 28), random.choice(LOREM)[:75], fill=(90, 90, 90), font=f_s)
    if blur:  # smudge the middle of the account number
        box = (330, 135, 430, 185)
        region = img.crop(box).filter(ImageFilter.GaussianBlur(9))
        img.paste(region, box)
    return img


def photo_effect(img, angle=2.5, blur=False):
    bg = Image.new("RGB", (1200, 1500), (68, 62, 58))
    rot = img.rotate(angle, expand=True, fillcolor=(68, 62, 58))
    rot.thumbnail((1100, 1400))
    bg.paste(rot, (50, 40))
    px = bg.load()
    rnd = random.Random(5)
    for _ in range(40000):
        x, y = rnd.randrange(bg.width), rnd.randrange(bg.height)
        r, g, b = px[x, y]; n = rnd.randint(-18, 18)
        px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))
    bg = bg.filter(ImageFilter.GaussianBlur(1.6 if blur else 0.7))
    return bg


def build_ebill(path, job):
    random.seed(21)
    style = job["ebill_style"]
    if style == "clean_pdf":
        img = bill_image(job)
    else:
        img = photo_effect(bill_image(job, blur=(style == "photo_blur")), angle=-2.2,
                           blur=(style == "photo_blur"))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=70)
    buf.seek(0)
    c = canvas.Canvas(path, pagesize=letter)
    iw, ih = img.size
    scale = min((W - 40) / iw, (H - 40) / ih)
    c.drawImage(ImageReader(buf), 20, 20, iw * scale, ih * scale)
    # invisible text layer (prototype stand-in for OCR output; real bill photos need OCR)
    acct = job["utility"]["acct"]
    if style == "photo_blur":
        parts = acct.split(" ")
        acct = parts[0][:2] + "### ##### " + parts[-1]
    t = c.beginText(30, 60)
    t.setTextRenderMode(3)
    t.setFont("Helvetica", 8)
    for line in (f"Account Number: {acct}", f"Meter Number: {job['utility']['meter']}",
                 f"Customer: {job['ebill_name']}", f"Service Address: {job['site']['addr'].upper()}, "
                 f"{job['site']['city'].upper()}, {job['site']['state']} {job['site']['zip']}",
                 f"Utility: {job['utility']['name']}", f"Rate class: {job['utility']['tariff']}"):
        t.textLine(line)
    c.drawText(t)
    c.showPage(); c.save()


# ----------------------------------------------------------------------------
# Raw doc 4: 50-page PPA contract (agreement 1-24, exhibits, p30 cancel,
# marker p42, disclosure 43-46, DocuSign certificate 47-50)
# ----------------------------------------------------------------------------
DISCLOSURE_FIRST, DISCLOSURE_LAST = 43, 46
DOCUSIGN_FIRST, DOCUSIGN_LAST = 47, 50
MARKER_PAGE = 42
CANCEL_PAGE = 30
TOTAL_CONTRACT = 50


def contract_page(c, job, n, env, final=False):
    cu = job["customer"]
    # pages from the disclosure onward belong to a separate DocuSign envelope (may differ in job03)
    envelope_header(c, (job["envelope_disclosure"] or env) if n >= DISCLOSURE_FIRST else env)
    footer(c, "Solar Power Purchase Agreement - LightHarbor", n, TOTAL_CONTRACT)
    if n == 1:
        txt(c, 40, H - 60, "SOLAR POWER PURCHASE AGREEMENT", "Helvetica-Bold", 16)
        y = H - 95
        field(c, 44, y, "Customer (Homeowner)", job["full_name"], 280)
        field(c, 340, y, "Phone", cu["phone"], 150); y -= 28
        field(c, 44, y, "Installation Address", job["site_line"], 440); y -= 28
        # DC size sits right below name and address block (as in the real packet)
        txt(c, 44, y, "System Size (kW DC):", "Helvetica-Bold", 10)
        txt(c, 170, y, f'{job["kw_contract"]:.2f}', "Helvetica-Bold", 12)
        txt(c, 260, y, "Estimated Year-1 Production:", size=9)
        txt(c, 400, y, f'{int(job["kw_contract"]*1180):,} kWh', size=9); y -= 22
        field(c, 44, y, "Seller / Owner", FINANCE["name"], 440); y -= 28
        field(c, 44, y, "Certified Installer", INSTALLER["name"], 300)
        field(c, 360, y, "License", INSTALLER["license"], 120); y -= 28
        field(c, 44, y, "PPA Rate ($/kWh)", "$0.190", 100); field(c, 180, y, "Escalator", "2.99%", 80)
        field(c, 300, y, "Term (years)", "25", 60); y -= 36
        for _ in range(10):
            y = para(c, 44, y, random.choice(LOREM), W - 90) - 4
    elif n == 24:
        txt(c, 40, H - 70, "Signature Page - Solar Power Purchase Agreement", "Helvetica-Bold", 12)
        para(c, 44, H - 100, "By signing below the Parties agree to be bound by this Agreement and its exhibits.", W - 90)
        y = H - 190
        for who, name, d in (("Homeowner", job["full_name"], job["sign_date_long"]),
                             ("Owner (LightHarbor)", FINANCE["contact"], job["sign_date_long"])):
            txt(c, 44, y, who, "Helvetica-Bold", 10)
            txt(c, 44, y - 28, "Signature:"); c.line(110, y - 30, 330, y - 30); sig(c, 114, y - 27, name)
            txt(c, 44, y - 52, "Name:"); txt(c, 110, y - 52, name); c.line(110, y - 54, 330, y - 54)
            txt(c, 44, y - 76, "Date:"); txt(c, 110, y - 76, d); c.line(110, y - 78, 330, y - 78)
            y -= 130
    elif n == CANCEL_PAGE:
        txt(c, 40, H - 70, "EXHIBIT C: NOTICE OF CANCELLATION", "Helvetica-Bold", 13)
        y = para(c, 44, H - 100, "You may cancel this transaction, without any penalty or obligation, within 10 days after "
                 "signing the contract. If you cancel, any property traded in, any payments made by you under "
                 "the contract or sale and any negotiable instrument executed by you will be returned within 10 days "
                 "following receipt by the seller of your cancellation notice.", W - 90, size=10)
        y = para(c, 44, y - 8, "To cancel, mail or deliver a signed and dated copy of this cancellation notice, or any other "
                 f"written notice, or send an email to help@lightharbor.example not later than midnight of the "
                 "third business day after you sign the Agreement.", W - 90, size=10)
        y -= 20
        txt(c, 44, y, "Installation Address:", "Helvetica-Bold", 10); txt(c, 170, y, job["site_line"], size=10); y -= 50
        txt(c, 44, y, "Homeowner:", "Helvetica-Bold", 11); y -= 32
        txt(c, 44, y, "Signature: ____________________________________"); y -= 34
        txt(c, 44, y, f"Name: {job['full_name']}"); c.line(90, y - 2, 330, y - 2); y -= 34
        txt(c, 44, y, "Date: ____________________________________"); y -= 60
        txt(c, 44, y, "Co-Homeowner (if any):", "Helvetica-Bold", 11); y -= 32
        for lab in ("Signature:", "Name:", "Date:"):
            txt(c, 44, y, f"{lab} ____________________________________"); y -= 30
    elif n == MARKER_PAGE:
        txt(c, 40, H - 70, "DISCLOSURE FORM - START OF ADI DISCLOSURE", "Helvetica-Bold", 13)
        para(c, 44, H - 100, "Pages that follow this notice form the Solar Power Purchase Agreement Disclosure Statement "
             "and the electronic signature certificate for this transaction.", W - 90, size=10)
    elif DISCLOSURE_FIRST <= n <= DISCLOSURE_LAST:
        disc_env = job["envelope_disclosure"] or env
        k = n - DISCLOSURE_FIRST
        if k == 0:
            txt(c, 150, H - 60, "Solar Power Purchase Agreement Disclosure Form", "Helvetica-Bold", 11)
            txt(c, 130, H - 74, "Administratively Determined Incentive (ADI) Program", "Helvetica", 9.5)
            bar(c, 40, H - 98, W - 80, 14, "SOLAR POWER PURCHASE DISCLOSURE STATEMENT")
            y = H - 125
            cols = [(40, "POWER PROVIDER (FINANCER)", FINANCE["short"], FINANCE["contact"], FINANCE["addr"] + ", " + FINANCE["city"] + " " + FINANCE["zip"], FINANCE["phone"], FINANCE["new_email"]),
                    (215, "SOLAR INSTALLER", INSTALLER["name"], INSTALLER["contact"], INSTALLER["addr"] + ", " + INSTALLER["city"] + " " + INSTALLER["zip"], INSTALLER["phone"],
                     INSTALLER["dept_email"] if final else INSTALLER["cust_service_email"]),
                    (390, "WARRANTY / MAINTENANCE", FINANCE["short"], FINANCE["contact"], FINANCE["addr"], FINANCE["phone"], FINANCE["new_email"])]
            for x, hd, comp, contact, addr, ph, em in cols:
                txt(c, x, y, hd, "Helvetica-Bold", 7.5)
                yy = y - 14
                for lab, v in (("Company", comp), ("Contact", contact), ("Address", addr), ("Telephone", ph), ("Email", em)):
                    yy = para(c, x, yy, f"{lab}: {v}", 160, size=7.5) - 3
            y -= 120
            bar(c, 40, y, W - 80, 14, "CUSTOMER (PREMISE CONTACT)")
            y -= 24
            for lab, v in (("Customer Name", job["full_name"]), ("System Installation Address", job["site_line"]),
                           ("Phone", cu["phone"]), ("Email", cu["email"])):
                field(c, 44, y, lab, v, 440); y -= 28
        elif k == 1:
            txt(c, 40, H - 60, "System and Financial Summary", "Helvetica-Bold", 12)
            y = H - 95
            for lab, v in (("System Size (kW DC)", f'{job["kw_contract"]:.2f}'), ("Estimated annual production", f'{int(job["kw_contract"]*1180):,} kWh'),
                           ("PPA rate", "$0.190 / kWh"), ("Annual escalator", "2.99%"), ("Term", "25 years"),
                           ("DocuSign Envelope ID (this document)", job["envelope_disclosure"] or env)):
                field(c, 44, y, lab, v, 440); y -= 28
            y -= 10
            for _ in range(8):
                y = para(c, 44, y, random.choice(LOREM), W - 90) - 4
        elif k == 2:
            txt(c, 40, H - 60, "Acknowledgement", "Helvetica-Bold", 12)
            para(c, 44, H - 85, "Customer acknowledges receipt and review of this disclosure statement.", W - 90)
            y = H - 160
            for who, name, d in (("Customer", job["full_name"], job["sign_date_long"]), ("Power Provider", FINANCE["contact"], job["sign_date_long"])):
                txt(c, 44, y, who, "Helvetica-Bold", 10); txt(c, 44, y - 26, "Signature:")
                c.line(110, y - 28, 330, y - 28); sig(c, 114, y - 25, name)
                txt(c, 44, y - 50, "Date:"); txt(c, 110, y - 50, d); c.line(110, y - 52, 330, y - 52); y -= 120
        else:
            for _ in range(6):
                pass
            y = H - 70
            txt(c, 40, y, "Program Notices", "Helvetica-Bold", 12); y -= 24
            for _ in range(14):
                y = para(c, 44, y, random.choice(LOREM), W - 90) - 4
    elif DOCUSIGN_FIRST <= n <= DOCUSIGN_LAST:
        disc_env = job["envelope_disclosure"] or env
        k = n - DOCUSIGN_FIRST
        txt(c, 40, H - 60, "Certificate Of Completion" if k == 0 else f"Certificate Of Completion (continued {k})", "Helvetica-Bold", 14)
        txt(c, 40, H - 80, f"Envelope Id: {disc_env}", size=9)
        y = H - 110
        for lab, v in (("Status", "Completed"), ("Document Pages", str(TOTAL_CONTRACT)), ("Signatures", "3"), ("Initials", "0")):
            txt(c, 40, y, lab, "Helvetica-Bold", 9); txt(c, 190, y, v, size=9); y -= 16
        y -= 12
        for ev in ("Envelope Sent", "Certified Delivered", "Signing Complete", "Completed"):
            txt(c, 40, y, ev, size=9); txt(c, 250, y, job["sign_date_long"] + " 10:" + str(10 + k * 7), size=9); y -= 14
    else:
        # generic agreement / exhibit page
        section = "Agreement" if n < 25 else ("Exhibit A/B - Schedules" if n < 30 else "Exhibit")
        txt(c, 40, H - 60, f"{section} - Section {n}", "Helvetica-Bold", 12)
        y = H - 90
        for _ in range(16):
            y = para(c, 44, y, random.choice(LOREM) + " " + random.choice(LOREM), W - 90, size=9.5) - 6


def build_contract(path, job):
    random.seed(33)
    def go(buf):
        c = canvas.Canvas(buf, pagesize=letter)
        for n in range(1, TOTAL_CONTRACT + 1):
            contract_page(c, job, n, job["envelope"])
            c.showPage()
        c.save()
    write_pages(path, pages_of(build(go)))


def final_contract_pages(job):
    """returns (disclosure_pages, docusign_pages, contract_pages) for the FINAL packet, email-swapped"""
    random.seed(33)
    def go(buf):
        c = canvas.Canvas(buf, pagesize=letter)
        for n in range(1, TOTAL_CONTRACT + 1):
            contract_page(c, job, n, job["envelope"], final=True)
            c.showPage()
        c.save()
    pg = pages_of(build(go))
    contract = pg[0:24] + [pg[CANCEL_PAGE - 1]]
    disc = pg[DISCLOSURE_FIRST - 1:DISCLOSURE_LAST]
    dsig = pg[DOCUSIGN_FIRST - 1:DOCUSIGN_LAST]
    return contract, disc, dsig


# ----------------------------------------------------------------------------
# Signature forms
# ----------------------------------------------------------------------------
def build_signature_forms(path_fin, path_inst, job):
    def fin(buf):
        c = canvas.Canvas(buf, pagesize=letter)
        txt(c, 40, H - 60, f"{FINANCE['short']} Signature Authorization", "Helvetica-Bold", 14)
        para(c, 44, H - 90, "The undersigned is an authorized signatory of the Power Provider for ADI program filings.", W - 90)
        txt(c, 44, H - 150, "Name:"); txt(c, 100, H - 150, FINANCE["contact"], "Helvetica-Bold", 11)
        txt(c, 44, H - 180, "Title:"); txt(c, 100, H - 180, "Authorized Signatory")
        txt(c, 44, H - 210, "Signature:"); c.line(110, H - 212, 330, H - 212); sig(c, 114, H - 207, FINANCE["contact"])
        c.showPage(); c.save()
    def inst(buf):
        c = canvas.Canvas(buf, pagesize=letter)
        txt(c, 40, H - 60, "Company Digital Signature Authorization Form", "Helvetica-Bold", 14)
        para(c, 44, H - 90, "This template is for company officials who choose to authorize their employees to apply their "
             "legally binding digital signatures to documents submitted to the ADI Program.", W - 90)
        txt(c, 44, H - 170, "I,"); txt(c, 62, H - 170, INSTALLER["contact"], SCRIPT_FONT, 16)
        txt(c, 250, H - 170, "[Full Name], Vice President (Title) of")
        txt(c, 44, H - 205, INSTALLER["name"], SCRIPT_FONT, 16); txt(c, 300, H - 205, "[Formal Company Name], hereby")
        para(c, 44, H - 240, "authorize the employees of the company to apply digital signatures to program documents.", W - 90)
        sig(c, 60, H - 330, INSTALLER["contact"], size=20)
        c.line(50, H - 335, 260, H - 335)
        c.showPage()
        for k in (2, 3):
            txt(c, 40, H - 60, f"Signature Verification Sheet ({k-1}/2)", "Helvetica-Bold", 13)
            y = H - 100
            for _ in range(8):
                y = para(c, 44, y, random.choice(LOREM), W - 90) - 5
            c.showPage()
        c.save()
    write_pages(path_fin, pages_of(build(fin)))
    write_pages(path_inst, pages_of(build(inst)))


# ----------------------------------------------------------------------------
# Designs (11x17 landscape)  &  Site report
# ----------------------------------------------------------------------------
DESIGN_PAGE_TITLES = ["PV-0 COVER / NOTES", "PV-1 SITE PLAN", "PV-2 ROOF / ATTACHMENT DETAIL",
                      "PV-3 ELECTRICAL DIAGRAM", "PV-4 LABELS / PLACARDS", "PV-5 EQUIPMENT SCHEDULE",
                      "SPEC SHEET - PV MODULE", "SPEC SHEET - INVERTER", "SPEC SHEET - RAPID SHUTDOWN"]
KEEP_DESIGN_PAGES = [1, 3, 7]  # zero-based: site plan, electrical diagram, inverter spec


def title_block(c, job, sheet, kw):
    x0 = TABLOID[0] - 210
    c.rect(x0, 24, 190, TABLOID[1] - 48)
    txt(c, x0 + 8, TABLOID[1] - 50, "PROJECT NAME", "Helvetica-Bold", 7)
    txt(c, x0 + 8, TABLOID[1] - 62, f'{job["customer"]["last"].upper()}, {job["customer"]["first"].upper()}', "Helvetica", 9)
    txt(c, x0 + 8, TABLOID[1] - 86, "PROJECT ADDRESS", "Helvetica-Bold", 7)
    txt(c, x0 + 8, TABLOID[1] - 98, job["site"]["addr"].upper(), size=8)
    txt(c, x0 + 8, TABLOID[1] - 108, f'{job["site"]["city"].upper()}, {job["site"]["state"]} {job["site"]["zip"]}', size=8)
    txt(c, x0 + 8, TABLOID[1] - 134, "SYSTEM SIZE", "Helvetica-Bold", 7)
    txt(c, x0 + 8, TABLOID[1] - 146, f"{kw:.3f} kW DC", "Helvetica-Bold", 10)
    txt(c, x0 + 8, TABLOID[1] - 172, "DRAWN BY", "Helvetica-Bold", 7); txt(c, x0 + 8, TABLOID[1] - 184, "Sunridge Solar Design", size=8)
    txt(c, x0 + 8, 60, sheet, "Helvetica-Bold", 12)
    txt(c, x0 + 8, 40, "11x17 TEMPLATE - fictional test data", size=6, color=GREY)


def draw_modules(c, x, y, count, cols, mw=24, mh=38):
    rows = (count + cols - 1) // cols
    drawn = 0
    for r in range(rows):
        for k in range(cols):
            if drawn >= count:
                return
            c.setFillColor(HexColor("#2b3a55")); c.setStrokeColor(white)
            c.rect(x + k * (mw + 2), y - r * (mh + 2), mw, mh, stroke=1, fill=1)
            drawn += 1
    c.setFillColor(black); c.setStrokeColor(black)


def build_designs(path, job, full=True):
    arrays = job["arrays_design"]
    kw_title = job["kw_design"]
    def go(buf):
        c = canvas.Canvas(buf, pagesize=TABLOID)
        for pi, ttl in enumerate(DESIGN_PAGE_TITLES):
            title_block(c, job, ttl.split(" ")[0] if ttl.startswith("PV") else "SPEC", kw_title)
            txt(c, 30, TABLOID[1] - 36, ttl, "Helvetica-Bold", 16)
            if ttl.startswith("PV-1"):
                # house + arrays
                c.setStrokeColor(black); c.setFillColor(HexColor("#e8e1d4"))
                c.rect(280, 180, 520, 340, stroke=1, fill=1)
                x = 300
                for a in arrays:
                    cols = max(2, min(6, a["modules"]))
                    draw_modules(c, x, 440, a["modules"], cols)
                    txt(c, x, 495, f'R{a["roof"]} ({a["modules"]} MODULES)', "Helvetica-Bold", 8)
                    txt(c, x, 195, f'AZ {a["az"]}  TILT {a["pitch"]}', size=7)
                    x += (cols * 26) + 24
                txt(c, 60, 150, "3'-0\" CLEAR PATH AT RIDGE, 3'-0\" CLEAR PATH AT EAVES", size=8)
                txt(c, 60, 130, f'TOTAL MODULES: {job["panels_design"]}   TOTAL DC: {job["kw_design"]:.3f} kW', "Helvetica-Bold", 10)
                c.circle(900, 640, 24); txt(c, 893, 636, "N", "Helvetica-Bold", 14)
            elif ttl.startswith("PV-3"):
                labels = ["PV ARRAYS", "DC DISCONNECT", f'INVERTER {INVERTER["model"]}', "AC DISCONNECT", "PRODUCTION METER", "UTILITY METER"]
                x = 60
                for lb in labels:
                    c.rect(x, 330, 130, 70)
                    para(c, x + 6, 380, lb, 118, "Helvetica-Bold", 8)
                    if x < 800:
                        c.line(x + 130, 365, x + 160, 365)
                    x += 160
                txt(c, 60, 280, f'INVERTER AC OUTPUT: {INVERTER["ac_kw"]} kW / {INVERTER["ac_a"]} A', size=9)
            elif ttl.startswith("PV-5"):
                y = 560
                txt(c, 60, y, "EQUIPMENT SCHEDULE", "Helvetica-Bold", 11); y -= 26
                txt(c, 60, y, f'MODULES   {job["panels_design"]} x {PANEL["mfr"]} ({PANEL["model"]})   {PANEL["watts"]} W', size=10); y -= 22
                txt(c, 60, y, f'INVERTER  {INVERTER["qty"]} x {INVERTER["mfr"]} {INVERTER["model"]}   {INVERTER["ac_kw"]} kW AC', size=10); y -= 30
                for a in arrays:
                    txt(c, 60, y, f'ARRAY R{a["roof"]}: {a["modules"]} modules  AZ {a["az"]}  TILT {a["pitch"]}  = {a["size_kw"]:.3f} kW', size=9); y -= 18
            elif ttl.startswith("SPEC SHEET - PV"):
                txt(c, 60, 500, f'{PANEL["mfr"]} {PANEL["model"]} SERIES', "Helvetica-Bold", 28)
                txt(c, 60, 470, "395-415 Wp | 132 Cells | 21.1% max efficiency", size=12)
                c.setFillColor(HexColor("#1b1b1b")); c.rect(60, 180, 160, 260, stroke=0, fill=1); c.setFillColor(black)
                txt(c, 260, 440, "Electrical characteristics (STC)", "Helvetica-Bold", 11)
                for i, (k, v) in enumerate([("Power class (W)", "395 / 400 / 405 / 410 / 415"), ("Isc (A)", "11.30"), ("Voc (V)", "45.27"), ("Efficiency (%)", "20.1 - 21.1")]):
                    txt(c, 260, 415 - i * 18, f"{k}: {v}", size=10)
            elif ttl.startswith("SPEC SHEET - INV"):
                txt(c, 60, 500, f'{INVERTER["mfr"]} {INVERTER["model"]}', "Helvetica-Bold", 26)
                for i, (k, v) in enumerate([("Rated AC output", f'{INVERTER["ac_kw"]*1000:.0f} W'), ("Max AC current", f'{INVERTER["ac_a"]} A'),
                                            ("Peak efficiency", f'{INVERTER["eff"]*100:.0f}%'), ("Nominal AC voltage", "240 V")]):
                    txt(c, 60, 450 - i * 22, f"{k}: {v}", size=12)
            else:
                y = 560
                for _ in range(12):
                    y = para(c, 60, y, random.choice(LOREM), 800, size=10) - 6
            c.showPage()
        c.save()
    pgs = pages_of(build(go))
    write_pages(path, pgs)
    return pgs


def build_site_report(path, job):
    arr = job["arrays_sitereport"]
    def go(buf):
        c = canvas.Canvas(buf, pagesize=(1000, 760))
        # page 1: aerial-ish cover
        c.setFillColor(HexColor("#2f4f3a")); c.rect(0, 0, 1000, 760, stroke=0, fill=1)
        c.setFillColor(HexColor("#cdb892")); c.rect(300, 220, 400, 280, stroke=0, fill=1)
        c.setFillColor(white); c.setFont("Helvetica-Bold", 26); c.drawString(40, 710, "Remote Site Assessment")
        c.setFont("Helvetica", 14); c.drawString(40, 685, f'{job["site_line"]}')
        c.showPage()
        # page 2: RSA - roof summaries
        c.setFillColor(HexColor("#0e1116")); c.rect(0, 0, 1000, 760, stroke=0, fill=1)
        c.setFillColor(white); c.setFont("Helvetica-Bold", 20)
        c.drawString(60, 690, "SolarScope"); c.setFont("Helvetica", 11)
        c.drawRightString(940, 700, "RSA - ROOF SUMMARIES"); c.drawRightString(940, 684, f'{job["customer"]["last"]}, {job["customer"]["first"]}')
        c.drawRightString(940, 668, job["site_line"]); c.drawRightString(940, 652, "Vendor: SolarScope")
        hdr = ["ROOF #", "PITCH (DEGREES)", "AZIMUTH (DEGREES)", "SOLAR ACCESS (UNSHADED %)", "EFFICIENCY (TSRF%)",
               "MODULES (QTY)", "ARRAY SIZE (kW DC)", "UTILITY PRODUCTION (kWh)", "ACTUAL PRODUCTION (kWh)"]
        x0, y0, cw, rh = 60, 600, 98, 34
        c.setFillColor(HexColor("#4a78b5")); c.rect(x0, y0, cw * len(hdr), rh, stroke=0, fill=1)
        c.setFillColor(white); c.setFont("Helvetica-Bold", 6.5)
        for i, h in enumerate(hdr):
            for j, line in enumerate(simpleSplit(h, "Helvetica-Bold", 6.5, cw - 8)):
                c.drawCentredString(x0 + cw * i + cw / 2, y0 + rh - 13 - j * 8, line)
        rows = roof_rows(arr)
        for r, a in enumerate(rows):
            y = y0 - (r + 1) * rh
            c.setFillColor(HexColor("#b9b9b9")); c.rect(x0, y, cw * len(hdr), rh, stroke=1, fill=1)
            c.setFillColor(black); c.setFont("Helvetica", 9)
            vals = [str(r + 1)] + ([str(a["pitch"]), str(a["az"]), str(a["access"]), str(a["tsrf"]), str(a["modules"]),
                                    f'{a["size_kw"]:.3f}', f'{a["util"]:,}', f'{a["actual"]:,}'] if a else [""] * 8)
            if a is None:
                vals[0] = str(r + 1)
            for i, v in enumerate(vals):
                c.drawCentredString(x0 + cw * i + cw / 2, y + 12, v)
        y = y0 - 7 * rh - 10
        wa = round(sum(a["access"] * a["modules"] for a in arr) / sum(a["modules"] for a in arr))
        wt = round(sum(a["tsrf"] * a["modules"] for a in arr) / sum(a["modules"] for a in arr))
        c.setFillColor(HexColor("#4a78b5")); c.rect(x0 + cw * 3, y, cw * 2, 16, stroke=0, fill=1); c.rect(x0 + cw * 5, y, cw * 4, 16, stroke=0, fill=1)
        c.setFillColor(white); c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x0 + cw * 4, y + 4, "WEIGHTED AVERAGES"); c.drawCentredString(x0 + cw * 7, y + 4, "TOTALS")
        y -= rh
        c.setFillColor(HexColor("#b9b9b9")); c.rect(x0 + cw * 3, y, cw * 6, rh, stroke=1, fill=1)
        c.setFillColor(black); c.setFont("Helvetica", 9)
        c.drawCentredString(x0 + cw * 3.5, y + 12, str(wa)); c.drawCentredString(x0 + cw * 4.5, y + 12, str(wt))
        c.drawCentredString(x0 + cw * 5.5, y + 12, str(sum(a["modules"] for a in arr)))
        c.drawCentredString(x0 + cw * 6.5, y + 12, f'{sum(a["size_kw"] for a in arr):.3f}')
        c.drawCentredString(x0 + cw * 7.5, y + 12, f'{sum(a["util"] for a in arr):,}')
        c.drawCentredString(x0 + cw * 8.5, y + 12, f'{sum(a["actual"] for a in arr):,}')
        c.showPage()
        for r in range(3, 9):  # per-roof shading pages
            c.setFillColor(HexColor("#101418")); c.rect(0, 0, 1000, 760, stroke=0, fill=1)
            c.setFillColor(white); c.setFont("Helvetica-Bold", 16); c.drawString(60, 700, f"Roof {r-2} - shading analysis")
            rnd = random.Random(r)
            for gx in range(20):
                for gy in range(12):
                    t = rnd.random()
                    c.setFillColor(HexColor("#ffcc33") if t > .5 else HexColor("#ff8844") if t > .2 else HexColor("#cc3322"))
                    c.rect(100 + gx * 36, 120 + gy * 36, 34, 34, stroke=0, fill=1)
            c.showPage()
        c.save()
    write_pages(path, pages_of(build(go)))


# ----------------------------------------------------------------------------
# Name clarification (expected output for name mismatch jobs)
# ----------------------------------------------------------------------------
def build_name_clarification(path, job):
    def go(buf):
        c = canvas.Canvas(buf, pagesize=letter)
        txt(c, 60, H - 70, "Garden State Clean Energy Program", "Helvetica-Bold", 12)
        txt(c, 60, H - 86, "Administrative Review Team", size=11)
        txt(c, 60, H - 102, "100 Example Plaza, Suite 520, Trenton, NJ 08000", size=11)
        txt(c, 60, H - 140, "RE: Name Clarification", "Helvetica-Bold", 12)
        c.line(60, H - 146, W - 60, H - 146)
        txt(c, 60, H - 180, "To the Garden State Clean Energy Program,", size=11)
        txt(c, 60, H - 215, "Please note the following:", size=11)
        para(c, 60, H - 245, f'{job["customer"]["first"]} {job["customer"]["last"]} and {job["ebill_name"].title()} '
             "are the same person; one is her maiden name.", W - 120, size=11)
        txt(c, 60, H - 330, "Sincerely,", size=11)
        sig(c, 60, H - 360, INSTALLER["contact"], size=20)
        txt(c, 60, H - 385, INSTALLER["contact"] + ", " + INSTALLER["name"], size=10)
        c.showPage(); c.save()
    write_pages(path, pages_of(build(go)))


# ----------------------------------------------------------------------------
# Ground truth JSON
# ----------------------------------------------------------------------------
def truth(job, jid):
    arrays = []
    for a in job["arrays_design"]:
        arrays.append({
            "roof": a["roof"], "quantity": a["modules"], "rating_dc_kw": PANEL["watts"] / 1000,
            "manufacturer": "NovaSun", "model": PANEL["model"], "location": "Roof",
            "orientation_azimuth": a["az"], "tilt": a["pitch"], "tracking": "Fixed",
            "solar_access_pct": a["access"], "design_system_rated_output_kwh": a["util"],
            "ideal_system_rated_output_kwh": a["actual"],
        })
    sr_mod = sum(a["modules"] for a in job["arrays_sitereport"])
    checks = {
        "dc_size_contract_vs_design_vs_chatter": "FAIL" if job["kw_contract"] != job["kw_design"] else "PASS",
        "panel_count_site_report_vs_designs": "FAIL" if sr_mod != job["panels_design"] else "PASS",
        "audit_date_within_2_days_of_signing": "FAIL" if abs(int(job["audit_last_date"].split("/")[1]) - int(job["sign_date"].split("-")[1])) > 2 else "PASS",
        "docusign_envelope_id_matches_disclosure": "FAIL" if job["envelope_disclosure"] else "PASS",
        "all_signature_dates_present": "FAIL" if job["adi_blank_customer_date"] else "WARN_finance_date_blank_in_raw_filled_in_final",
        "ebill_name_matches_contract": "FAIL_needs_name_clarification_form" if job["name_clarification"] else "PASS",
        "ebill_account_number_legible": "FAIL" if job["ebill_style"] == "photo_blur" else "PASS",
        "lightreach_email_swapped": "FIXED_IN_FINAL",
        "customer_service_email_swapped_on_disclosure": "FIXED_IN_FINAL",
    }
    return {
        "job_id": jid, "scenario": job["title"],
        "customer": {**job["customer"], "contract_full_name": job["full_name"], "ebill_name": job["ebill_name"]},
        "site": job["site"],
        "utility": job["utility"],
        "salesforce": {"total_install_cost": job["price"], "finance_partner": "LightHarbor",
                       "system_size_kw_in_salesforce": job["kw_contract"], "chatter": job["chatter"],
                       "state_program_fields": {"prelim_state_status": "Submitted (after run)", "follow_up_weeks": 4}},
        "portal_values": {
            "interconnection_type": "Behind the meter", "market_segment": "Net metered residential",
            "registration_type": "New registration", "installation_type": "Rooftop",
            "owner": "financer (autofilled)", "installer": INSTALLER["name"], "contact": INSTALLER["contact"],
            "license": INSTALLER["license"], "license_expiry": INSTALLER["license_exp"],
            "customer_type": "Residential", "tariff": "Residential",
            "inverter": {"quantity": 1, "manufacturer": INVERTER["mfr"], "model": INVERTER["model"], "ac_kw": INVERTER["ac_kw"],
                         "peak_efficiency": INVERTER["eff"], "location": "Outdoor", "ai_tool_continuous_rating_w": INVERTER["ac_kw"] * 1000},
            "arrays": arrays,
            "total_panels": job["panels_design"], "total_dc_kw_design": job["kw_design"],
            "total_dc_kw_contract": job["kw_contract"],
        },
        "expected_checks": checks,
        "name_clarification_required": job["name_clarification"],
        "final_documents": ["1_ADI.pdf", "2_Contract.pdf", "3_Disclosure.pdf", "4_EBill.pdf", "5_Designs.pdf"]
                           + (["6_Name_Clarification.pdf"] if job["name_clarification"] else []),
        "state_ai_tool_known_issues_to_reproduce": [
            "lumps all panels into one array", "drops middle digits of utility account number",
            "pre-fills an outdated license number", "inverter continuous rating must be a whole number (W)",
        ],
    }


# ----------------------------------------------------------------------------
def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for jid, raw in JOBS.items():
        job = derive(raw)
        base = os.path.join(OUT, jid)
        rawd, expd = os.path.join(base, "raw"), os.path.join(base, "expected")
        os.makedirs(rawd); os.makedirs(expd)
        random.seed(7)
        build_combined_pack(os.path.join(rawd, "Combined Pack.pdf"), job)
        build_audit_trail(os.path.join(rawd, "Combined Pack_AuditTrail.pdf"), job)
        build_ebill(os.path.join(rawd, "Electric Bill.pdf"), job)
        build_contract(os.path.join(rawd, "LightHarbor PPA Contract.pdf"), job)
        build_signature_forms(os.path.join(rawd, "LightHarbor Signature Forms.pdf"),
                              os.path.join(rawd, "Installer Signature Forms.pdf"), job)
        design_pages = build_designs(os.path.join(rawd, "FULL SET Designs.pdf"), job)
        build_site_report(os.path.join(rawd, "SITE REPORT.pdf"), job)

        # ---------- expected / final five documents
        adi_final = pages_of(adi_pdf(job, final=True))
        audit_pages = list(PdfReader(os.path.join(rawd, "Combined Pack_AuditTrail.pdf")).pages)
        fin_sig = list(PdfReader(os.path.join(rawd, "LightHarbor Signature Forms.pdf")).pages)
        inst_sig = list(PdfReader(os.path.join(rawd, "Installer Signature Forms.pdf")).pages)
        contract, disc, dsig = final_contract_pages(job)
        write_pages(os.path.join(expd, "1_ADI.pdf"), adi_final + audit_pages)
        write_pages(os.path.join(expd, "2_Contract.pdf"), contract + dsig + fin_sig + inst_sig[:1])
        write_pages(os.path.join(expd, "3_Disclosure.pdf"), disc + dsig + fin_sig + inst_sig[:1])
        shutil.copy(os.path.join(rawd, "Electric Bill.pdf"), os.path.join(expd, "4_EBill.pdf"))
        write_pages(os.path.join(expd, "5_Designs.pdf"), [design_pages[i] for i in KEEP_DESIGN_PAGES])
        if job["name_clarification"]:
            build_name_clarification(os.path.join(expd, "6_Name_Clarification.pdf"), job)
        with open(os.path.join(expd, "expected_values.json"), "w") as f:
            json.dump(truth(job, jid), f, indent=2)
        with open(os.path.join(rawd, "salesforce_opportunity.json"), "w") as f:
            json.dump({"opportunity": f'{job["customer"]["last"]}, {job["customer"]["first"]}',
                       "finance_partner": "LightHarbor", "system_size_kw": job["kw_contract"],
                       "total_install_cost": job["price"], "utility_company": job["utility"]["name"],
                       "utility_account_number": job["utility"]["acct"], "utility_meter_number": job["utility"]["meter"],
                       "installation_type": "Pitched Roof - Asphalt", "chatter": job["chatter"]}, f, indent=2)
        print("built", jid)

    with open(os.path.join(OUT, "README.md"), "w") as f:
        f.write(README)


README = """# Fictional NJ prelim-state test packets

All names, addresses, companies, account numbers and signatures are invented.
Layouts mimic the document types in the walkthrough videos.

| Job | Scenario |
|---|---|
| job01_clean | 14 panels / 2 arrays. Everything consistent. The ADI finance-signer date is blank in the raw file (the specialist fills it in). |
| job02_three_arrays_name_mismatch | 24 panels / 3 arrays (the state AI lumps these into one). E-bill is a phone photo with a different name (maiden name) so a Name Clarification form is required. |
| job03_defects | Deliberate defects: contract DC (6.15) != design DC (5.74); stale site report (16 modules vs 14); audit date 3 days before ADI signing date; disclosure DocuSign envelope ID differs from the contract; customer date missing on ADI; e-bill photo with smudged account number. |

Each job has:
- `raw/`      files as the specialist downloads them from Box/Salesforce (plus `salesforce_opportunity.json`)
- `expected/` the five finished documents (1_ADI, 2_Contract, 3_Disclosure, 4_EBill, 5_Designs) and `expected_values.json`
              (portal field values, per-array data, and which validation checks should PASS/FAIL)

Regenerate with `python generate_test_data.py`.
"""

if __name__ == "__main__":
    main()

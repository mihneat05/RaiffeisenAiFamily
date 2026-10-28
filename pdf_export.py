"""Checklist-ul de printat / salvat, ca PDF (fpdf2)."""
import os
import unicodedata
from datetime import date

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Fonturile de bază din fpdf nu au ș/ț/ă; căutăm un TTF și, dacă nu găsim, scoatem diacriticele.
_FONT_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "assets", "DejaVuSans.ttf"),
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]
_MARK = {"ok": "[OK]", "warn": "[DE VERIFICAT]", "fail": "[PROBLEMĂ]", "pending": "[LIPSEȘTE]"}


def _ascii(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def build_checklist_pdf(event_label, rows, headline, reasons, branch):
    pdf = FPDF()
    pdf.set_margins(18, 18, 18)
    pdf.add_page()

    font = next((p for p in _FONT_CANDIDATES if os.path.exists(p)), None)
    if font:
        pdf.add_font("Body", fname=font)
        family, clean = "Body", str
    else:
        family, clean = "Helvetica", _ascii

    def line(text, size=11, gap=1.5, indent=0):
        pdf.set_font(family, size=size)
        pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(0, size * 0.5, clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(gap)

    line("Raiffeisen Family Agent · checklist", size=18, gap=1)
    line(f"Situație: {event_label}   ·   {date.today():%d.%m.%Y}", size=10, gap=6)

    line(headline, size=13, gap=1)
    for r in reasons:
        line(f"– {r}", size=10, indent=4, gap=0.5)
    pdf.ln(5)

    line("Ce acte să iei cu tine (în original)", size=13, gap=2)
    for row in rows:
        line(f"{_MARK[row['status']]}  {row['label']}", gap=0.5)
        for r in row["reasons"]:
            line(f"– {r}", size=9, indent=6, gap=0.5)
        pdf.ln(1.5)
    pdf.ln(4)

    line("Unde mergi", size=13, gap=2)
    line(branch["name"], gap=0.5)
    line(f"{branch['address']} · {branch['hours']}", size=10, gap=6)

    line("Acest checklist e generat de un asistent AI și are rol consultativ. "
         "Verificarea finală se face la bancă, de către consilier.", size=8)
    return bytes(pdf.output())

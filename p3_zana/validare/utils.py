"""Funcții mici: CNP, date, nume, cote. Fără LLM, doar cod determinist."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from fractions import Fraction
from typing import Optional

# ---------------------------------------------------------------- CNP

PONDERI_CNP = "279146358279"
JUDETE_VALIDE = {f"{i:02d}" for i in range(1, 49)} | {"51", "52", "70", "80", "81", "82", "83"}


def cifra_control_cnp(primele_12: str) -> int:
    s = sum(int(c) * int(p) for c, p in zip(primele_12, PONDERI_CNP))
    rest = s % 11
    return 1 if rest == 10 else rest


def data_nasterii_din_cnp(cnp: str, azi: Optional[date] = None) -> Optional[date]:
    azi = azi or date.today()
    s, aa, ll, zz = int(cnp[0]), int(cnp[1:3]), int(cnp[3:5]), int(cnp[5:7])
    if s in (1, 2):
        an = 1900 + aa
    elif s in (3, 4):
        an = 1800 + aa
    elif s in (5, 6):
        an = 2000 + aa
    elif s in (7, 8, 9):  # rezidenți / străini: secolul nu e codat, îl deducem
        an = 2000 + aa if 2000 + aa <= azi.year else 1900 + aa
    else:
        return None
    try:
        return date(an, ll, zz)
    except ValueError:
        return None


def verifica_cnp(cnp: object, azi: Optional[date] = None) -> list[tuple[str, str]]:
    """Întoarce o listă de (cod, mesaj). Listă goală = CNP valid."""
    if cnp is None or str(cnp).strip() == "":
        return [("CNP_LIPSA", "CNP-ul nu a putut fi citit de pe act.")]
    cnp = re.sub(r"\s", "", str(cnp))
    if not re.fullmatch(r"\d{13}", cnp):
        return [("CNP_FORMAT", f"CNP-ul „{cnp}” trebuie să aibă exact 13 cifre.")]
    if cnp[0] == "0":
        return [("CNP_SEX", "Prima cifră a CNP-ului nu poate fi 0.")]
    erori = []
    nastere = data_nasterii_din_cnp(cnp, azi)
    if nastere is None:
        erori.append(("CNP_DATA", "Data de naștere din CNP nu este o dată reală."))
    elif nastere > (azi or date.today()):
        erori.append(("CNP_DATA", "Data de naștere din CNP este în viitor."))
    if cnp[7:9] not in JUDETE_VALIDE:
        erori.append(("CNP_JUDET", f"Codul de județ „{cnp[7:9]}” din CNP nu există."))
    if cnp[9:12] == "000":
        erori.append(("CNP_SERIE", "Numărul de ordine din CNP nu poate fi 000."))
    if int(cnp[12]) != cifra_control_cnp(cnp[:12]):
        erori.append(("CNP_CIFRA_CONTROL",
                      "Cifra de control a CNP-ului nu se potrivește: probabil o cifră a fost "
                      "citită greșit sau actul conține o greșeală."))
    return erori


def curata_cnp(cnp: object) -> Optional[str]:
    if cnp is None:
        return None
    c = re.sub(r"\s", "", str(cnp))
    return c or None


# ---------------------------------------------------------------- date

FORMATE_DATA = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y")


def parse_data(valoare: object) -> Optional[date]:
    if valoare is None or valoare == "":
        return None
    if isinstance(valoare, datetime):
        return valoare.date()
    if isinstance(valoare, date):
        return valoare
    text = str(valoare).strip()
    for fmt in FORMATE_DATA:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def format_data(d: date) -> str:
    return d.strftime("%d.%m.%Y")


# ---------------------------------------------------------------- nume

def normalizeaza(text: object) -> str:
    """„Ștefănescu-Popa  ana” -> „STEFANESCU POPA ANA”."""
    if text is None:
        return ""
    t = unicodedata.normalize("NFKD", str(text))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^A-Za-z ]", " ", t.replace("-", " "))
    return re.sub(r"\s+", " ", t).strip().upper()


def tokeni(text: object) -> set[str]:
    return set(normalizeaza(text).split())


def nume_compatibile(a: object, b: object) -> bool:
    """Egal sau unul conține toate cuvintele celuilalt (ex. două prenume vs. unul)."""
    ta, tb = tokeni(a), tokeni(b)
    if not ta or not tb:
        return False
    return ta <= tb or tb <= ta


def nume_complet(persoana: dict) -> str:
    return f"{persoana.get('prenume', '') or ''} {persoana.get('nume', '') or ''}".strip()


# ---------------------------------------------------------------- cote

def parse_cota(valoare: object) -> Optional[Fraction]:
    """Acceptă „1/4”, „25%”, 0.25, „0,25”."""
    if valoare is None or valoare == "":
        return None
    if isinstance(valoare, (int, float)):
        return Fraction(str(valoare)).limit_denominator(10000)
    text = str(valoare).strip().replace(",", ".").replace(" ", "")
    try:
        if text.endswith("%"):
            return Fraction(text[:-1]) / 100
        return Fraction(text).limit_denominator(10000)
    except (ValueError, ZeroDivisionError):
        return None

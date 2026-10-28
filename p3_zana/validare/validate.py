"""validate_document: verifică UN act, independent de celelalte."""
from __future__ import annotations

import re
from datetime import date, timedelta
from fractions import Fraction
from typing import Any, Optional

from .adaptor import normalizeaza_act
from .models import Problema, Severitate, Verdict
from .reguli import (CAI_CNP, CAMPURI_OBLIGATORII, CAMPURI_RECOMANDATE,
                     SCOR_MINIM_LIZIBILITATE, ZILE_AVERTIZARE_EXPIRARE)
from .utils import data_nasterii_din_cnp, format_data, parse_cota, parse_data, verifica_cnp

E, A = Severitate.EROARE, Severitate.ATENTIE


def ia(doc: dict, cale: str) -> Any:
    val: Any = doc
    for parte in cale.split("."):
        if not isinstance(val, dict):
            return None
        val = val.get(parte)
    return val


def id_act(doc: dict) -> str:
    return str(doc.get("id") or doc.get("tip") or "act")


def validate_document(doc: Any, azi: Optional[date] = None) -> Verdict:
    """Acceptă formatul P2 (schemas.py, dict sau model) sau formatul intern."""
    azi = azi or date.today()
    doc = normalizeaza_act(doc)
    tip = doc.get("tip")
    did = id_act(doc)
    probleme: list[Problema] = []

    def add(cod: str, sev: Severitate, mesaj: str, camp: str | None = None) -> None:
        probleme.append(Problema(cod=cod, severitate=sev, mesaj=mesaj, document=did, camp=camp))

    if tip not in CAMPURI_OBLIGATORII:
        add("TIP_NECUNOSCUT", E, f"Nu am recunoscut tipul actului („{tip}”). "
            "Încarcă o poză mai clară sau alege tipul actului manual.")
        return Verdict.din_probleme(probleme)

    # 1. calitatea pozei (dacă P2 trimite un scor)
    scor = doc.get("lizibilitate")
    if isinstance(scor, (int, float)) and scor < SCOR_MINIM_LIZIBILITATE:
        add("POZA_NECLARA", A, "Poza nu e destul de clară, unele date pot fi citite greșit. "
            "Refă poza la lumină bună, fără reflexii.")

    # 2. câmpuri obligatorii
    for cale in CAMPURI_OBLIGATORII[tip]:
        val = ia(doc, cale)
        if val is None or val == "" or val == []:
            add("CAMP_LIPSA", E, f"Nu am putut citi câmpul „{cale}” de pe act.", cale)
    for cale, mesaj in CAMPURI_RECOMANDATE.get(tip, {}).items():
        if ia(doc, cale) in (None, "", []):
            add("CAMP_RECOMANDAT_LIPSA", A, mesaj, cale)

    # câmpuri pe care P2 le-a citit cu încredere mică
    for camp in doc.get("campuri_nesigure") or []:
        add("CAMP_NESIGUR", A, f"Câmpul „{camp}” nu a fost citit sigur. Verifică-l pe act "
            "sau refă poza.", camp)

    # 3. CNP-uri
    for cale in CAI_CNP.get(tip, []):
        cnp = ia(doc, cale)
        if cnp in (None, ""):
            continue  # deja raportat ca lipsă
        for cod, mesaj in verifica_cnp(cnp, azi):
            add(cod, E, mesaj, cale)

    # 4. verificări specifice fiecărui tip
    VERIFICARI_SPECIFICE[tip](doc, azi, add)

    # 5. elemente vizuale (doar preliminar: AI-ul NU garantează autenticitatea)
    for camp, eticheta in (("semnat_stampilat", "semnătura sau ștampila"),
                           ("are_stampila", "ștampila"), ("are_semnatura", "semnătura")):
        if doc.get(camp) is False:
            add(camp.upper(), A, f"Nu am găsit {eticheta} pe act. Consilierul va verifica originalul.", camp)

    return Verdict.din_probleme(probleme)


# ------------------------------------------------------------------ pe tipuri

def _data_trecut(doc, cale, azi, add, eticheta):
    """Parsează o dată care trebuie să fie în trecut. Întoarce data sau None."""
    brut = ia(doc, cale)
    if brut in (None, ""):
        return None
    d = parse_data(brut)
    if d is None:
        add("DATA_INVALIDA", E, f"Data „{brut}” ({eticheta}) nu este o dată validă.", cale)
    elif d > azi:
        add("DATA_VIITOR", E, f"Data ({eticheta}) {format_data(d)} este în viitor.", cale)
    return d


def _buletin(doc, azi, add):
    serie, numar = doc.get("serie"), doc.get("numar")
    if serie and not re.fullmatch(r"[A-Z]{2}", str(serie).strip().upper()):
        add("SERIE_FORMAT", A, f"Seria „{serie}” ar trebui să aibă 2 litere. Verifică dacă a fost citită corect.", "serie")
    if numar and not re.fullmatch(r"\d{6}", str(numar).strip()):
        add("NUMAR_FORMAT", A, f"Numărul „{numar}” ar trebui să aibă 6 cifre. Verifică dacă a fost citit corect.", "numar")

    exp_brut = doc.get("data_expirarii")
    exp = parse_data(exp_brut)
    if exp_brut and exp is None:
        add("DATA_INVALIDA", E, f"Data expirării „{exp_brut}” nu este o dată validă.", "data_expirarii")
    elif exp:
        if exp < azi:
            add("BULETIN_EXPIRAT", E, f"Buletinul a expirat pe {format_data(exp)}. "
                "Ai nevoie de un act de identitate valabil.", "data_expirarii")
        elif exp <= azi + timedelta(days=ZILE_AVERTIZARE_EXPIRARE):
            add("BULETIN_EXPIRA_CURAND", A, f"Buletinul expiră pe {format_data(exp)}. "
                "Dacă programarea e după această dată, nu va mai fi valabil.", "data_expirarii")

    # data nașterii de pe buletin vs. cea codată în CNP
    nastere = parse_data(doc.get("data_nasterii"))
    cnp = str(doc.get("cnp") or "")
    if nastere and len(cnp) == 13 and cnp.isdigit():
        din_cnp = data_nasterii_din_cnp(cnp, azi)
        if din_cnp and din_cnp != nastere:
            add("CNP_vs_DATA_NASTERII", E, "Data nașterii de pe buletin nu corespunde cu cea din CNP.", "cnp")


def _certificat_deces(doc, azi, add):
    deces = _data_trecut(doc, "data_decesului", azi, add, "decesului")
    cnp = str(doc.get("cnp") or "")
    if deces and len(cnp) == 13 and cnp.isdigit():
        nastere = data_nasterii_din_cnp(cnp, azi)
        if nastere and deces < nastere:
            add("DECES_INAINTE_NASTERE", E, "Data decesului este înaintea datei nașterii din CNP.", "data_decesului")


def _certificat_mostenitor(doc, azi, add):
    _data_trecut(doc, "data_emiterii", azi, add, "emiterii")
    mostenitori = doc.get("mostenitori") or []
    if not isinstance(mostenitori, list):
        add("MOSTENITORI_FORMAT", E, "Lista moștenitorilor nu a putut fi citită.", "mostenitori")
        return
    total = Fraction(0)
    cote_ok = True
    for i, m in enumerate(mostenitori, 1):
        eticheta = f"mostenitori[{i}]"
        for camp in ("nume", "prenume", "cnp", "cota"):
            if not m.get(camp):
                add("CAMP_LIPSA", E, f"Moștenitorul {i}: nu am putut citi „{camp}”.", f"{eticheta}.{camp}")
        if m.get("cnp"):
            for cod, mesaj in verifica_cnp(m["cnp"], azi):
                add(cod, E, f"Moștenitorul {i}: {mesaj}", f"{eticheta}.cnp")
        cota = parse_cota(m.get("cota"))
        if m.get("cota") and (cota is None or cota <= 0 or cota > 1):
            add("COTA_INVALIDA", E, f"Moștenitorul {i}: cota „{m.get('cota')}” nu este validă.", f"{eticheta}.cota")
            cote_ok = False
        elif cota is None:
            cote_ok = False
        else:
            total += cota
    if mostenitori and cote_ok and total != 1:
        add("COTE_SUMA", E, f"Cotele moștenitorilor însumează {total} în loc de 1 (100%). "
            "Probabil o cotă a fost citită greșit.", "mostenitori")


def _certificat_casatorie(doc, azi, add):
    _data_trecut(doc, "data_casatoriei", azi, add, "căsătoriei")


def _sentinta_divort(doc, azi, add):
    _data_trecut(doc, "data", azi, add, "sentinței")
    if doc.get("definitiva") is False:
        add("SENTINTA_NEDEFINITIVA", E, "Sentința nu apare ca definitivă. Banca are nevoie de "
            "sentința cu mențiunea „definitivă”.", "definitiva")


def _procura(doc, azi, add):
    emitere = _data_trecut(doc, "data_emiterii", azi, add, "emiterii")
    exp_brut = doc.get("data_expirarii")
    if exp_brut:
        exp = parse_data(exp_brut)
        if exp is None:
            add("DATA_INVALIDA", E, f"Data expirării „{exp_brut}” nu este validă.", "data_expirarii")
        elif exp < azi:
            add("PROCURA_EXPIRATA", E, f"Procura a expirat pe {format_data(exp)}.", "data_expirarii")
        elif emitere and exp < emitere:
            add("PROCURA_DATE", E, "Data expirării procurii este înaintea datei emiterii.", "data_expirarii")
    ops = doc.get("operatiuni")
    if ops not in (None, "") and not isinstance(ops, list):
        add("OPERATIUNI_FORMAT", A, "Nu am putut citi clar ce operațiuni permite procura.", "operatiuni")
    m1, m2 = str(ia(doc, "mandant.cnp") or ""), str(ia(doc, "mandatar.cnp") or "")
    if m1 and m1 == m2:
        add("PROCURA_ACEEASI_PERSOANA", E, "Titularul și împuternicitul au același CNP.", "mandatar.cnp")


VERIFICARI_SPECIFICE = {
    "buletin": _buletin,
    "certificat_deces": _certificat_deces,
    "certificat_mostenitor": _certificat_mostenitor,
    "certificat_casatorie": _certificat_casatorie,
    "sentinta_divort": _sentinta_divort,
    "procura": _procura,
}

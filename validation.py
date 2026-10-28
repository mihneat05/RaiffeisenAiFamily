"""Puntea dintre frontend (P4) și validarea reală (P3, pachetul `validare/`).

Frontendul (backend.py) cere:
    validate_document(doc)               -> {"status": "ok"|"warn"|"fail", "reasons": [str]}
    crosscheck_documents(docs, event)    -> {"status": "ok"|"warn"|"fail", "reasons": [str]}
iar P3 lucrează în formatul din schemas.py (cheie `tip_act`). Aici se face traducerea.

Merge cu ambele surse de acte:
  - P2 real   -> dict / model Pydantic în formatul schemas.py (are `tip_act`)
  - P2 mock   -> {"doc_type", "lizibil", "fields"} din mock_backend.py
La datele mock lipsesc multe câmpuri (seria, CNP-ul defunctului etc.), așa că pentru ele
nu raportăm „câmp lipsă”: restul verificărilor (CNP, expirare, nume între acte) merg normal.
"""
from __future__ import annotations

import sys
from pathlib import Path

for _p in (Path(__file__).parent, Path(__file__).parent / "p3_zana"):   # P3 stă în p3_zana/ (P1)
    if (_p / "validare").is_dir() and str(_p) not in sys.path:
        sys.path.append(str(_p))

from validare import Severitate  # noqa: E402
from validare import crosscheck_documents as _p3_crosscheck  # noqa: E402
from validare import validate_document as _p3_validate  # noqa: E402

STATUS = {Severitate.OK: "ok", Severitate.INFO: "ok", Severitate.ATENTIE: "warn", Severitate.EROARE: "fail"}
COD_IGNORAT_LA_MOCK = {"CAMP_LIPSA", "CAMP_RECOMANDAT_LIPSA", "SEMNAT_STAMPILAT"}

# evenimentele frontendului -> fluxurile P3 (casatorie_divort se decide după acte)
EVENIMENTE = {"deces": "deces", "imputernicire": "imputernicire"}

# tipurile frontendului care nu există în schemas.py
TIP_FRONTEND = {"buletin_titular": "buletin", "buletin_imputernicit": "buletin"}


# ------------------------------------------------------------------ traducere acte

def _split_nume(complet):
    """„POPESCU MARIA” -> ("POPESCU", "MARIA"). Pe actele românești numele de familie e primul."""
    parti = (complet or "").split()
    return (parti[0], " ".join(parti[1:]) or None) if parti else (None, None)


def _din_mock(doc_type, f, fisier, lizibil):
    """Format mock_backend -> format schemas.py (cât se poate din puținele câmpuri mock)."""
    tip = TIP_FRONTEND.get(doc_type, doc_type)
    nume, prenume = _split_nume(f.get("titular"))
    act = {"tip_act": tip, "fisier": fisier, "lizibil": lizibil, "_mock": True,
           "nume": nume, "prenume": prenume, "cnp": f.get("cnp"),
           "serie": f.get("serie"), "numar": f.get("numar") or f.get("nr_act"),
           "emitent": f.get("notar")}

    if tip == "buletin":
        act["data_expirarii"] = f.get("valabil_pana")
    elif tip == "certificat_deces":
        act["nume"], act["prenume"] = _split_nume(f.get("nume_decedat"))
        act["data_decesului"] = f.get("data_decesului")
    elif tip == "certificat_mostenitor":
        # mock-ul are doar titularul: îl tratăm ca singurul moștenitor
        act.update(nume=None, prenume=None, cnp=None,
                   mostenitori=[{"nume": nume, "prenume": prenume, "cnp": f.get("cnp"), "cota": "1/1"}])
    elif tip == "certificat_casatorie":
        if any(k in (fisier or "").lower() for k in ("divort", "sentinta")):
            act.update(tip_act="sentinta_divort", nume_reclamant=f.get("titular"),
                       nume_parat=f.get("sot"), data_ramanerii_definitive=f.get("data"))
        else:
            act.update(nume_sotie=f.get("titular"), nume_sot=f.get("sot"), data_casatoriei=f.get("data"))
        act.update(nume=None, prenume=None, cnp=None)
    elif tip == "procura":
        act.update(nume_mandant=f.get("titular"), nume_mandatar=f.get("imputernicit"),
                   nume=None, prenume=None, cnp=None)
    return act


def _la_format_p3(doc):
    """Orice formă primim de la frontend -> dict în formatul schemas.py."""
    if hasattr(doc, "model_dump"):
        doc = doc.model_dump()
    doc = dict(doc)
    if "tip_act" in doc:                                  # deja format P2 real
        return doc
    fields = doc.get("fields") or {}
    if hasattr(fields, "model_dump"):
        fields = fields.model_dump()
    if "tip_act" in fields:                               # P2 real, împachetat de backend.py
        return {"fisier": doc.get("filename"), **fields}
    return _din_mock(doc.get("doc_type"), fields, doc.get("filename"), doc.get("lizibil", True))


# ------------------------------------------------------------------ traducere verdict

def _la_format_frontend(verdict, mock_ids):
    probleme = [p for p in verdict.probleme
                if not (p.document in mock_ids and p.cod in COD_IGNORAT_LA_MOCK)]
    reasons = [f"Lipsește: {a}." for a in verdict.acte_lipsa] + [p.mesaj for p in probleme]
    if verdict.acte_lipsa or any(p.severitate == Severitate.EROARE for p in probleme):
        status = "fail"
    elif any(p.severitate == Severitate.ATENTIE for p in probleme):
        status = "warn"
    else:
        status = "ok"
    return {"status": status, "reasons": reasons}


def _id(act):
    return str(act.get("fisier") or act.get("tip_act") or "act")


# ------------------------------------------------------------------ API pentru frontend

def validate_document(doc):
    act = _la_format_p3(doc)
    mock_ids = {_id(act)} if act.get("_mock") else set()
    return _la_format_frontend(_p3_validate(act), mock_ids)


def crosscheck_documents(docs, event):
    acte = [_la_format_p3(d) for d in docs]
    if event == "casatorie_divort":
        flux = "divort" if any(a.get("tip_act") == "sentinta_divort" for a in acte) else "casatorie"
    else:
        flux = EVENIMENTE.get(event, event)
    mock_ids = {_id(a) for a in acte if a.get("_mock")}
    rezultat = _la_format_frontend(_p3_crosscheck(acte, flux), mock_ids)
    if rezultat["status"] == "ok" and not rezultat["reasons"]:
        rezultat["reasons"] = ["Toate actele necesare sunt încărcate și arată în regulă."]
    return rezultat

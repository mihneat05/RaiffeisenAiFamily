"""Traduce formatul lui P2 (schemas.py, cheie `tip_act`) în formatul intern al validărilor.

Singurul loc unde apar numele cheilor lui P2. Dacă P2 redenumește o cheie, se schimbă doar aici.
"""
from __future__ import annotations

from typing import Any


def _persoana(nume: Any, cnp: Any, prenume: Any = None) -> dict:
    return {"nume": nume, "prenume": prenume, "cnp": cnp}


def normalizeaza_act(doc: Any) -> dict:
    """Acceptă model Pydantic sau dict, în formatul P2 sau intern. Întoarce dict intern."""
    if hasattr(doc, "model_dump"):
        doc = doc.model_dump()
    if not isinstance(doc, dict) or "tip_act" not in doc:
        return doc  # deja în format intern
    return din_p2(doc)


def din_p2(d: dict) -> dict:
    tip = d.get("tip_act")
    out: dict = {
        "tip": tip,
        "id": d.get("fisier") or tip,
        "campuri_nesigure": d.get("campuri_nesigure") or [],
        "serie": d.get("serie"),
        "numar": d.get("numar"),
    }
    if d.get("lizibil") is False:
        out["lizibilitate"] = 0.0
    if d.get("semnat_stampilat") is not None:
        out["semnat_stampilat"] = d["semnat_stampilat"]

    if tip == "buletin":
        out.update(nume=d.get("nume"), prenume=d.get("prenume"), cnp=d.get("cnp"),
                   data_expirarii=d.get("data_expirarii"), data_nasterii=d.get("data_nasterii"))

    elif tip == "certificat_deces":
        out.update(nume=d.get("nume"), prenume=d.get("prenume"), cnp=d.get("cnp"),
                   data_decesului=d.get("data_decesului"))

    elif tip == "certificat_mostenitor":
        out.update(defunct=_persoana(d.get("nume"), d.get("cnp"), d.get("prenume")),
                   notar=d.get("emitent"), data_emiterii=d.get("data_emiterii"),
                   mostenitori=d.get("mostenitori") or [])

    elif tip == "certificat_casatorie":
        out.update(sot1=_persoana(d.get("nume_sot"), d.get("cnp_sot")),
                   sot2=_persoana(d.get("nume_sotie"), d.get("cnp_sotie")),
                   data_casatoriei=d.get("data_casatoriei"))

    elif tip == "sentinta_divort":
        definitiva = d.get("data_ramanerii_definitive")
        out.update(instanta=d.get("emitent"),
                   data=definitiva or d.get("data_emiterii"),
                   definitiva=definitiva is not None,
                   sot1=_persoana(d.get("nume_reclamant"), d.get("cnp_reclamant")),
                   sot2=_persoana(d.get("nume_parat"), d.get("cnp_parat")))

    elif tip == "procura":
        out.update(mandant=_persoana(d.get("nume_mandant"), d.get("cnp_mandant")),
                   mandatar=_persoana(d.get("nume_mandatar"), d.get("cnp_mandatar")),
                   notar=d.get("emitent"), data_emiterii=d.get("data_emiterii"),
                   data_expirarii=d.get("data_valabilitate") or d.get("data_expirarii"),
                   operatiuni=d.get("operatiuni"))
    return out

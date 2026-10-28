"""Aceleași verificări, dar cu input EXACT în formatul lui P2 (schemas.py)."""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import exemple_p2 as p2
from schemas import parse_act
from validare import Severitate, crosscheck_documents, executa_tool, validate_document

AZI = date(2026, 10, 28)
OK, INFO, ATENTIE, EROARE = Severitate.OK, Severitate.INFO, Severitate.ATENTIE, Severitate.EROARE


def coduri(v):
    return {p.cod for p in v.probleme}


def test_schemas_accepta_toate_exemplele():
    for caz in (p2.CAZ_COMPLET, p2.CAZ_CASATORIE, p2.CAZ_DIVORT, p2.CAZ_IMPUTERNICIRE):
        for act in caz:
            parse_act(act)


def test_schemas_nu_respinge_cnp_gresit():
    # schema trebuie să lase CNP-ul greșit să treacă, ca P3 să explice problema
    assert parse_act({**p2.BULETIN_MARIA, "cnp": "123"}).cnp == "123"


def test_accepta_modele_pydantic():
    modele = [parse_act(a) for a in p2.CAZ_COMPLET]
    assert crosscheck_documents(modele, "deces", AZI).status == OK


def test_caz_complet():
    v = crosscheck_documents(p2.CAZ_COMPLET, "deces", AZI)
    assert v.status == OK and v.acte_lipsa == []


def test_caz_act_lipsa():
    v = crosscheck_documents(p2.CAZ_ACT_LIPSA, "deces", AZI)
    assert v.status == EROARE and v.acte_lipsa == ["certificat de moștenitor"]


def test_caz_cnp_gresit():
    v = crosscheck_documents(p2.CAZ_CNP_GRESIT, "deces", AZI)
    assert v.status == EROARE and {"CNP_CIFRA_CONTROL", "CNP_DIFERIT"} <= coduri(v)
    assert any(p.document == "buletin_maria.jpg" for p in v.probleme)


def test_caz_nume_schimbat():
    v = crosscheck_documents(p2.CAZ_NUME_SCHIMBAT, "deces", AZI)
    assert v.status == ATENTIE and "NUME_FAMILIE_DIFERIT" in coduri(v)


def test_nelizibil_si_campuri_nesigure():
    act = {**p2.BULETIN_MARIA, "lizibil": False, "campuri_nesigure": ["cnp"]}
    v = validate_document(act, AZI)
    assert v.status == ATENTIE and {"POZA_NECLARA", "CAMP_NESIGUR"} <= coduri(v)


def test_fara_semnatura_stampila():
    v = validate_document({**p2.certificat_deces, "semnat_stampilat": False}, AZI)
    assert "SEMNAT_STAMPILAT" in coduri(v)


def test_null_nu_e_eroare_de_cod():
    act = {**p2.BULETIN_MARIA, "cnp": None, "serie": None}
    v = validate_document(act, AZI)
    assert v.status == EROARE and "CAMP_LIPSA" in coduri(v)


def test_casatorie_nume_nou_e_info():
    v = crosscheck_documents(p2.CAZ_CASATORIE, "casatorie", AZI)
    assert v.status == OK and "NUME_ACTUALIZAT" in coduri(v)


def test_divort_ok_fara_cnp_in_sentinta():
    assert crosscheck_documents(p2.CAZ_DIVORT, "divort", AZI).status == OK


def test_divort_nedefinitiv():
    docs = p2.copie(p2.CAZ_DIVORT)
    docs[0]["data_ramanerii_definitive"] = None
    assert "SENTINTA_NEDEFINITIVA" in coduri(crosscheck_documents(docs, "divort", AZI))


def test_divort_buletin_strain():
    docs = p2.copie(p2.CAZ_DIVORT)[:1] + [p2.BULETIN_ANA]
    assert "NU_E_PARTE" in coduri(crosscheck_documents(docs, "divort", AZI))


def test_imputernicire_ok():
    assert crosscheck_documents(p2.CAZ_IMPUTERNICIRE, "imputernicire", AZI).status == OK


def test_imputernicire_fara_cnp_si_operatiuni():
    docs = p2.copie(p2.CAZ_IMPUTERNICIRE)
    docs[0].update(cnp_mandant=None, cnp_mandatar=None, operatiuni=None)
    v = crosscheck_documents(docs, "imputernicire", AZI)
    assert v.status == ATENTIE and v.acte_lipsa == []  # buletinele găsite după nume


def test_procura_expirata():
    docs = p2.copie(p2.CAZ_IMPUTERNICIRE)
    docs[0]["data_valabilitate"] = "2026-01-01"
    assert "PROCURA_EXPIRATA" in coduri(crosscheck_documents(docs, "imputernicire", AZI))


def test_tool_cu_format_p2():
    rez = json.loads(executa_tool("crosscheck_documents", {"documents": p2.CAZ_CNP_GRESIT, "flux": "deces"}))
    assert rez["emoji"] == "❌"

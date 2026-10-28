import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json

import exemple as ex
from validare import Severitate, crosscheck_documents, executa_tool, validate_document
from validare.utils import parse_cota, verifica_cnp

AZI = date(2026, 10, 28)
OK, ATENTIE, EROARE = Severitate.OK, Severitate.ATENTIE, Severitate.EROARE


def coduri(verdict):
    return {p.cod for p in verdict.probleme}


# ------------------------------------------------------------ CNP

def test_cnp_valid():
    assert verifica_cnp("1500315400010", AZI) == []


def test_cnp_cifra_control_gresita():
    assert "CNP_CIFRA_CONTROL" in {c for c, _ in verifica_cnp("1500315400011", AZI)}


def test_cnp_format_si_data():
    assert verifica_cnp("12345", AZI)[0][0] == "CNP_FORMAT"
    assert "CNP_DATA" in {c for c, _ in verifica_cnp("1501345400010", AZI)}  # luna 13


def test_cote():
    assert parse_cota("1/4") == parse_cota("25%") == parse_cota(0.25) == parse_cota("0,25")


# ------------------------------------------------------------ validate_document

def test_buletin_ok():
    assert validate_document(ex.buletin(ex.SOTIE, "b"), AZI).status == OK


def test_buletin_expirat():
    v = validate_document(ex.buletin(ex.SOTIE, "b", expira="01.01.2026"), AZI)
    assert v.status == EROARE and "BULETIN_EXPIRAT" in coduri(v)


def test_buletin_expira_curand():
    v = validate_document(ex.buletin(ex.SOTIE, "b", expira="10.11.2026"), AZI)
    assert v.status == ATENTIE and "BULETIN_EXPIRA_CURAND" in coduri(v)


def test_camp_lipsa():
    doc = ex.buletin(ex.SOTIE, "b")
    del doc["cnp"]
    assert "CAMP_LIPSA" in coduri(validate_document(doc, AZI))


def test_cote_nu_insumeaza_1():
    doc = ex.copie([ex.certificat_mostenitor])[0]
    doc["mostenitori"][0]["cota"] = "1/2"
    assert "COTE_SUMA" in coduri(validate_document(doc, AZI))


def test_poza_neclara():
    doc = ex.buletin(ex.SOTIE, "b", lizibilitate=0.4)
    assert validate_document(doc, AZI).status == ATENTIE


def test_sentinta_nedefinitiva():
    doc = ex.copie(ex.CAZ_DIVORT)[0]
    doc["definitiva"] = False
    assert "SENTINTA_NEDEFINITIVA" in coduri(validate_document(doc, AZI))


def test_tip_necunoscut():
    assert validate_document({"tip": "factura"}, AZI).status == EROARE


# ------------------------------------------------------------ cele 3 cazuri de demo

def test_caz_complet():
    v = crosscheck_documents(ex.CAZ_COMPLET, "deces", AZI)
    # singura observație e ℹ️ informativă și nu strică verdictul ✅
    assert v.status == OK and v.emoji == "✅"
    assert coduri(v) == {"MOSTENITORI_FARA_BULETIN"}
    assert v.acte_lipsa == []


def test_caz_act_lipsa():
    v = crosscheck_documents(ex.CAZ_ACT_LIPSA, "deces", AZI)
    assert v.status == EROARE and v.acte_lipsa == ["certificat de moștenitor"]


def test_caz_cnp_gresit():
    v = crosscheck_documents(ex.CAZ_CNP_GRESIT, "deces", AZI)
    assert v.status == EROARE
    assert {"CNP_CIFRA_CONTROL", "CNP_DIFERIT"} <= coduri(v)


def test_caz_nume_schimbat():
    v = crosscheck_documents(ex.CAZ_NUME_SCHIMBAT, "deces", AZI)
    assert v.status == ATENTIE and "NUME_FAMILIE_DIFERIT" in coduri(v)


def test_buletin_strain_nu_e_mostenitor():
    docs = ex.copie(ex.CAZ_COMPLET) + [ex.buletin(ex.MAMA, "buletin_ana.jpg")]
    assert "NU_E_MOSTENITOR" in coduri(crosscheck_documents(docs, "deces", AZI))


def test_defuncti_diferiti():
    docs = ex.copie(ex.CAZ_COMPLET)
    docs[0]["cnp"], docs[0]["nume"], docs[0]["prenume"] = "2520812400051", "Marin", "Ana"
    assert "PERSOANA_DIFERITA" in coduri(crosscheck_documents(docs, "deces", AZI))


def test_ordine_date():
    docs = ex.copie(ex.CAZ_COMPLET)
    docs[1]["data_emiterii"] = "01.08.2026"
    assert "ORDINE_DATE" in coduri(crosscheck_documents(docs, "deces", AZI))


# ------------------------------------------------------------ celelalte fluxuri

def test_casatorie_ok():
    assert crosscheck_documents(ex.CAZ_CASATORIE, "casatorie", AZI).status == OK


def test_casatorie_buletin_vechi():
    docs = ex.copie(ex.CAZ_CASATORIE)
    docs[1]["nume"] = "Popescu"
    assert "BULETIN_NUME_VECHI" in coduri(crosscheck_documents(docs, "casatorie", AZI))


def test_divort_ok():
    assert crosscheck_documents(ex.CAZ_DIVORT, "divort", AZI).status == OK


def test_imputernicire_ok():
    assert crosscheck_documents(ex.CAZ_IMPUTERNICIRE, "imputernicire", AZI).status == OK


def test_imputernicire_lipsa_buletin_titular():
    docs = ex.copie(ex.CAZ_IMPUTERNICIRE)[:1] + [ex.buletin(ex.FIU, "b")]
    v = crosscheck_documents(docs, "imputernicire", AZI)
    assert v.status == EROARE and any("titularului" in a for a in v.acte_lipsa)


def test_procura_incetata_la_deces():
    docs = ex.copie(ex.CAZ_IMPUTERNICIRE) + [{**ex.certificat_deces, **ex.MAMA}]
    assert "PROCURA_INCETATA_DECES" in coduri(crosscheck_documents(docs, "imputernicire", AZI))


def test_flux_necunoscut():
    assert crosscheck_documents([], "credit", AZI).status == EROARE


# ------------------------------------------------------------ tools pentru P1

def test_executa_tool_intoarce_json():
    rez = json.loads(executa_tool("crosscheck_documents", {"documents": ex.CAZ_ACT_LIPSA, "flux": "deces"}))
    assert rez["status"] == "eroare" and rez["emoji"] == "❌"


def test_executa_tool_nu_pica():
    rez = json.loads(executa_tool("validate_document", {}))
    assert "eroare" in rez

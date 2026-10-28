"""Aceleași scenarii ca în exemple.py, dar EXACT în formatul lui P2 (schemas.py).

Persoane inventate, CNP-uri cu cifră de control corectă. Pot fi date lui P5 ca model pentru actele false.
"""
from copy import deepcopy

certificat_deces = {
    "tip_act": "certificat_deces", "fisier": "certificat_deces.jpg", "lizibil": True,
    "nume": "Popescu", "prenume": "Ion", "cnp": "1500315400010", "data_nasterii": "1950-03-15",
    "serie": "DD", "numar": "123456", "data_emiterii": "2026-09-03", "data_expirarii": None,
    "emitent": "Primăria Sector 1 – Stare Civilă", "semnat_stampilat": True, "campuri_nesigure": [],
    "data_decesului": "2026-09-02", "locul_decesului": "București",
}

certificat_mostenitor = {
    "tip_act": "certificat_mostenitor", "fisier": "certificat_mostenitor.pdf", "lizibil": True,
    "nume": "Popescu", "prenume": "Ion", "cnp": "1500315400010",          # defunctul
    "data_nasterii": None, "serie": None, "numar": "45/2026", "data_emiterii": "2026-10-15",
    "data_expirarii": None, "emitent": "BNP Georgescu Ana", "semnat_stampilat": True,
    "campuri_nesigure": [],
    "mostenitori": [
        {"nume": "Popescu", "prenume": "Maria", "cnp": "2600721400026", "cota": "1/4"},
        {"nume": "Popescu", "prenume": "Andrei", "cnp": "1881120400037", "cota": "3/8"},
        {"nume": "Popescu", "prenume": "Elena", "cnp": "2950105120041", "cota": "3/8"},
    ],
}


def buletin(nume, prenume, cnp, nastere, fisier, expira="2031-05-10", **extra):
    return {
        "tip_act": "buletin", "fisier": fisier, "lizibil": True, "nume": nume, "prenume": prenume,
        "cnp": cnp, "data_nasterii": nastere, "serie": "RX", "numar": "654321",
        "data_emiterii": "2021-05-10", "data_expirarii": expira, "emitent": "SPCLEP Sector 1",
        "semnat_stampilat": True, "campuri_nesigure": [], **extra,
    }


BULETIN_MARIA = buletin("Popescu", "Maria", "2600721400026", "1960-07-21", "buletin_maria.jpg")
BULETIN_ELENA = buletin("Ionescu", "Elena", "2950105120041", "1995-01-05", "buletin_elena.jpg")
BULETIN_ANDREI = buletin("Popescu", "Andrei", "1881120400037", "1988-11-20", "buletin_andrei.jpg")
BULETIN_ANA = buletin("Marin", "Ana", "2520812400051", "1952-08-12", "buletin_ana.jpg")

# ---------------------------------------------------------------- cele 3 cazuri de demo
CAZ_COMPLET = [certificat_deces, certificat_mostenitor, BULETIN_MARIA]
CAZ_ACT_LIPSA = [certificat_deces, BULETIN_MARIA]
CAZ_CNP_GRESIT = [certificat_deces, certificat_mostenitor,
                  {**BULETIN_MARIA, "cnp": "2600721400027"}]
CAZ_NUME_SCHIMBAT = [certificat_deces, certificat_mostenitor, BULETIN_ELENA]

# ---------------------------------------------------------------- celelalte fluxuri
CAZ_CASATORIE = [
    {"tip_act": "certificat_casatorie", "fisier": "certificat_casatorie.jpg", "lizibil": True,
     "nume": None, "prenume": None, "cnp": None, "data_nasterii": None, "serie": "CC", "numar": "112233",
     "data_emiterii": "2026-06-20", "data_expirarii": None, "emitent": "Primăria Cluj-Napoca",
     "semnat_stampilat": True, "campuri_nesigure": [],
     "nume_sot": "Ionescu Mihai", "cnp_sot": "1920304400057",
     "nume_sotie": "Popescu Elena", "cnp_sotie": "2950105120041", "data_casatoriei": "2026-06-20"},
    BULETIN_ELENA,
]

CAZ_DIVORT = [
    {"tip_act": "sentinta_divort", "fisier": "sentinta.pdf", "lizibil": True,
     "nume": None, "prenume": None, "cnp": None, "data_nasterii": None, "serie": None,
     "numar": "1234/299/2026", "data_emiterii": "2026-07-10", "data_expirarii": None,
     "emitent": "Judecătoria Sector 1", "semnat_stampilat": True, "campuri_nesigure": [],
     "data_ramanerii_definitive": "2026-08-15",
     "nume_reclamant": "Popescu Andrei", "nume_parat": "Popescu Ioana"},
    BULETIN_ANDREI,
]

CAZ_IMPUTERNICIRE = [
    {"tip_act": "procura", "fisier": "procura.pdf", "lizibil": True,
     "nume": None, "prenume": None, "cnp": None, "data_nasterii": None, "serie": None,
     "numar": "78/2026", "data_emiterii": "2026-10-01", "data_expirarii": None,
     "emitent": "BNP Georgescu Ana", "semnat_stampilat": True, "campuri_nesigure": [],
     "nume_mandant": "Marin Ana", "nume_mandatar": "Popescu Andrei",
     "cnp_mandant": "2520812400051", "cnp_mandatar": "1881120400037",
     "data_valabilitate": "2029-10-01", "operatiuni": ["plăți", "retrageri numerar"]},
    BULETIN_ANA, BULETIN_ANDREI,
]


def copie(caz):
    return deepcopy(caz)

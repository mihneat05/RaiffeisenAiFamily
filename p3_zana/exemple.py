"""Date de test sintetice (persoane INVENTATE), în formatul pe care îl produce read_document.

CNP-urile au cifra de control corectă. Le poate refolosi P5 pentru actele false.
Scenariile corespund celor 3 cazuri de demo: complet / act lipsă / CNP greșit.
"""
from copy import deepcopy

DEFUNCT = {"nume": "Popescu", "prenume": "Ion", "cnp": "1500315400010"}
SOTIE = {"nume": "Popescu", "prenume": "Maria", "cnp": "2600721400026"}
FIU = {"nume": "Popescu", "prenume": "Andrei", "cnp": "1881120400037"}
FIICA = {"nume": "Ionescu", "prenume": "Elena", "cnp": "2950105120041"}   # născută Popescu
MAMA = {"nume": "Marin", "prenume": "Ana", "cnp": "2520812400051"}

certificat_deces = {
    "id": "certificat_deces.jpg", "tip": "certificat_deces", **DEFUNCT,
    "data_decesului": "02.09.2026", "serie": "DD", "numar": "123456",
    "are_stampila": True, "lizibilitate": 0.95,
}

certificat_mostenitor = {
    "id": "certificat_mostenitor.pdf", "tip": "certificat_mostenitor",
    "defunct": DEFUNCT, "notar": "BNP Georgescu Ana", "numar": "45/2026",
    "data_emiterii": "15.10.2026",
    "mostenitori": [
        {**SOTIE, "cota": "1/4"},
        {**FIU, "cota": "3/8"},
        {**FIICA, "nume": "Popescu", "cota": "3/8"},  # pe certificat apare cu numele de fată
    ],
    "are_stampila": True, "are_semnatura": True,
}


def buletin(persoana: dict, id_: str, expira: str = "10.05.2031", **extra) -> dict:
    return {"id": id_, "tip": "buletin", **persoana, "serie": "RX", "numar": "654321",
            "data_expirarii": expira, **extra}


# ---------------------------------------------------------------- scenarii deces

CAZ_COMPLET = [certificat_deces, certificat_mostenitor, buletin(SOTIE, "buletin_maria.jpg")]

CAZ_ACT_LIPSA = [certificat_deces, buletin(SOTIE, "buletin_maria.jpg")]   # lipsește certificatul de moștenitor

_buletin_cnp_gresit = buletin(SOTIE, "buletin_maria.jpg")
_buletin_cnp_gresit["cnp"] = "2600721400027"                              # ultima cifră greșită
CAZ_CNP_GRESIT = [certificat_deces, certificat_mostenitor, _buletin_cnp_gresit]

# bonus pentru demo: fiica s-a căsătorit -> nume diferit, același CNP -> ⚠️
CAZ_NUME_SCHIMBAT = [certificat_deces, certificat_mostenitor, buletin(FIICA, "buletin_elena.jpg")]

CAZ_BULETIN_EXPIRAT = [certificat_deces, certificat_mostenitor,
                       buletin(SOTIE, "buletin_maria.jpg", expira="01.03.2025")]

# ---------------------------------------------------------------- alte fluxuri

CAZ_CASATORIE = [
    {"id": "certificat_casatorie.jpg", "tip": "certificat_casatorie",
     "sot1": {"nume": "Ionescu", "prenume": "Mihai", "cnp": "1920304400057"},
     "sot2": {**FIICA, "nume": "Popescu", "nume_dupa_casatorie": "Ionescu"},
     "data_casatoriei": "20.06.2026", "serie": "CC", "numar": "112233"},
    buletin(FIICA, "buletin_elena_nou.jpg"),
]

CAZ_DIVORT = [
    {"id": "sentinta.pdf", "tip": "sentinta_divort", "instanta": "Judecătoria Sector 1",
     "numar": "1234/299/2026", "data": "10.07.2026", "definitiva": True,
     "sot1": FIU, "sot2": {"nume": "Popescu", "prenume": "Ioana", "cnp": "2900101400030",
                           "nume_dupa_divort": "Stan"}},
    buletin(FIU, "buletin_andrei.jpg"),
]

CAZ_IMPUTERNICIRE = [
    {"id": "procura.pdf", "tip": "procura", "mandant": MAMA, "mandatar": FIU,
     "notar": "BNP Georgescu Ana", "numar": "78/2026", "data_emiterii": "01.10.2026",
     "data_expirarii": "01.10.2029", "operatiuni": ["plăți", "retrageri numerar"]},
    buletin(MAMA, "buletin_ana.jpg"),
    buletin(FIU, "buletin_andrei.jpg"),
]


def copie(caz: list[dict]) -> list[dict]:
    return deepcopy(caz)

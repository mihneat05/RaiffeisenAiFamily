"""Regulile de business, într-un singur loc: ce câmpuri are fiecare act și ce acte cere fiecare flux.

Formatul JSON pe care îl produce P2 (read_document) este descris în README.md.
Ca să adăugați un tip de act sau un flux nou, modificați doar acest fișier.
"""

# câmpuri obligatorii pe tip de act (căi cu punct pentru obiecte imbricate)
CAMPURI_OBLIGATORII: dict[str, list[str]] = {
    "buletin": ["nume", "prenume", "cnp", "serie", "numar", "data_expirarii"],
    "certificat_deces": ["nume", "prenume", "cnp", "data_decesului", "serie", "numar"],
    "certificat_mostenitor": ["defunct.nume", "defunct.cnp", "data_emiterii", "mostenitori"],
    # în formatul P2 soții / părțile / mandanții au doar nume complet (prenume opțional)
    "certificat_casatorie": ["sot1.nume", "sot1.cnp", "sot2.nume", "sot2.cnp", "data_casatoriei"],
    "sentinta_divort": ["data", "sot1.nume", "sot2.nume"],
    "procura": ["mandant.nume", "mandatar.nume", "data_emiterii"],
}

# câmpuri care nu blochează dacă lipsesc, dar merită un ⚠️
CAMPURI_RECOMANDATE: dict[str, dict[str, str]] = {
    "procura": {"operatiuni": "Nu am putut citi ce operațiuni permite procura. Consilierul va verifica."},
    "certificat_mostenitor": {"notar": "Nu am putut citi notarul care a emis certificatul."},
}

# unde se află CNP-urile în fiecare tip de act
CAI_CNP: dict[str, list[str]] = {
    "buletin": ["cnp"],
    "certificat_deces": ["cnp"],
    "certificat_mostenitor": ["defunct.cnp"],  # moștenitorii sunt verificați separat
    "certificat_casatorie": ["sot1.cnp", "sot2.cnp"],
    "sentinta_divort": ["sot1.cnp", "sot2.cnp"],
    "procura": ["mandant.cnp", "mandatar.cnp"],
}

NUME_ACTE = {
    "buletin": "carte de identitate (buletin)",
    "certificat_deces": "certificat de deces",
    "certificat_mostenitor": "certificat de moștenitor",
    "certificat_casatorie": "certificat de căsătorie",
    "sentinta_divort": "sentință de divorț definitivă",
    "procura": "procură notarială",
}

# actele cerute pe flux: tip -> câte exemplare minim
ACTE_NECESARE: dict[str, dict[str, int]] = {
    "deces": {"certificat_deces": 1, "certificat_mostenitor": 1, "buletin": 1},
    "casatorie": {"certificat_casatorie": 1, "buletin": 1},
    "divort": {"sentinta_divort": 1, "buletin": 1},
    "imputernicire": {"procura": 1, "buletin": 2},  # titular + împuternicit
}

ZILE_AVERTIZARE_EXPIRARE = 30   # buletin care expiră curând -> ⚠️
SCOR_MINIM_LIZIBILITATE = 0.7   # sub acest scor (dacă P2 îl trimite) -> ⚠️

"""Rulează: python demo.py  -> verdictul pentru fiecare scenariu (input în formatul lui P2)."""
import exemple_p2 as ex
from validare import crosscheck_documents

SCENARII = [
    ("Deces – dosar complet", ex.CAZ_COMPLET, "deces"),
    ("Deces – lipsește un act", ex.CAZ_ACT_LIPSA, "deces"),
    ("Deces – CNP greșit pe buletin", ex.CAZ_CNP_GRESIT, "deces"),
    ("Deces – nume schimbat după căsătorie", ex.CAZ_NUME_SCHIMBAT, "deces"),
    ("Căsătorie", ex.CAZ_CASATORIE, "casatorie"),
    ("Divorț", ex.CAZ_DIVORT, "divort"),
    ("Împuternicire", ex.CAZ_IMPUTERNICIRE, "imputernicire"),
]

EMOJI = {"eroare": "❌", "atentie": "⚠️", "info": "ℹ️"}

for titlu, docs, flux in SCENARII:
    v = crosscheck_documents(docs, flux)
    print(f"\n=== {titlu} ===\n{v.emoji} {v.titlu}")
    for a in v.acte_lipsa:
        print(f"   📄 Lipsește: {a}")
    for p in v.probleme:
        print(f"   {EMOJI[p.severitate.value]} [{p.cod}] {p.mesaj}")

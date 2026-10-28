"""
test_p2.py - ruleaza read_document pe toate actele din folderul test_acte/
si afiseaza un rezumat (CNP-urile sunt mascate).

Folosire:  python test_p2.py
"""
import json
from pathlib import Path

from read_document import mask_cnp, read_document

FOLDER = Path("test_acte")
EXT = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


def main():
    if not FOLDER.exists():
        FOLDER.mkdir()
        print(f"Am creat folderul '{FOLDER}'. Pune acolo pozele / PDF-urile de test si ruleaza din nou.")
        return

    fisiere = sorted(f for f in FOLDER.iterdir() if f.suffix.lower() in EXT)
    if not fisiere:
        print(f"Folderul '{FOLDER}' e gol. Adauga poze de test.")
        return

    for f in fisiere:
        print("=" * 60)
        print(f.name)
        rezultat = read_document(str(f))
        print(mask_cnp(json.dumps(rezultat, indent=2, ensure_ascii=False)))


if __name__ == "__main__":
    main()

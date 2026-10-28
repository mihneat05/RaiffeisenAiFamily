"""
test_p2.py - ruleaza read_document pe cazurile din date_test/ si compara cu rezultate_asteptate.json.

Folosire:
    python test_p2.py                 # cauta date_test/ langa script
    python test_p2.py cale/date_test  # alt folder

Structura acceptata pentru date_test/:
    date_test/
        rezultate_asteptate.json
        caz_complet/      act1.jpg, act2.pdf ...
        caz_act_lipsa/    ...
        caz_cnp_gresit/   ...
    (merg si fisiere puse direct in date_test/, fara subfoldere)

rezultate_asteptate.json - oricare dintre forme:
    {"caz_complet": {"act1.jpg": {"tip_act": "buletin", "cnp": "..."}, ...}, ...}
    {"act1.jpg": {"tip_act": "buletin", ...}, ...}
    [{"fisier": "act1.jpg", "tip_act": "buletin", ...}, ...]
Se compara DOAR campurile prezente in asteptari. Nume/texte: fara diacritice, case-insensitive.
"""
import json
import sys
import unicodedata
from pathlib import Path

from read_document import read_document

EXT = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".heic", ".bmp"}


def norm(v):
    if isinstance(v, str):
        v = unicodedata.normalize("NFKD", v).encode("ascii", "ignore").decode()
        return " ".join(v.lower().replace("-", " ").split())
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    return v


# Formatul lui P5 (date_test/rezultate_asteptate.json): nume de campuri din knowledge base
# -> le traducem in cheile din schemas.py. Campurile compuse (ex. serie_numar_certificat) se sar.
P5_TIP = {"act_identitate_solicitant": "buletin", "act_identitate_nou": "buletin",
          "act_identitate_titular": "buletin", "act_identitate_imputernicit": "buletin",
          "procura_notariala": "procura", "certificat_sau_sentinta_divort": "sentinta_divort"}
P5_CAMP = {"nume_defunct": "nume", "prenume_defunct": "prenume", "cnp_defunct": "cnp",
           "data_eliberarii": "data_emiterii", "numar_certificat": "numar",
           "semnatura_stampila": "semnat_stampilat"}
P5_SKIP = {"serie_numar_certificat", "notar"}


def _din_p5(caz: dict) -> dict:
    out = {}
    for fname, act in caz["acte_incarcate"].items():
        exp = {"tip_act": P5_TIP.get(act["tip_act"], act["tip_act"])}
        for k, v in act.get("campuri", {}).items():
            if k in P5_SKIP:
                continue
            if k == "mostenitori":            # comparam doar CNP-urile mostenitorilor
                exp["_cnp_mostenitori"] = sorted(m.get("cnp") for m in v)
                continue
            if k == "nume_defunct" and isinstance(v, str) and " " in v:
                continue                      # "NUME PRENUME" intr-un singur camp
            exp[P5_CAMP.get(k, k)] = v
        out[f"{caz['caz']}/{fname}"] = exp
    return out


def flatten_expected(data) -> dict[str, dict]:
    """Intoarce {cale_relativa_sau_nume_fisier: asteptari}."""
    out = {}
    if isinstance(data, list) and data and "acte_incarcate" in data[0]:   # formatul P5
        for caz in data:
            out.update(_din_p5(caz))
        return out
    if isinstance(data, list):
        for item in data:
            out[item["fisier"]] = {k: v for k, v in item.items() if k != "fisier"}
        return out
    for key, val in data.items():
        if isinstance(val, dict) and val and all(isinstance(x, dict) for x in val.values()) \
                and "tip_act" not in val:
            for fname, exp in val.items():           # forma pe cazuri
                out[f"{key}/{fname}"] = exp
        elif isinstance(val, list) and val and isinstance(val[0], dict) and "fisier" in val[0]:
            for item in val:
                out[f"{key}/{item['fisier']}"] = {k: v for k, v in item.items() if k != "fisier"}
        else:
            out[key] = val
    return out


def find_expected(expected: dict, rel: str) -> dict | None:
    if rel in expected:
        return expected[rel]
    name = Path(rel).name
    return expected.get(name)


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "date_test"
    if not root.is_dir():
        sys.exit(f"Nu exista folderul {root}")
    exp_file = root / "rezultate_asteptate.json"
    if not exp_file.exists():
        exp_file = root.parent / "rezultate_asteptate.json"
    expected = flatten_expected(json.loads(exp_file.read_text(encoding="utf-8"))) \
        if exp_file.exists() else {}
    if not expected:
        print(f"ATENTIE: nu am gasit asteptari in {exp_file}, doar afisez rezultatele.\n")

    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in EXT)
    total_ok = total_campuri = 0
    fails = []
    for f in files:
        rel = f.relative_to(root).as_posix()
        rez = read_document(str(f))
        exp = find_expected(expected, rel)
        print(f"\n=== {rel}  -> tip_act={rez.get('tip_act')} lizibil={rez.get('lizibil')}"
              + (f" eroare={rez['eroare']}" if "eroare" in rez else ""))
        if exp is None:
            print(json.dumps(rez, indent=2, ensure_ascii=False))
            continue
        if "_cnp_mostenitori" in exp:
            rez = dict(rez, _cnp_mostenitori=sorted(m.get("cnp") for m in rez.get("mostenitori") or []))
        for camp, val in exp.items():
            total_campuri += 1
            ok = norm(rez.get(camp)) == norm(val)
            total_ok += ok
            mark = "OK  " if ok else "FAIL"
            print(f"  {mark} {camp}: asteptat={val!r} primit={rez.get(camp)!r}")
            if not ok:
                fails.append((rel, camp))

    lipsa = [k for k in expected if not any(
        f.relative_to(root).as_posix() == k or f.name == Path(k).name for f in files)]
    print("\n" + "=" * 60)
    print(f"Fisiere: {len(files)} | Campuri corecte: {total_ok}/{total_campuri}")
    if lipsa:
        print("In asteptari dar fara fisier:", ", ".join(lipsa))
    for rel, camp in fails:
        print(f"  FAIL {rel} :: {camp}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()

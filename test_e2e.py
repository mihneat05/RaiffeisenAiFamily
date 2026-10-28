"""test_e2e.py - test cap-coadă pe actele REALE (poze) din date_test/.

Pentru fiecare caz: citește pozele cu read_document (P2, LLM vision) -> verifică (P3)
-> compară verdictul cu date_test/rezultate_asteptate.json (P5).
Nu folosește chat-ul agentului, deci e rapid și repetabil.

Rulare:  python test_e2e.py
Rezultatele detaliate (CNP mascat) se salvează în date_test/rezultate_obtinute.json
"""
import json
import time
from pathlib import Path

from agent import Session, mask_cnp, read_document, run_check

ROOT = Path(__file__).parent
CAZURI = json.loads((ROOT / "date_test" / "rezultate_asteptate.json").read_text(encoding="utf-8"))
EXT = {".png", ".jpg", ".jpeg", ".pdf"}

rezultate, trecute = [], 0
for caz in CAZURI:
    folder = ROOT / "date_test" / caz["caz"]
    asteptat = caz["rezultat_asteptat"]["verdict"]
    print(f"\n=== {caz['caz']}  (așteptat: {asteptat}) ===")

    s = Session()
    s.flux, s.scenariu = caz["flux_id"], caz["scenariu"]
    t0 = time.time()
    for f in sorted(p for p in folder.iterdir() if p.suffix.lower() in EXT):
        doc = read_document(str(f))
        s.docs.append(doc)
        print(f"  citit {f.name:28s} -> {doc.get('tip_act', '?'):22s} {doc.get('eroare', '')}")
    v = run_check(s)
    durata = time.time() - t0

    ok = v["status"] == asteptat
    trecute += ok
    print(f"  verdict: {v['status']}  {'✅ CORECT' if ok else '❌ GREȘIT'}   ({durata:.1f} s, verificări {v['verificari']})")
    for a in v["acte_lipsa"]:
        print(f"    lipsește: {a}")
    for p in v["probleme"]:
        print(f"    [{p['severitate']}] {p['cod']}: {p['mesaj']}")
    rezultate.append({"caz": caz["caz"], "asteptat": asteptat, "obtinut": v["status"], "corect": ok,
                      "secunde": round(durata, 1), "verdict": v, "acte": s.docs})

out = ROOT / "date_test" / "rezultate_obtinute.json"
out.write_text(mask_cnp(json.dumps(rezultate, ensure_ascii=False, indent=2, default=str)), encoding="utf-8")
print(f"\n==> {trecute}/{len(CAZURI)} cazuri corecte. Timp mediu / dosar: "
      f"{sum(r['secunde'] for r in rezultate) / len(rezultate):.1f} s.  Detalii: {out.relative_to(ROOT)}")

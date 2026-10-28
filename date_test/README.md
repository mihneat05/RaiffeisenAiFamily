# Date de test – acte sintetice (P5)

Acte **false**, marcate SPECIMEN, cu persoane inventate. Doar pentru testare.
Flux: **deces / succesiune**, scenariul `ridicare_bani` din `knowledge_base/kb_deces_succesiune.json`.

| Folder | Ce conține | Verdict așteptat |
|---|---|---|
| `caz1_complet/` | certificat deces + certificat moștenitor + buletin, toate corecte | `gata` ✅ |
| `caz2_act_lipsa/` | lipsește certificatul de moștenitor | `lipseste` ❌ |
| `caz3_cnp_gresit/` | CNP-ul de pe buletin are cifra de control greșită și nu se potrivește cu certificatul de moștenitor | `de_verificat` ⚠ |

## Pentru cine

- **P2**: compară ce extrage `read_document` din fiecare poză cu `campuri` din `rezultate_asteptate.json`.
- **P3**: compară verdictul din `validate_document` / `crosscheck_documents` cu `rezultat_asteptat`.
- **P1**: test cap-coadă al agentului cu cele 3 cazuri.

Numele câmpurilor sunt aceleași ca în `campuri_cheie` din knowledge base.

## Regenerare

`python genereaza_acte.py` (are nevoie de `pip install pillow`).

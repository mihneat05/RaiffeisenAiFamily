# Frontend (P4): Streamlit

```
pip install -r requirements.txt
streamlit run app.py
```

Merge imediat, fără restul echipei: tot ce lipsește e înlocuit de `mock_backend.py`.
În sidebar, la „Stare module”, vezi ce e real (🟢) și ce e încă mock (🟡).

## Fișiere

| Fișier | Ce face |
|---|---|
| `app.py` | UI-ul: chat, upload, checklist live, verdict, PDF, cardul cu sucursala |
| `backend.py` | **Singurul punct de legătură** cu P1/P2/P3/P5. Folosește modulul real dacă există, altfel mock-ul |
| `mock_backend.py` | Versiuni false ale funcțiilor colegilor, cu CNP verificat real (cifra de control) |
| `pdf_export.py` | Checklist-ul de printat (fpdf2, cu diacritice) |
| `demo_files/` | Fișiere goale cu nume care declanșează cazurile în mock (complet, CNP greșit, expirat, neclar) |

## Contractul cu echipa (de confirmat cu P1)

Pune modulele lângă `app.py` cu numele și formele astea și frontendul le preia singur:

```python
# agent.py (P1)
agent_turn(message: str, ctx: dict) -> {"reply": str, "event": "deces"|"casatorie_divort"|"imputernicire"|None}
#   ctx = {"event", "docs": [{"doc_type","label","status","reasons"}], "verdict", "history"}

# reader.py (P2)
read_document(data: bytes, filename: str) -> {"doc_type": str, "lizibil": bool, "fields": {...}}
#   poate întoarce și un model Pydantic; backend.py face model_dump()

# validation.py (P3)
validate_document(doc) -> {"status": "ok"|"warn"|"fail", "reasons": [str]}
crosscheck_documents(docs, event) -> {"status": "ok"|"warn"|"fail", "reasons": [str]}

# knowledge.py (P5)
required_docs(event) -> [{"type": str, "label": str}]
```

`doc_type` trebuie să fie același la P2, P3 și P5: `buletin`, `buletin_titular`, `buletin_imputernicit`,
`certificat_deces`, `certificat_mostenitor`, `certificat_casatorie`, `procura`.

Dacă cineva are alte nume sau semnături, se schimbă doar `backend.py`.

`USE_MOCK=1 streamlit run app.py` forțează mock-urile (util ca plasă de siguranță la demo).

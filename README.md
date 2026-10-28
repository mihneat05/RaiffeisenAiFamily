# P3 – Validare + Crosscheck (Raiffeisen Family Agent)

Cod determinist, **fără LLM**. Primește JSON-ul actelor citite de P2 și întoarce verdictul ✅ / ⚠️ / ❌ cu motive în română.

```
validare/
  reguli.py      ← TOATE regulile de business (câmpuri, acte pe flux). Aici modificați.
  utils.py       ← CNP (cifra de control, dată, județ), date, nume fără diacritice, cote
  validate.py    ← validate_document(doc)           – un act singur
  crosscheck.py  ← crosscheck_documents(docs, flux) – actele între ele + acte lipsă
  models.py      ← Verdict, Problema, Severitate
  tools.py       ← TOOLS (schema pentru LLM) + executa_tool() pentru P1
  adaptor.py     ← traduce formatul P2 (schemas.py) în formatul intern
schemas.py       ← modelele Pydantic comune cu P2 (contractul de date)
exemple_p2.py    ← cele 3 cazuri de demo în formatul P2 (complet / act lipsă / CNP greșit) + alte fluxuri
exemple.py       ← aceleași date în formatul intern (folosite de testele vechi)
demo.py          ← python demo.py
tests/           ← python -m pytest -q   (46 teste)
```

Cerințe: Python 3.10+, `pydantic>=2`.

## Pentru P1 (agent)

```python
from validare import TOOLS, executa_tool

tools = TOOLS + [read_document_tool, ...]          # format Anthropic: name/description/input_schema
# în bucla de tool calling:
rezultat_text = executa_tool(tool_use.name, tool_use.input)   # întoarce JSON string, nu aruncă excepții
```

Ordinea recomandată în promptul de sistem: `read_document` pe fiecare act → `validate_document` pe fiecare (feedback rapid: „poza e neclară”) → `crosscheck_documents` la final → agentul explică verdictul.

Verdictul (ce primește LLM-ul):

```json
{
  "status": "eroare",            // "ok" | "atentie" | "eroare"
  "emoji": "❌",
  "titlu": "Lipsește sau e greșit ceva",
  "acte_lipsa": ["certificat de moștenitor"],
  "probleme": [
    {"cod": "CNP_CIFRA_CONTROL", "severitate": "eroare",
     "mesaj": "Cifra de control a CNP-ului nu se potrivește…",
     "document": "buletin_maria.jpg", "camp": "cnp"}
  ]
}
```

Severități: `eroare` ❌ blochează · `atentie` ⚠️ verifică un om · `info` ℹ️ sfat, nu schimbă verdictul.

## Pentru P2 (citire acte): formatul este `schemas.py`

Contractul comun e **`schemas.py`**, cu cheile stabilite de P2 (`tip_act`, `lizibil`, `nume`, `prenume`, `cnp`,
`data_nasterii`, `serie`, `numar`, `data_emiterii`, `data_expirarii`, `emitent`, `semnat_stampilat`,
`campuri_nesigure` + cheile specifice fiecărui act). P2 îl folosește pentru output, P3 îl primește direct.
Formate: CNP string de 13 cifre · date `YYYY-MM-DD` · lipsă = `null` · booleeni `true`/`false`.

Câmpurile marcate `# PROPUNERE P3` lipseau din lista inițială și trebuie confirmate:

| Act | Ce adaugă P3 | De ce |
|---|---|---|
| toate | `fisier` | mesajele pot spune *pe care poză* e problema |
| `certificat_mostenitor` | tot actul: `nume/prenume/cnp` = defunctul + `mostenitori: [{nume, prenume, cnp, cota}]` | e actul central la deces; fără el nu putem verifica cine are dreptul la bani |
| `procura` | `cnp_mandant`, `cnp_mandatar`, `operatiuni` | CNP-urile apar pe procura notarială; `operatiuni` = „ce poate face împuternicitul” |
| `sentinta_divort` | `cnp_reclamant`, `cnp_parat` *(opționale)* | dacă lipsesc, potrivim doar după nume |

Toate validările acceptă formatul P2 ca dict **sau** ca model Pydantic. Traducerea în formatul intern e în
`validare/adaptor.py`: dacă P2 redenumește o cheie, se schimbă doar acolo.

Exemple complete în formatul P2: `exemple_p2.py` (și pentru P5, ca model pentru actele false).

## Ce verifică

**Pe fiecare act:** câmpuri lipsă · `lizibil: false` și `campuri_nesigure` → ⚠️ · CNP (13 cifre, cifra de control, dată de naștere reală, cod județ) · buletin expirat / expiră în 30 de zile · data nașterii vs. CNP · date în viitor · cotele moștenitorilor însumează 100% · sentință definitivă · procură expirată · poză neclară · ștampilă/semnătură lipsă (doar ⚠️, *verificare vizuală preliminară*, nu garantează autenticitatea).

**Între acte, pe flux:**
- **deces:** același defunct pe certificatul de deces și cel de moștenitor · certificatul de moștenitor emis după deces · buletinul aparține unui moștenitor · ℹ️ ceilalți moștenitori
- **casatorie:** buletinul aparține unui soț · numele nou pe buletin = ℹ️ normal, se actualizează
- **divort:** buletinul aparține unei părți din sentință
- **imputernicire:** buletinele titularului și împuternicitului · procura încetează dacă titularul a decedat

Peste tot: CNP diferit cu același nume → ❌ · CNP identic cu nume de familie diferit → ⚠️ (posibilă căsătorie).

Fluxuri: `deces`, `casatorie`, `divort`, `imputernicire`.

## Team Contributions

### P4 – Anastasia Radu
- Contributed to the implementation and integration of the P4 module.

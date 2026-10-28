"""Implementări false pentru P1 (agent), P2 (citire acte), P3 (validare) și P5 (conținut).

Frontendul rulează cu ele până sunt gata modulele reale. Se comportă după numele
fișierului încărcat, ca să poți simula cele 3 cazuri de demo:
    buletin.jpg, certificat_deces.pdf, certificat_mostenitor.pdf  -> complet
    buletin_cnp_gresit.jpg                                         -> CNP greșit
    buletin_expirat.jpg / buletin_neclar.jpg / buletin_alt_nume.jpg
"""
import unicodedata
from datetime import date

EVENTS = {
    "deces": "Deces / Succesiune",
    "casatorie_divort": "Căsătorie / Divorț",
    "imputernicire": "Împuternicire",
}

REQUIRED_DOCS = {
    "deces": [
        {"type": "certificat_deces", "label": "Certificat de deces"},
        {"type": "certificat_mostenitor", "label": "Certificat de moștenitor / act notarial"},
        {"type": "buletin", "label": "Buletinul tău"},
    ],
    "casatorie_divort": [
        {"type": "certificat_casatorie", "label": "Certificat de căsătorie / sentință de divorț definitivă"},
        {"type": "buletin", "label": "Buletinul nou (cu numele actualizat)"},
    ],
    "imputernicire": [
        {"type": "procura", "label": "Procură notarială"},
        {"type": "buletin_titular", "label": "Buletinul titularului de cont"},
        {"type": "buletin_imputernicit", "label": "Buletinul împuternicitului"},
    ],
}

DOC_LABELS = {d["type"]: d["label"] for docs in REQUIRED_DOCS.values() for d in docs}

# Ordinea contează: "buletin_titular.jpg" conține și "buletin".
_FILENAME_KEYWORDS = [
    ("mostenitor", "certificat_mostenitor"),
    ("succesiune", "certificat_mostenitor"),
    ("deces", "certificat_deces"),
    ("casatorie", "certificat_casatorie"),
    ("divort", "certificat_casatorie"),
    ("sentinta", "certificat_casatorie"),
    ("procura", "procura"),
    ("titular", "buletin_titular"),
    ("imputernicit", "buletin_imputernicit"),
    ("buletin", "buletin"),
    ("ci_", "buletin"),
]

_EVENT_KEYWORDS = {
    "deces": ["deces", "decedat", "murit", "mostenire", "mostenitor", "succesiune", "pierdut"],
    "casatorie_divort": ["casator", "divort", "nume nou", "schimbat numele", "nunta"],
    "imputernicire": ["procur", "imputernic", "in numele", "bolnav", "spital"],
}

BRANCHES = [
    {
        "name": "Raiffeisen Bank — Agenția Unirii",
        "address": "Bd. Unirii nr. 1, București",
        "hours": "Luni–Vineri, 09:00–17:00",
        "distance": "1,2 km",
        "booking_url": "https://www.raiffeisen.ro/",
    },
]


def strip_diacritics(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


# --- CNP --------------------------------------------------------------------

_CNP_WEIGHTS = "279146358279"


def cnp_control_digit(first12):
    total = sum(int(a) * int(b) for a, b in zip(first12, _CNP_WEIGHTS)) % 11
    return 1 if total == 10 else total


def cnp_is_valid(cnp):
    return (
        isinstance(cnp, str)
        and len(cnp) == 13
        and cnp.isdigit()
        and int(cnp[12]) == cnp_control_digit(cnp[:12])
    )


def _fake_cnp(broken=False):
    first12 = "285031540012"
    control = cnp_control_digit(first12)
    return first12 + str((control + 1) % 10 if broken else control)


# --- P2: read_document --------------------------------------------------------

def read_document(data, filename):
    """Mock pentru P2. Întoarce {"doc_type", "lizibil", "fields"}."""
    name = strip_diacritics(filename)
    doc_type = next((t for kw, t in _FILENAME_KEYWORDS if kw in name), "necunoscut")
    client = "IONESCU ANA" if "alt_nume" in name else "POPESCU MARIA"

    if doc_type.startswith("buletin"):
        holder = "POPESCU ION" if doc_type == "buletin_imputernicit" else client
        fields = {
            "titular": holder,
            "cnp": _fake_cnp(broken="cnp_gresit" in name),
            "serie": "RX",
            "numar": "123456",
            "valabil_pana": "2023-01-10" if "expirat" in name else "2031-05-20",
        }
    elif doc_type == "certificat_deces":
        fields = {"nume_decedat": "POPESCU GHEORGHE", "data_decesului": "2026-09-02", "nr_act": "1452"}
    elif doc_type == "certificat_mostenitor":
        fields = {"titular": client, "cnp": _fake_cnp(), "notar": "BNP Vasilescu", "nr_act": "88/2026"}
    elif doc_type == "certificat_casatorie":
        fields = {"titular": client, "sot": "POPESCU ANDREI", "data": "2026-06-14", "nr_act": "301"}
    elif doc_type == "procura":
        fields = {"titular": client, "imputernicit": "POPESCU ION", "notar": "BNP Vasilescu", "nr_act": "120/2026"}
    else:
        fields = {}

    return {"doc_type": doc_type, "lizibil": "neclar" not in name, "fields": fields}


# --- P3: validate_document / crosscheck_documents -----------------------------

def validate_document(doc):
    """Mock pentru P3. Întoarce {"status": "ok"|"warn"|"fail", "reasons": [...]}."""
    fails, warns = [], []
    fields = doc.get("fields", {})

    if doc.get("doc_type") == "necunoscut":
        warns.append("Nu am recunoscut tipul actului.")
    if not doc.get("lizibil", True):
        warns.append("Poza nu e clară. Refă-o la lumină bună, fără reflexii.")
    if "cnp" in fields and not cnp_is_valid(fields["cnp"]):
        fails.append("CNP-ul nu e valid (cifra de control nu se potrivește).")
    expiry = fields.get("valabil_pana")
    if expiry and date.fromisoformat(expiry) < date.today():
        fails.append(f"Buletinul a expirat pe {expiry}.")

    status = "fail" if fails else "warn" if warns else "ok"
    return {"status": status, "reasons": fails + warns}


def crosscheck_documents(docs, event):
    """Mock pentru P3. docs = lista întoarsă de backend.process_upload."""
    fails, warns = [], []
    present = {d["doc_type"] for d in docs}

    for req in REQUIRED_DOCS[event]:
        if req["type"] not in present:
            fails.append(f"Lipsește: {req['label']}.")
    for d in docs:
        if d["status"] == "fail":
            fails.append(f"{d['label']}: {' '.join(d['reasons'])}")
        elif d["status"] == "warn":
            warns.append(f"{d['label']}: {' '.join(d['reasons'])}")

    names = {d["fields"]["titular"] for d in docs if d["fields"].get("titular") and d["doc_type"] != "buletin_imputernicit"}
    if len(names) > 1:
        warns.append(f"Numele diferă între acte: {' / '.join(sorted(names))}.")

    if fails:
        return {"status": "fail", "reasons": fails + warns}
    if warns:
        return {"status": "warn", "reasons": warns}
    return {"status": "ok", "reasons": ["Toate actele necesare sunt încărcate și arată în regulă."]}


# --- P5: conținut ---------------------------------------------------------------

def required_docs(event):
    return REQUIRED_DOCS.get(event, [])


def find_branch():
    return BRANCHES[0]


# --- P1: agent_turn ---------------------------------------------------------------

def detect_event(text):
    text = strip_diacritics(text)
    return next((ev for ev, kws in _EVENT_KEYWORDS.items() if any(k in text for k in kws)), None)


def agent_turn(message, ctx):
    """Mock pentru P1. ctx = {"event", "docs", "verdict", "history"}.
    Întoarce {"reply": str, "event": str|None}."""
    text = strip_diacritics(message)
    event = ctx.get("event")
    detected = detect_event(message)

    if detected and detected != event:
        intro = "Îmi pare foarte rău pentru pierderea ta. " if detected == "deces" else ""
        needed = "\n".join(f"- {d['label']}" for d in REQUIRED_DOCS[detected])
        return {
            "reply": f"{intro}Pentru **{EVENTS[detected]}** ai nevoie de:\n{needed}\n\n"
                     "Încarcă poze sau PDF-uri cu ele în stânga și le verific înainte să mergi la bancă.",
            "event": detected,
        }
    if not event:
        return {"reply": "Spune-mi pe scurt ce s-a întâmplat: un deces în familie, o căsătorie sau un divorț, "
                         "ori vrei să faci o procură pentru cineva?"}
    if "sucursal" in text or "programa" in text:
        b = find_branch()
        return {"reply": f"Cea mai apropiată unitate e **{b['name']}**, {b['address']} ({b['hours']}). "
                         "Te poți programa din cardul din dreapta."}

    verdict = ctx.get("verdict") or {}
    if verdict.get("status") == "ok":
        return {"reply": "Din ce văd, ai tot ce îți trebuie. **Ești pregătit să mergi la bancă.** "
                         "Ia actele în original. Consilierul face verificarea finală."}
    reasons = "\n".join(f"- {r}" for r in verdict.get("reasons", []))
    return {"reply": f"Mai sunt câteva lucruri înainte să mergi la bancă:\n{reasons}"}

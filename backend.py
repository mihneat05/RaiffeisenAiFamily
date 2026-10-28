"""Singurul loc prin care frontendul vorbește cu restul echipei.

Fiecare funcție folosește modulul real dacă există și cade pe mock_backend altfel:
    agent.agent_turn(message, ctx) -> {"reply": str, "event": str|None}           (P1)
    reader.read_document(data: bytes, filename: str) -> {"doc_type", "lizibil", "fields"}   (P2)
    validation.validate_document(doc) -> {"status": "ok"|"warn"|"fail", "reasons": [...]}  (P3)
    validation.crosscheck_documents(docs, event) -> {"status", "reasons"}              (P3)
    knowledge.required_docs(event) -> [{"type", "label"}]                              (P5)
USE_MOCK=1 forțează mock-urile peste tot.
"""
import importlib
import os

import mock_backend as mock


def _load(module, name):
    if os.getenv("USE_MOCK") == "1":
        return None
    try:
        return getattr(importlib.import_module(module), name)
    except ModuleNotFoundError as e:
        if e.name != module:
            print(f"[backend] {module}.{name} există, dar importul a eșuat: {e}")
        return None
    except (ImportError, AttributeError) as e:
        print(f"[backend] {module}.{name} indisponibil, folosesc mock: {e}")
        return None


_agent_turn = _load("agent", "agent_turn")
_read_document = _load("reader", "read_document")
_validate_document = _load("validation", "validate_document")
_crosscheck_documents = _load("validation", "crosscheck_documents")
_required_docs = _load("knowledge", "required_docs")

# True = încă pe mock. Apare în sidebar, ca să știi ce rulează la demo.
MOCKED = {
    "P1 agent": _agent_turn is None,
    "P2 citire acte": _read_document is None,
    "P3 validare": _validate_document is None,
    "P3 crosscheck": _crosscheck_documents is None,
    "P5 conținut": _required_docs is None,
}

EVENTS = mock.EVENTS


def _as_dict(obj):
    # P2 folosește Pydantic, deci poate întoarce un model în loc de dict.
    return obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)


def required_docs(event):
    return [_as_dict(d) for d in (_required_docs or mock.required_docs)(event)]


def doc_label(doc_type, event=None):
    labels = {d["type"]: d["label"] for d in required_docs(event)} if event else {}
    return labels.get(doc_type) or mock.DOC_LABELS.get(doc_type) or "Act necunoscut"


def process_upload(filename, data, event=None):
    """Citire (P2) + validare (P3) pentru un singur fișier."""
    try:
        extracted = _as_dict((_read_document or mock.read_document)(data, filename))
        check = _as_dict((_validate_document or mock.validate_document)(extracted))
    except Exception as e:  # la demo vrem un mesaj, nu un ecran roșu
        print(f"[backend] procesarea {filename} a eșuat: {e!r}")
        extracted = {"doc_type": "necunoscut", "fields": {}}
        check = {"status": "warn", "reasons": ["Nu am putut citi actul. Încearcă o poză mai clară sau un PDF."]}

    # P2 real (schemas.py) întoarce actul „plat”, cu `tip_act`; mock-ul întoarce doc_type + fields.
    if "tip_act" in extracted:
        doc_type, fields = extracted.get("tip_act") or "necunoscut", extracted
    else:
        doc_type, fields = extracted.get("doc_type", "necunoscut"), extracted.get("fields", {})
    return {
        "filename": filename,
        "doc_type": doc_type,
        "label": doc_label(doc_type, event),
        "fields": fields,
        "lizibil": extracted.get("lizibil", True),
        "status": check["status"],
        "reasons": check.get("reasons", []),
    }


def crosscheck(docs, event):
    try:
        return _as_dict((_crosscheck_documents or mock.crosscheck_documents)(docs, event))
    except Exception as e:
        print(f"[backend] crosscheck a eșuat: {e!r}")
        return {"status": "warn", "reasons": ["Nu am putut compara actele între ele. Consilierul le va verifica."]}


def agent_turn(message, ctx):
    try:
        return _as_dict((_agent_turn or mock.agent_turn)(message, ctx))
    except Exception as e:
        print(f"[backend] agentul a eșuat: {e!r}")
        return {"reply": "Am o problemă tehnică acum. Încearcă din nou în câteva secunde."}


def find_branch():
    return mock.find_branch()

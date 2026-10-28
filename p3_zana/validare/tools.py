"""Definițiile de tool pentru bucla LLM a lui P1 + dispatcher.

TOOLS e în formatul Anthropic (name / description / input_schema).
Pentru OpenAI: {"type": "function", "function": {"name", "description", "parameters": input_schema}}.
"""
from __future__ import annotations

import json
from typing import Any

from .crosscheck import FLUXURI, crosscheck_documents
from .validate import validate_document

TOOLS: list[dict[str, Any]] = [
    {
        "name": "validate_document",
        "description": (
            "Verifică un singur act deja citit (JSON-ul de la read_document): câmpuri obligatorii, "
            "CNP valid (cifra de control, dată, județ), buletin neexpirat, date coerente, cote moștenire. "
            "Întoarce status ok/atentie/eroare + lista de probleme explicate în română."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"document": {"type": "object", "description": "JSON-ul actului, cu cheia 'tip'."}},
            "required": ["document"],
        },
    },
    {
        "name": "crosscheck_documents",
        "description": (
            "Verifică toate actele încărcate împreună pentru un flux: aceeași persoană pe toate actele "
            "(CNP + nume), ordinea datelor, cine are voie (moștenitor, soț, împuternicit) și ce acte lipsesc. "
            "Apelează-l după ce toate actele au fost citite. Rezultatul e verdictul final consultativ."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "documents": {"type": "array", "items": {"type": "object"}},
                "flux": {"type": "string", "enum": list(FLUXURI)},
            },
            "required": ["documents", "flux"],
        },
    },
]


def executa_tool(nume: str, argumente: dict) -> str:
    """Rulează tool-ul cerut de LLM și întoarce rezultatul ca text JSON (pentru tool_result)."""
    try:
        if nume == "validate_document":
            verdict = validate_document(argumente["document"])
        elif nume == "crosscheck_documents":
            verdict = crosscheck_documents(argumente["documents"], argumente["flux"])
        else:
            return json.dumps({"eroare": f"tool necunoscut: {nume}"}, ensure_ascii=False)
        return json.dumps(verdict.pentru_agent(), ensure_ascii=False)
    except Exception as exc:  # agentul primește eroarea în loc să pice demo-ul
        return json.dumps({"eroare": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False)

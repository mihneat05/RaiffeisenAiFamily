"""P3 – Validare + crosscheck pentru Raiffeisen Family Agent.

Doar cod determinist, fără LLM. Agentul (P1) apelează:
    validate_document(doc)              -> Verdict pentru un act
    crosscheck_documents(docs, flux)    -> Verdict pentru tot dosarul
"""
from .crosscheck import FLUXURI, crosscheck_documents
from .models import Problema, Severitate, Verdict
from .tools import TOOLS, executa_tool
from .validate import validate_document

__all__ = ["validate_document", "crosscheck_documents", "Verdict", "Problema",
           "Severitate", "FLUXURI", "TOOLS", "executa_tool"]

"""Modelele de ieșire: problemele găsite și verdictul final (✅ / ⚠️ / ❌)."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severitate(str, Enum):
    OK = "ok"
    INFO = "info"         # ℹ️ sfat pentru client, NU schimbă verdictul
    ATENTIE = "atentie"   # ⚠️ de verificat de un om
    EROARE = "eroare"     # ❌ blochează dosarul


EMOJI = {Severitate.OK: "✅", Severitate.INFO: "ℹ️", Severitate.ATENTIE: "⚠️", Severitate.EROARE: "❌"}
TEXT = {
    Severitate.OK: "Gata de mers la bancă",
    Severitate.ATENTIE: "De verificat",
    Severitate.EROARE: "Lipsește sau e greșit ceva",
}


class Problema(BaseModel):
    cod: str = Field(description="Cod stabil, ex. CNP_CIFRA_CONTROL")
    severitate: Severitate
    mesaj: str = Field(description="Explicație pe limba clientului, în română")
    document: Optional[str] = Field(default=None, description="id-ul / tipul actului")
    camp: Optional[str] = None


class Verdict(BaseModel):
    status: Severitate
    emoji: str
    titlu: str
    probleme: list[Problema] = []
    acte_lipsa: list[str] = []

    @classmethod
    def din_probleme(cls, probleme: list[Problema], acte_lipsa: list[str] | None = None) -> "Verdict":
        acte_lipsa = acte_lipsa or []
        if any(p.severitate == Severitate.EROARE for p in probleme) or acte_lipsa:
            status = Severitate.EROARE
        elif any(p.severitate == Severitate.ATENTIE for p in probleme):
            status = Severitate.ATENTIE
        else:
            status = Severitate.OK
        # erorile primele, ca agentul să le spună întâi pe cele grave
        ordine = {Severitate.EROARE: 0, Severitate.ATENTIE: 1, Severitate.INFO: 2, Severitate.OK: 3}
        probleme = sorted(probleme, key=lambda p: ordine[p.severitate])
        return cls(status=status, emoji=EMOJI[status], titlu=TEXT[status],
                   probleme=probleme, acte_lipsa=acte_lipsa)

    def pentru_agent(self) -> dict:
        """Forma compactă trimisă înapoi LLM-ului ca rezultat de tool."""
        return self.model_dump(mode="json")

"""schemas.py – contractul comun P2 (read_document) ↔ P3 (validare) ↔ P1 (agent).

Cheile sunt exact cele stabilite de P2. Ce e marcat cu  # PROPUNERE P3  lipsea din lista
inițială și e necesar pentru crosscheck; confirmați în grup înainte să-l folosiți.

Reguli de format (P2):
  - CNP: string de 13 cifre (nu număr)
  - date: "YYYY-MM-DD"
  - lipsă / necitibil: null   (nu "", nu "N/A")
  - booleeni: true / false

IMPORTANT: câmpurile sunt intenționat permisive (str | None, fără regex). Dacă schema ar
respinge un CNP greșit, Pydantic ar arunca o excepție și clientul n-ar mai primi mesajul
„cifra de control nu se potrivește”. Validarea se face în P3, nu aici.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field, TypeAdapter


class ActBaza(BaseModel):
    """Chei comune tuturor actelor."""
    tip_act: str
    fisier: Optional[str] = Field(None, description="numele fișierului încărcat")  # PROPUNERE P3 (pt. mesaje)
    lizibil: Optional[bool] = None
    nume: Optional[str] = None
    prenume: Optional[str] = None
    cnp: Optional[str] = Field(None, description="13 cifre, ca string")
    data_nasterii: Optional[str] = Field(None, description="YYYY-MM-DD")
    serie: Optional[str] = None
    numar: Optional[str] = None
    data_emiterii: Optional[str] = Field(None, description="YYYY-MM-DD")
    data_expirarii: Optional[str] = Field(None, description="YYYY-MM-DD")
    emitent: Optional[str] = Field(None, description="SPCLEP / notar / instanță / starea civilă")
    semnat_stampilat: Optional[bool] = None
    campuri_nesigure: list[str] = Field(default_factory=list,
                                        description="cheile citite cu încredere mică")


class Buletin(ActBaza):
    tip_act: Literal["buletin"] = "buletin"


class CertificatDeces(ActBaza):
    """nume / prenume / cnp = persoana decedată."""
    tip_act: Literal["certificat_deces"] = "certificat_deces"
    data_decesului: Optional[str] = None
    locul_decesului: Optional[str] = None


class Mostenitor(BaseModel):  # PROPUNERE P3
    nume: Optional[str] = None
    prenume: Optional[str] = None
    cnp: Optional[str] = None
    cota: Optional[str] = Field(None, description='ex. "1/4" sau "25%"')


class CertificatMostenitor(ActBaza):  # PROPUNERE P3 – lipsea din listă, dar e actul central la deces
    """nume / prenume / cnp = persoana decedată (aceleași chei ca pe certificatul de deces)."""
    tip_act: Literal["certificat_mostenitor"] = "certificat_mostenitor"
    mostenitori: list[Mostenitor] = Field(default_factory=list)


class CertificatCasatorie(ActBaza):
    tip_act: Literal["certificat_casatorie"] = "certificat_casatorie"
    nume_sot: Optional[str] = Field(None, description="nume complet")
    cnp_sot: Optional[str] = None
    nume_sotie: Optional[str] = Field(None, description="nume complet")
    cnp_sotie: Optional[str] = None
    data_casatoriei: Optional[str] = None


class SentintaDivort(ActBaza):
    """data_ramanerii_definitive = null înseamnă că sentința NU e definitivă."""
    tip_act: Literal["sentinta_divort"] = "sentinta_divort"
    data_ramanerii_definitive: Optional[str] = None
    nume_reclamant: Optional[str] = None
    nume_parat: Optional[str] = None
    cnp_reclamant: Optional[str] = None  # PROPUNERE P3 (dacă apare în sentință)
    cnp_parat: Optional[str] = None      # PROPUNERE P3


class Procura(ActBaza):
    tip_act: Literal["procura"] = "procura"
    nume_mandant: Optional[str] = None
    nume_mandatar: Optional[str] = None
    cnp_mandant: Optional[str] = None    # PROPUNERE P3 – procura notarială are CNP-urile
    cnp_mandatar: Optional[str] = None   # PROPUNERE P3
    data_valabilitate: Optional[str] = Field(None, description="până când e valabilă; null = nelimitat")
    operatiuni: Optional[list[str]] = Field(None, description="ce are voie împuternicitul")  # PROPUNERE P3


Act = Annotated[
    Union[Buletin, CertificatDeces, CertificatMostenitor, CertificatCasatorie, SentintaDivort, Procura],
    Field(discriminator="tip_act"),
]
_adapter = TypeAdapter(Act)


def parse_act(data: dict) -> BaseModel:
    """dict de la LLM -> modelul potrivit, după tip_act."""
    return _adapter.validate_python(data)

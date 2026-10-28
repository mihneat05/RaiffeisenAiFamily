"""
schemas.py - contractul de date dintre P2 (citire acte) si P3 (validare/crosscheck).

Reguli:
- Toate campurile sunt Optional: daca LLM-ul nu vede ceva, pune None (null), nu inventeaza.
- CNP = string, exact cum apare pe act. FARA validatori in schema (nici regex, nici cifra de
  control): validarea o face P3, ca un CNP gresit sa ajunga la el si clientul sa primeasca
  mesajul potrivit.
- Date in format ISO (YYYY-MM-DD).
- nume / prenume / cnp / data_nasterii = ale titularului actului. La certificatul de deces
  si la cel de mostenitor, titularul = DEFUNCTUL (aceleasi chei, ca sa se compare direct).
- Data de expirare e MEREU data_expirarii (inclusiv la procura).
- `fisier` e completat de cod (numele fisierului), nu de LLM.
"""
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

TipAct = Literal[
    "buletin",
    "certificat_deces",
    "certificat_mostenitor",
    "certificat_casatorie",
    "sentinta_divort",
    "procura",
    "adeverinta_medicala",
    "scrisoare_medicala",
    "necunoscut",
]


class ActBase(BaseModel):
    """Campuri comune tuturor actelor."""

    tip_act: TipAct
    fisier: Optional[str] = None          # numele pozei/PDF-ului, setat de cod
    lizibil: bool = True
    nume: Optional[str] = None
    prenume: Optional[str] = None
    cnp: Optional[str] = None
    data_nasterii: Optional[date] = None
    serie: Optional[str] = None
    numar: Optional[str] = None
    data_emiterii: Optional[date] = None
    data_expirarii: Optional[date] = None
    emitent: Optional[str] = None
    semnat_stampilat: Optional[bool] = None
    # numele campurilor pe care LLM-ul nu e sigur (ex: ["cnp", "serie"])
    campuri_nesigure: list[str] = Field(default_factory=list)


class Buletin(ActBase):
    tip_act: Literal["buletin"] = "buletin"
    adresa: Optional[str] = None
    cetatenie: Optional[str] = None


class CertificatDeces(ActBase):
    tip_act: Literal["certificat_deces"] = "certificat_deces"
    # nume / prenume / cnp / data_nasterii = ale persoanei decedate
    data_decesului: Optional[date] = None
    locul_decesului: Optional[str] = None


class Mostenitor(BaseModel):
    nume: Optional[str] = None
    prenume: Optional[str] = None
    cnp: Optional[str] = None
    cota: Optional[str] = None            # ex: "1/2"


class CertificatMostenitor(ActBase):
    tip_act: Literal["certificat_mostenitor"] = "certificat_mostenitor"
    # nume / prenume / cnp = ale DEFUNCTULUI (ca pe certificatul de deces)
    mostenitori: list[Mostenitor] = Field(default_factory=list)


class CertificatCasatorie(ActBase):
    tip_act: Literal["certificat_casatorie"] = "certificat_casatorie"
    nume_sot: Optional[str] = None
    cnp_sot: Optional[str] = None
    nume_sotie: Optional[str] = None
    cnp_sotie: Optional[str] = None
    data_casatoriei: Optional[date] = None


class SentintaDivort(ActBase):
    tip_act: Literal["sentinta_divort"] = "sentinta_divort"
    nume_reclamant: Optional[str] = None
    cnp_reclamant: Optional[str] = None
    nume_parat: Optional[str] = None
    cnp_parat: Optional[str] = None
    data_ramanerii_definitive: Optional[date] = None


class Procura(ActBase):
    tip_act: Literal["procura"] = "procura"
    nume_mandant: Optional[str] = None
    cnp_mandant: Optional[str] = None
    nume_mandatar: Optional[str] = None
    cnp_mandatar: Optional[str] = None
    operatiuni: list[str] = Field(default_factory=list)   # ce are voie sa faca mandatarul
    # data de expirare = data_expirarii (din ActBase)


class AdeverintaMedicala(ActBase):
    tip_act: Literal["adeverinta_medicala"] = "adeverinta_medicala"
    nume_titular: Optional[str] = None
    diagnostic_mentionat: Optional[bool] = None


class ScrisoareMedicala(ActBase):
    """Scrisoare medicala (flux imputernicire): dovedeste ca titularul nu se poate prezenta."""

    tip_act: Literal["scrisoare_medicala"] = "scrisoare_medicala"
    # nume / prenume / cnp / data_nasterii = ale PACIENTULUI
    unitate_medicala: Optional[str] = None
    medic: Optional[str] = None
    # true daca scrisoarea spune ca pacientul e imobilizat / nu se poate deplasa
    incapacitate_deplasare: Optional[bool] = None
    diagnostic_mentionat: Optional[bool] = None   # NU copiem diagnosticul (date sensibile)


class ActNecunoscut(ActBase):
    """Folosit cand actul nu poate fi clasificat sau poza nu e lizibila."""

    tip_act: Literal["necunoscut"] = "necunoscut"


SCHEMAS: dict[str, type[ActBase]] = {
    "buletin": Buletin,
    "certificat_deces": CertificatDeces,
    "certificat_mostenitor": CertificatMostenitor,
    "certificat_casatorie": CertificatCasatorie,
    "sentinta_divort": SentintaDivort,
    "procura": Procura,
    "adeverinta_medicala": AdeverintaMedicala,
    "scrisoare_medicala": ScrisoareMedicala,
    "necunoscut": ActNecunoscut,
}


def to_json_dict(act: ActBase) -> dict:
    """Dict gata de JSON (datele devin string ISO). Foloseste asta, nu model_dump() simplu."""
    return act.model_dump(mode="json")


if __name__ == "__main__":
    # test rapid: python schemas.py
    exemplu = CertificatMostenitor(
        nume="Popescu",
        prenume="Ion",
        cnp="1500101123456",
        mostenitori=[Mostenitor(nume="Popescu", prenume="Maria", cnp="2520202123456", cota="1/2")],
    )
    print(to_json_dict(exemplu))

"""crosscheck_documents: verifică actele ÎNTRE ELE pentru un flux (deces, căsătorie, divorț, împuternicire)."""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Callable, Optional

from .adaptor import normalizeaza_act
from .models import Problema, Severitate, Verdict
from .reguli import ACTE_NECESARE, NUME_ACTE
from .utils import curata_cnp, format_data, nume_compatibile, nume_complet, parse_data, tokeni
from .validate import id_act, validate_document

E, A = Severitate.EROARE, Severitate.ATENTIE
Add = Callable[..., None]

FLUXURI = tuple(ACTE_NECESARE)


def crosscheck_documents(docs: list[dict], flux: str, azi: Optional[date] = None,
                         include_validari: bool = True) -> Verdict:
    """Verdictul complet al dosarului.

    docs  – lista de acte așa cum le întoarce read_document (P2)
    flux  – "deces" | "casatorie" | "divort" | "imputernicire"
    include_validari – adaugă și problemele din validate_document pentru fiecare act
    """
    azi = azi or date.today()
    probleme: list[Problema] = []

    def add(cod: str, sev: Severitate, mesaj: str, document: str | None = None, camp: str | None = None):
        probleme.append(Problema(cod=cod, severitate=sev, mesaj=mesaj, document=document, camp=camp))

    if flux not in ACTE_NECESARE:
        add("FLUX_NECUNOSCUT", E, f"Fluxul „{flux}” nu există. Variante: {', '.join(FLUXURI)}.")
        return Verdict.din_probleme(probleme)

    docs = [normalizeaza_act(d) for d in docs]
    if include_validari:
        for d in docs:
            probleme.extend(validate_document(d, azi).probleme)

    acte_lipsa = _acte_lipsa(docs, flux)
    _VERIFICARI_FLUX[flux](docs, azi, add, acte_lipsa)
    return Verdict.din_probleme(probleme, acte_lipsa)


# ------------------------------------------------------------------ ajutătoare

def _de_tip(docs: list[dict], tip: str) -> list[dict]:
    return [d for d in docs if d.get("tip") == tip]


def _acte_lipsa(docs: list[dict], flux: str) -> list[str]:
    numarate = Counter(d.get("tip") for d in docs)
    lipsa = []
    for tip, minim in ACTE_NECESARE[flux].items():
        if flux == "imputernicire" and tip == "buletin":
            continue  # tratat nominal mai jos (al cui buletin lipsește)
        if numarate[tip] < minim:
            lipsa.append(NUME_ACTE[tip])
    return lipsa


def _buletin_cu_cnp(docs: list[dict], cnp: Optional[str]) -> Optional[dict]:
    if not cnp:
        return None
    return next((b for b in _de_tip(docs, "buletin") if curata_cnp(b.get("cnp")) == cnp), None)


def _aceeasi_persoana(p1: dict, p2: dict, doc1: str, doc2: str, add: Add, rol: str) -> bool:
    """Compară CNP + nume între două acte. Întoarce True dacă CNP-ul se potrivește."""
    c1, c2 = curata_cnp(p1.get("cnp")), curata_cnp(p2.get("cnp"))
    n1, n2 = nume_complet(p1), nume_complet(p2)
    if c1 and c2 and c1 != c2:
        if nume_compatibile(n1, n2):
            add("CNP_DIFERIT", E, f"{rol}: același nume ({n1}), dar CNP diferit pe „{doc1}” și „{doc2}”. "
                "Una dintre cifre a fost citită greșit sau e o greșeală pe act.", doc2, "cnp")
        else:
            add("PERSOANA_DIFERITA", E, f"{rol}: „{doc1}” și „{doc2}” par să fie despre persoane diferite "
                f"({n1} vs. {n2}).", doc2)
        return False
    if c1 and c1 == c2:
        if not (p1.get("prenume") and p2.get("prenume")):
            # un act are doar numele complet (ex. certificat de căsătorie în format P2)
            if not nume_compatibile(n1, n2):
                comun = tokeni(n1) & tokeni(n2)
                add("NUME_FAMILIE_DIFERIT" if comun else "NUME_DIFERIT", A,
                    f"{rol}: CNP identic, dar numele diferă ({n1} vs. {n2}). "
                    + ("Probabil numele s-a schimbat după căsătorie." if comun else "Consilierul va verifica."),
                    doc2, "nume")
        elif not nume_compatibile(p1.get("prenume"), p2.get("prenume")):
            add("PRENUME_DIFERIT", A, f"{rol}: CNP identic, dar prenumele diferă ({n1} vs. {n2}). "
                "Consilierul va verifica.", doc2, "prenume")
        elif not nume_compatibile(p1.get("nume"), p2.get("nume")):
            add("NUME_FAMILIE_DIFERIT", A, f"{rol}: CNP identic, dar numele de familie diferă ({n1} vs. {n2}). "
                "Probabil numele s-a schimbat după căsătorie: adaugă certificatul de căsătorie.", doc2, "nume")
        return True
    return False


# ------------------------------------------------------------------ fluxuri

def _flux_deces(docs, azi, add, acte_lipsa):
    certificate_deces = _de_tip(docs, "certificat_deces")
    certificate_most = _de_tip(docs, "certificat_mostenitor")
    if not certificate_deces or not certificate_most:
        return
    cd, cm = certificate_deces[0], certificate_most[0]
    defunct = cm.get("defunct") or {}
    cnp_defunct = curata_cnp(cd.get("cnp"))

    # 1. același defunct pe ambele certificate
    _aceeasi_persoana(cd, defunct, id_act(cd), id_act(cm), add, "Persoana decedată")

    # 2. ordinea datelor: certificatul de moștenitor vine după deces
    deces, emitere = parse_data(cd.get("data_decesului")), parse_data(cm.get("data_emiterii"))
    if deces and emitere and emitere < deces:
        add("ORDINE_DATE", E, f"Certificatul de moștenitor ({format_data(emitere)}) este emis înainte de "
            f"data decesului ({format_data(deces)}).", id_act(cm), "data_emiterii")

    # 3. buletinele aparțin moștenitorilor
    mostenitori = [m for m in (cm.get("mostenitori") or []) if isinstance(m, dict)]
    cnp_mostenitori = {curata_cnp(m.get("cnp")) for m in mostenitori}
    for b in _de_tip(docs, "buletin"):
        cnp_b = curata_cnp(b.get("cnp"))
        if cnp_b and cnp_b == cnp_defunct:
            add("BULETIN_DEFUNCT", A, "Ai încărcat buletinul persoanei decedate. Nu e greșit, dar banca are "
                "nevoie de buletinul tău, ca moștenitor.", id_act(b))
            continue
        potrivit = next((m for m in mostenitori if curata_cnp(m.get("cnp")) == cnp_b), None)
        if potrivit:
            _aceeasi_persoana(potrivit, b, id_act(cm), id_act(b), add, "Moștenitor")
            continue
        # poate CNP-ul a fost citit greșit, dar numele se potrivește
        dupa_nume = next((m for m in mostenitori if nume_compatibile(nume_complet(m), nume_complet(b))), None)
        if dupa_nume:
            _aceeasi_persoana(dupa_nume, b, id_act(cm), id_act(b), add, "Moștenitor")
        else:
            add("NU_E_MOSTENITOR", E, f"{nume_complet(b)} nu apare pe certificatul de moștenitor. "
                "Doar moștenitorii trecuți pe certificat pot ridica banii.", id_act(b))

    # 4. moștenitorii fără buletin: informativ
    fara_buletin = [nume_complet(m) for m in mostenitori
                    if curata_cnp(m.get("cnp")) not in {curata_cnp(b.get("cnp")) for b in _de_tip(docs, "buletin")}]
    if fara_buletin and len(fara_buletin) < len(mostenitori):
        add("MOSTENITORI_FARA_BULETIN", Severitate.INFO, "Pentru ceilalți moștenitori ("
            + ", ".join(fara_buletin) + ") va fi nevoie de buletinul lor sau de o procură, "
            "dacă nu vin personal la bancă.", id_act(cm))

    if cnp_defunct and cnp_defunct in cnp_mostenitori:
        add("DEFUNCT_MOSTENITOR", E, "Persoana decedată apare și ca moștenitor: verifică actele.", id_act(cm))


def _gaseste_sot(act: dict, b: dict) -> Optional[dict]:
    cnp_b = curata_cnp(b.get("cnp"))
    for k in ("sot1", "sot2"):
        s = act.get(k) or {}
        if cnp_b and curata_cnp(s.get("cnp")) == cnp_b:
            return s
    # fallback după nume (CNP lipsă sau citit greșit): cel mai mare număr de cuvinte comune
    candidati = []
    for k in ("sot1", "sot2"):
        s = act.get(k) or {}
        comun = len(tokeni(nume_complet(s)) & tokeni(nume_complet(b)))
        if comun:
            candidati.append((comun, s))
    return max(candidati, key=lambda c: c[0])[1] if candidati else None


def _flux_casatorie(docs, azi, add, acte_lipsa):
    certificate = _de_tip(docs, "certificat_casatorie")
    if not certificate:
        return
    cc = certificate[0]
    for b in _de_tip(docs, "buletin"):
        sot = _gaseste_sot(cc, b)
        if sot is None:
            add("NU_E_SOT", E, f"{nume_complet(b)} nu apare pe certificatul de căsătorie.", id_act(b))
            continue
        nume_nou = sot.get("nume_dupa_casatorie")
        if nume_nou:
            # buletinul trebuie să aibă deja numele nou
            if not nume_compatibile(nume_nou, b.get("nume")):
                add("BULETIN_NUME_VECHI", E, f"Buletinul are încă numele „{b.get('nume')}”, iar după căsătorie numele "
                    f"este „{nume_nou}”. Ai nevoie de buletinul nou, emis după schimbarea numelui.", id_act(b), "nume")
                # comparăm doar CNP + prenume, numele vechi e de așteptat
                _aceeasi_persoana({**sot, "nume": b.get("nume")}, b, id_act(cc), id_act(b), add, "Soț/soție")
            else:
                _aceeasi_persoana({**sot, "nume": nume_nou}, b, id_act(cc), id_act(b), add, "Soț/soție")
        else:
            _schimbare_nume_asteptata(sot, b, id_act(cc), add, "Soț/soție", "căsătoriei")


def _schimbare_nume_asteptata(persoana, b, doc_act, add, rol, eveniment):
    """La căsătorie / divorț e NORMAL ca numele de pe buletin să difere: ℹ️, nu ⚠️."""
    c1, c2 = curata_cnp(persoana.get("cnp")), curata_cnp(b.get("cnp"))
    n_act, n_b = nume_complet(persoana), nume_complet(b)
    if c1 and c1 == c2 and not nume_compatibile(n_act, n_b) and tokeni(n_act) & tokeni(n_b):
        add("NUME_ACTUALIZAT", Severitate.INFO, f"{rol}: numele de pe buletin ({n_b}) diferă de cel de pe act "
            f"({n_act}), cum e normal după schimbarea numelui în urma {eveniment}. Banca îl va actualiza.", id_act(b))
        return
    _aceeasi_persoana(persoana, b, doc_act, id_act(b), add, rol)


def _flux_divort(docs, azi, add, acte_lipsa):
    sentinte = _de_tip(docs, "sentinta_divort")
    if not sentinte:
        return
    sd = sentinte[0]
    for b in _de_tip(docs, "buletin"):
        sot = _gaseste_sot(sd, b)
        if sot is None:
            add("NU_E_PARTE", E, f"{nume_complet(b)} nu apare în sentința de divorț.", id_act(b))
            continue
        nume_dupa = sot.get("nume_dupa_divort")
        if nume_dupa:
            _aceeasi_persoana({**sot, "nume": nume_dupa}, b, id_act(sd), id_act(b), add, "Fost soț/fostă soție")
        elif not curata_cnp(sot.get("cnp")):
            # sentința în format P2 poate să nu aibă CNP: verificăm doar numele
            if not tokeni(nume_complet(sot)) & tokeni(nume_complet(b)):
                add("NUME_DIFERIT", A, f"{nume_complet(b)} nu se potrivește cu numele din sentință "
                    f"({nume_complet(sot)}).", id_act(b))
        else:
            _schimbare_nume_asteptata(sot, b, id_act(sd), add, "Fost soț/fostă soție", "divorțului")


def _flux_imputernicire(docs, azi, add, acte_lipsa):
    procuri = _de_tip(docs, "procura")
    if not procuri:
        acte_lipsa.append("buletinul titularului și al împuternicitului")
        return
    pr = procuri[0]
    for rol, eticheta in (("mandant", "titularului contului"), ("mandatar", "împuternicitului")):
        persoana = pr.get(rol) or {}
        b = _buletin_cu_cnp(docs, curata_cnp(persoana.get("cnp")))
        if b is None:  # poate CNP citit greșit: căutăm după nume
            b = next((x for x in _de_tip(docs, "buletin")
                      if nume_compatibile(nume_complet(x), nume_complet(persoana))), None)
        if b is None:
            acte_lipsa.append(f"buletinul {eticheta} ({nume_complet(persoana) or 'nume necitit'})")
        else:
            _aceeasi_persoana(persoana, b, id_act(pr), id_act(b), add,
                              "Titular" if rol == "mandant" else "Împuternicit")

    # procura încetează la decesul titularului
    cnp_mandant = curata_cnp((pr.get("mandant") or {}).get("cnp"))
    for cd in _de_tip(docs, "certificat_deces"):
        if cnp_mandant and curata_cnp(cd.get("cnp")) == cnp_mandant:
            add("PROCURA_INCETATA_DECES", E, "Titularul procurii a decedat, iar procura și-a încetat efectele. "
                "Pentru conturile lui urmează procedura de succesiune.", id_act(pr))


_VERIFICARI_FLUX = {
    "deces": _flux_deces,
    "casatorie": _flux_casatorie,
    "divort": _flux_divort,
    "imputernicire": _flux_imputernicire,
}

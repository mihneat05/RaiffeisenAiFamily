"""branches.py - caută cele mai apropiate sucursale Raiffeisen (date reale, live, din OpenStreetMap).

    find_nearest("Militari, București")  ->  {"locatie": {...}, "sucursale": [ {...}, ... ]}

1. Nominatim (OpenStreetMap) transformă ce scrie clientul (oraș / cartier / adresă) în coordonate.
2. Overpass (OpenStreetMap) caută băncile Raiffeisen din jurul acelui punct (5 km -> 15 km -> 50 km).
3. Le sortăm după distanță și întoarcem primele 3.

Fără chei API. Nu inventăm sucursale: dacă nu e internet sau nu găsim nimic, spunem asta.
Datele OSM pot fi incomplete (ex. programul) -> recomandăm verificarea pe raiffeisen.ro / *2000.
Test din terminal:  python branches.py "Piata Victoriei, Bucuresti"
"""
import json
import math
import re
import sys
from pathlib import Path
import urllib.parse
import urllib.request
from functools import lru_cache

USER_AGENT = "RaiffeisenFamilyAgent-hackathon/1.0 (prototip studentesc)"  # cerut de politica Nominatim
NOMINATIM = "https://nominatim.openstreetmap.org/search"
PHOTON = "https://photon.komoot.io/api/"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
RAZE_KM = (5, 15, 50)
DATA_FILE = Path(__file__).parent / "sucursale_osm.json"   # lista descărcată o dată cu: python branches.py --update
TIMEOUT = 12


def _get_json(url, data=None, timeout=None):
    """GET/POST -> JSON. Folosim httpx (vine cu anthropic): are propriile certificate SSL (certifi),
    deci merge și pe Windows, unde urllib dă des „CERTIFICATE_VERIFY_FAILED”."""
    try:
        import httpx
    except ImportError:
        req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout or TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    with httpx.Client(timeout=timeout or TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as c:
        if data:
            r = c.post(url, content=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        else:
            r = c.get(url)
        r.raise_for_status()
        return r.json()


def _nominatim(text):
    q = urllib.parse.urlencode({"q": text, "format": "json", "limit": 1, "countrycodes": "ro", "accept-language": "ro"})
    res = _get_json(f"{NOMINATIM}?{q}")
    return (float(res[0]["lat"]), float(res[0]["lon"]), res[0].get("display_name", text)) if res else None


def _photon(text):
    """Al doilea serviciu de geocodare (tot date OpenStreetMap), dacă Nominatim e blocat sau ocupat."""
    q = urllib.parse.urlencode({"q": text, "limit": 1, "bbox": "20.2,43.6,29.7,48.3"})  # doar România
    res = _get_json(f"{PHOTON}?{q}").get("features") or []
    if not res:
        return None
    lon, lat = res[0]["geometry"]["coordinates"]
    p = res[0].get("properties", {})
    nume = ", ".join(x for x in (p.get("name"), p.get("district"), p.get("city"), p.get("country")) if x)
    return float(lat), float(lon), nume or text


@lru_cache(maxsize=128)
def geocode(text):
    """Text liber -> (lat, lon, nume afișat) sau None. Încearcă Nominatim, apoi Photon."""
    erori = []
    for f in (_nominatim, _photon):
        try:
            r = f(text)
            if r:
                return r
        except Exception as e:
            erori.append(f"{f.__name__}: {e}")
    if len(erori) == 2:
        raise ConnectionError(" | ".join(erori))
    return None


def _overpass(lat, lon, raza_km):
    r = int(raza_km * 1000)
    query = f"""[out:json][timeout:20];
(
  nwr["amenity"="bank"]["name"~"Raiffeisen",i](around:{r},{lat},{lon});
  nwr["amenity"="bank"]["brand"~"Raiffeisen",i](around:{r},{lat},{lon});
);
out center tags;"""
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for url in OVERPASS:  # încercăm al doilea server dacă primul e ocupat
        try:
            return _get_json(url, data).get("elements", [])
        except Exception as e:
            last = e
    raise last


def _km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _adresa(t):
    strada = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
    oras = t.get("addr:city") or t.get("addr:town") or t.get("addr:village")
    return ", ".join(x for x in (strada, oras) if x) or None


_ZILE = {"Mo": "Lu", "Tu": "Ma", "We": "Mi", "Th": "Jo", "Fr": "Vi", "Sa": "Sâ", "Su": "Du", "PH": "Sărbători",
         "off": "închis"}


def _program(oh):
    if not oh:
        return "program: verifică pe raiffeisen.ro"
    for en, ro in _ZILE.items():
        oh = re.sub(rf"\b{en}\b", ro, oh)
    return oh.replace(";", ",")


def _sucursala(el, lat, lon):
    t = el.get("tags", {})
    if "atm" in str(t.get("name", "")).lower():   # bancomatele nu sunt sucursale
        return None
    blat = el.get("lat") or el.get("center", {}).get("lat")
    blon = el.get("lon") or el.get("center", {}).get("lon")
    if blat is None or blon is None:
        return None
    d = _km(lat, lon, blat, blon)
    return {
        "name": t.get("name", "Raiffeisen Bank"),
        "address": _adresa(t) or "adresa nu e trecută în OpenStreetMap",
        "hours": _program(t.get("opening_hours")),
        "distance": f"{d:.1f} km".replace(".", ","),
        "distance_km": round(d, 2),
        "lat": blat, "lon": blon,
        "booking_url": f"https://www.google.com/maps/dir/?api=1&destination={blat},{blon}",
        "phone": t.get("phone") or t.get("contact:phone"),
    }


# ------------------------------------------------------------------ lista locală (recomandat la demo)
def update(timeout=180):
    """Descarcă O DATĂ toate unitățile Raiffeisen din România (OpenStreetMap) în sucursale_osm.json."""
    query = f"""[out:json][timeout:{timeout}];
area["ISO3166-1"="RO"][admin_level=2]->.ro;
(
  nwr["amenity"="bank"]["name"~"Raiffeisen",i](area.ro);
  nwr["amenity"="bank"]["brand"~"Raiffeisen",i](area.ro);
);
out center tags;"""
    data = urllib.parse.urlencode({"data": query}).encode()
    elemente, erori = None, []
    for url in OVERPASS:
        try:
            elemente = _get_json(url, data, timeout=timeout + 20).get("elements", [])
            break
        except Exception as e:
            erori.append(f"{url}: {e}")
            print("  server indisponibil, încerc următorul:", e)
    if elemente is None:
        raise ConnectionError(" | ".join(erori))
    lista, vazute = [], set()
    for el in elemente:
        t = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or (round(lat, 4), round(lon, 4)) in vazute:
            continue
        vazute.add((round(lat, 4), round(lon, 4)))
        lista.append({"tags": {k: v for k, v in t.items() if k in (
            "name", "brand", "addr:street", "addr:housenumber", "addr:city", "addr:town", "addr:village",
            "opening_hours", "phone", "contact:phone")}, "lat": lat, "lon": lon})
    DATA_FILE.write_text(json.dumps(lista, ensure_ascii=False, indent=0), encoding="utf-8")
    return len(lista)


@lru_cache(maxsize=1)
def _lista_locala():
    if not DATA_FILE.exists():
        return None
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _norm(x):
    import unicodedata
    return unicodedata.normalize("NFKD", str(x or "")).encode("ascii", "ignore").decode().lower()


def _dupa_oras(text, lista):
    """Fără internet: potrivim orașul scris de client cu orașul din adresa sucursalelor."""
    cuvinte = {w for w in re.split(r"[\s,.-]+", _norm(text)) if len(w) > 2}
    gasite = []
    for el in lista:
        t = el["tags"]
        oras = {w for w in re.split(r"[\s,.-]+", _norm(t.get("addr:city") or t.get("addr:town") or t.get("addr:village"))) if w}
        if oras and cuvinte and oras <= cuvinte | oras and (oras & cuvinte):
            s = _sucursala(el, el["lat"], el["lon"])
            s["distance"], s["distance_km"] = "în oraș", 0
            gasite.append(s)
    return gasite[:3]


def _din_lista(lat, lon, lista):
    toate = [s for s in (_sucursala(el, lat, lon) for el in lista) if s]
    unice = {}
    for s in sorted(toate, key=lambda s: (s["distance_km"], s["hours"].startswith("program:"))):
        unice.setdefault((s["name"], s["address"]), s)
    top = sorted(unice.values(), key=lambda s: s["distance_km"])[:3]
    aproape = [s for s in top if s["distance_km"] <= RAZE_KM[-1]]
    return aproape or top[:1]   # dacă nu e nimic pe 50 km, arătăm măcar cea mai apropiată


@lru_cache(maxsize=128)
def _cauta(text):
    lista = _lista_locala()
    try:
        loc = geocode(text)
    except Exception:
        if lista:  # fără internet, dar avem lista: căutăm după oraș
            gasite = _dupa_oras(text, lista)
            if gasite:
                return {"locatie": {"text": text, "gasit": f"{text} (căutare după oraș, fără hartă)"},
                        "sucursale": gasite, "sursa": "listă locală OpenStreetMap"}
        raise
    if not loc:
        return {"eroare": "locatie_negasita", "mesaj": f"Nu am găsit locația „{text}”. Încearcă orașul și cartierul."}
    lat, lon, nume = loc
    info = {"text": text, "gasit": nume, "lat": lat, "lon": lon}
    if lista:  # varianta recomandată: distanțe calculate local, fără Overpass
        top = _din_lista(lat, lon, lista)
        return {"locatie": info, "sucursale": top, "sursa": "listă locală OpenStreetMap (programul se verifică pe raiffeisen.ro)"}
    for raza in RAZE_KM:  # fără listă locală: căutare live (serverele Overpass pot fi ocupate)
        top = _din_lista(lat, lon, _overpass(lat, lon, raza))
        if top:
            return {"locatie": dict(info, raza_km=raza), "sucursale": top,
                    "sursa": "OpenStreetMap (poate fi incomplet; programul se verifică pe raiffeisen.ro)"}
    return {"locatie": info, "sucursale": [], "mesaj": f"Nu am găsit sucursale Raiffeisen pe o rază de {RAZE_KM[-1]} km."}


def find_nearest(text):
    """Nu aruncă excepții: la demo vrem un mesaj, nu un ecran roșu."""
    text = (text or "").strip()
    if not text:
        return {"eroare": "fara_locatie", "mesaj": "Spune-mi orașul, cartierul sau adresa ta."}
    try:
        return _cauta(text)
    except Exception as e:
        return {"eroare": "fara_conexiune",
                "mesaj": "Nu pot căuta sucursalele acum (fără conexiune la hartă). "
                         "Le găsești pe raiffeisen.ro, la Rețea, sau la *2000.", "detalii": str(e)}


# ------------------------------------------------------------------ adresa din buletin
_CUV_CHEIE = {"mun", "municipiul", "or", "oras", "oraș", "orasul", "orașul", "com", "comuna", "sat", "satul", "loc",
              "sec", "sector", "sectorul", "jud", "judet", "judetul", "județul", "str", "strada", "nr", "bd", "bdul",
              "b-dul", "bulevardul", "cal", "calea", "al", "aleea", "sos", "șos", "soseaua", "șoseaua", "spl",
              "splaiul", "int", "intrarea", "bl", "sc", "et", "ap", "cam"}
_LOCALITATE = {"mun", "municipiul", "or", "oras", "oraș", "orasul", "orașul", "com", "comuna", "sat", "satul", "loc"}
_STRADA = {"str": "Strada", "strada": "Strada", "bd": "Bulevardul", "bdul": "Bulevardul", "b-dul": "Bulevardul",
           "bulevardul": "Bulevardul", "cal": "Calea", "calea": "Calea", "al": "Aleea", "aleea": "Aleea",
           "sos": "Șoseaua", "șos": "Șoseaua", "soseaua": "Șoseaua", "șoseaua": "Șoseaua",
           "spl": "Splaiul", "splaiul": "Splaiul", "int": "Intrarea", "intrarea": "Intrarea"}


def _tokeni(a):
    """„Mun.București Sec.6 Str.X nr.4” -> [("mun","București"), ("sec","6"), ("str","X"), ("nr","4")]."""
    a = re.sub(r"(?<=[A-Za-zăâîșțşţĂÂÎȘȚŞŢ])\.(?=\S)", ". ", str(a or "").replace(",", " "))  # „Str.X” -> „Str. X”
    out, cheie, val = [], None, []
    for w in a.split():
        k = w.rstrip(".").lower()
        if k in _CUV_CHEIE:
            if cheie or val:
                out.append((cheie, " ".join(val)))
            cheie, val = k, []
        else:
            val.append(w)
    if cheie or val:
        out.append((cheie, " ".join(val)))
    return out


def candidati_adresa(adresa):
    """Adresa ca pe buletin -> variante de căutat, de la cea mai precisă la cea mai largă.

    "Mun.București Sec.6 Str.Valea Ialomiței nr.4 bl.C1 sc.1 ap.12"
      -> ["Strada Valea Ialomiței 4, Sector 6, București", "Sector 6, București", "București"]
    """
    t = _tokeni(adresa)
    if not t:
        return []
    loc = [v for k, v in t if k in _LOCALITATE and v]
    sector = next((v for k, v in t if k in ("sec", "sector", "sectorul") and v), None)
    strada = next(((k, v) for k, v in t if k in _STRADA and v), None)
    nr = next((v for k, v in t if k == "nr" and v), None)
    oras = ", ".join(reversed(loc)) if loc else None        # „Sat Ghighiu Com Bărcănești” -> „Ghighiu, Bărcănești”
    zona = ", ".join(x for x in (f"Sector {sector}" if sector else None, oras) if x)
    out = []
    if strada and zona:
        out.append(f"{_STRADA[strada[0]]} {strada[1]}{' ' + nr if nr else ''}, {zona}")
    if zona:
        out.append(zona)
    if loc:
        out.append(loc[0])
    if not out:  # n-am recunoscut nimic: trimitem textul brut, fără bloc/scară/apartament
        out.append(" ".join(v for k, v in t if k not in ("bl", "sc", "et", "ap", "cam") and v))
    return [x for x in dict.fromkeys(out) if x]


def find_nearest_from_address(adresa):
    """Ca find_nearest, dar pornind de la adresa de pe buletin (încearcă variantele pe rând)."""
    variante = candidati_adresa(adresa)
    if not variante:
        return {"eroare": "fara_adresa", "mesaj": "Nu am putut citi adresa de pe buletin."}
    rez = None
    for v in variante:
        rez = find_nearest(v)
        if rez.get("eroare") == "fara_conexiune" or rez.get("sucursale"):
            break
    rez["din_buletin"] = True
    return rez


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["--update"]:
        print("Descarc lista sucursalelor Raiffeisen din OpenStreetMap (poate dura 1-2 minute)...")
        print(f"Gata: {update()} unități salvate în {DATA_FILE.name}")
    else:
        print(json.dumps(find_nearest(" ".join(sys.argv[1:]) or "Piata Victoriei, Bucuresti"),
                         ensure_ascii=False, indent=2))

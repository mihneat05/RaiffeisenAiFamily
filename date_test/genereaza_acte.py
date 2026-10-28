"""
Generează acte sintetice FALSE (marcate SPECIMEN) pentru testarea Raiffeisen Family Agent.
Flux: deces / succesiune. 3 cazuri: complet, act lipsă, CNP greșit.
Rulare: python genereaza_acte.py  -> creează folderul date_test/
"""
import json, os, math
from PIL import Image, ImageDraw, ImageFont

OUT = "date_test"
F = "/usr/share/fonts/truetype/dejavu/"
def font(name, size): return ImageFont.truetype(F + name, size)
SERIF_B, SERIF, SANS, SANS_B, MONO = "DejaVuSerif-Bold.ttf", "DejaVuSerif.ttf", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSansMono.ttf"

# ---------- CNP ----------
PONDERI = "279146358279"
def cifra_control(primele12):
    s = sum(int(a) * int(b) for a, b in zip(primele12, PONDERI)) % 11
    return "1" if s == 10 else str(s)

def cnp(sex, data, judet, nnn):
    """sex: 'M'/'F'; data: 'AAAA-LL-ZZ'; judet: '01'..'52'; nnn: '001'..'999'"""
    an, luna, zi = data.split("-")
    secol = 1 if an.startswith("19") else 5
    s = str(secol + (0 if sex == "M" else 1))
    baza = s + an[2:] + luna + zi + judet + nnn
    return baza + cifra_control(baza)

def strica_cnp(c):
    gresit = str((int(c[-1]) + 3) % 10)
    return c[:-1] + gresit

def cnp_valid(c):
    return len(c) == 13 and c.isdigit() and cifra_control(c[:12]) == c[12]

# ---------- desen ----------
def watermark(img):
    w, h = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(SANS_B, int(w / 7))
    txt = "SPECIMEN"
    tw = d.textlength(txt, font=f)
    d.text(((w - tw) / 2, h / 2 - w / 14), txt, font=f, fill=(200, 30, 30, 50))
    layer = layer.rotate(25, center=(w / 2, h / 2))
    img.alpha_composite(layer)
    d2 = ImageDraw.Draw(img)
    d2.text((40, h - 55), "DOCUMENT FALS – DOAR PENTRU TESTARE (hackathon)", font=font(SANS_B, 16), fill=(200, 30, 30, 255))

def stampila(d, cx, cy, r, sus, jos):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(40, 60, 160), width=4)
    d.ellipse((cx - r + 12, cy - r + 12, cx + r - 12, cy + r - 12), outline=(40, 60, 160), width=2)
    f = font(SANS_B, 15)
    for t, dy in ((sus, -18), (jos, 4)):
        tw = d.textlength(t, font=f)
        d.text((cx - tw / 2, cy + dy), t, font=f, fill=(40, 60, 160))

def semnatura(d, x, y):
    pts = [(x + i * 6, y + 12 * math.sin(i / 2.2) + (i % 3) * 2) for i in range(30)]
    d.line(pts, fill=(20, 20, 90), width=3)

def doc_alb(w, h, titlu, subtitlu):
    img = Image.new("RGBA", (w, h), (250, 248, 240, 255))
    d = ImageDraw.Draw(img)
    d.rectangle((15, 15, w - 15, h - 15), outline=(90, 90, 90), width=3)
    d.rectangle((25, 25, w - 25, h - 25), outline=(150, 150, 150), width=1)
    d.text((50, 45), "ROMÂNIA", font=font(SERIF_B, 22), fill="black")
    f = font(SERIF_B, 36)
    d.text(((w - d.textlength(titlu, font=f)) / 2, 90), titlu, font=f, fill="black")
    if subtitlu:
        f2 = font(SERIF, 20)
        d.text(((w - d.textlength(subtitlu, font=f2)) / 2, 140), subtitlu, font=f2, fill=(60, 60, 60))
    return img, d

def randuri(d, x, y, perechi, pas=42):
    for eticheta, valoare in perechi:
        d.text((x, y), eticheta, font=font(SANS, 19), fill=(80, 80, 80))
        d.text((x + 330, y), str(valoare), font=font(SANS_B, 21), fill="black")
        y += pas
    return y

# ---------- acte ----------
def certificat_deces(c, path):
    img, d = doc_alb(1200, 850, "CERTIFICAT DE DECES", f"Seria {c['serie_numar_certificat']}")
    randuri(d, 80, 200, [
        ("Numele:", c["nume_defunct"]),
        ("Prenumele:", c["prenume_defunct"]),
        ("CNP:", c["cnp_defunct"]),
        ("Data decesului:", c["data_decesului"]),
        ("Locul decesului:", c["locul_decesului"]),
        ("Data eliberării:", c["data_eliberarii"]),
        ("Emitent:", "Serviciul Public Local de Stare Civilă (fictiv)"),
    ])
    d.text((80, 600), "Ofițer de stare civilă", font=font(SANS, 18), fill="black")
    semnatura(d, 90, 650)
    stampila(d, 950, 640, 85, "STARE CIVILĂ", "SPECIMEN")
    watermark(img); img.convert("RGB").save(path)

def certificat_mostenitor(c, path):
    img, d = doc_alb(1200, 1000, "CERTIFICAT DE MOȘTENITOR", f"Nr. {c['numar_certificat']} din {c['data_emiterii']}")
    y = randuri(d, 80, 200, [
        ("Defunct:", c["nume_defunct"]),
        ("CNP defunct:", c["cnp_defunct"]),
        ("Notar public:", c["notar"]),
    ])
    d.text((80, y + 15), "Moștenitori și cote:", font=font(SANS_B, 21), fill="black")
    y += 60
    for m in c["mostenitori"]:
        d.text((100, y), f"• {m['nume']}   CNP {m['cnp']}   cota {m['cota']}", font=font(SANS, 20), fill="black")
        y += 38
    d.text((80, 760), "Notar public", font=font(SANS, 18), fill="black")
    if c["semnatura_stampila"]:
        semnatura(d, 90, 810)
        stampila(d, 950, 800, 90, "NOTAR PUBLIC", "SPECIMEN")
    watermark(img); img.convert("RGB").save(path)

def buletin(c, path):
    img = Image.new("RGBA", (1000, 630), (225, 238, 245, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((10, 10, 990, 620), radius=30, outline=(60, 90, 120), width=4)
    d.text((40, 30), "ROMÂNIA  •  CARTE DE IDENTITATE (fictivă)", font=font(SANS_B, 26), fill=(30, 50, 90))
    d.rectangle((40, 100, 270, 390), fill=(190, 200, 210), outline=(120, 120, 120))
    d.text((95, 230), "FOTO", font=font(SANS_B, 30), fill=(120, 120, 120))
    y = 100
    for et, val in [("Nume", c["nume"]), ("Prenume", c["prenume"]), ("CNP", c["cnp"]),
                    ("Seria / Nr.", f"{c['serie']} {c['numar']}"), ("Data emiterii", c["data_emiterii"]),
                    ("Valabil până la", c["data_expirarii"])]:
        d.text((300, y), et, font=font(SANS, 16), fill=(70, 70, 70))
        d.text((300, y + 20), val, font=font(SANS_B, 24), fill="black")
        y += 62
    mrz = f"IDROU{c['nume'].upper().replace(' ', '<')}<<{c['prenume'].upper().replace(' ', '<')}".ljust(36, "<")[:36]
    d.text((40, 500), mrz, font=font(MONO, 24), fill="black")
    d.text((40, 535), f"{c['serie']}{c['numar']}<<{c['cnp']}".ljust(36, "<")[:36], font=font(MONO, 24), fill="black")
    watermark(img); img.convert("RGB").save(path)

# ---------- cazuri ----------
def caz(nr, nume_folder, defunct, mostenitori, solicitant, verdict, motive, scenariu="ridicare_bani",
        include_mostenitor=True, cnp_buletin_override=None):
    folder = os.path.join(OUT, nume_folder)
    os.makedirs(folder, exist_ok=True)
    acte = {}

    cd = {
        "nume_defunct": defunct["nume"], "prenume_defunct": defunct["prenume"], "cnp_defunct": defunct["cnp"],
        "data_decesului": defunct["data_decesului"], "locul_decesului": defunct["loc"],
        "serie_numar_certificat": defunct["serie"], "data_eliberarii": defunct["data_eliberarii"],
    }
    certificat_deces(cd, os.path.join(folder, "certificat_deces.png"))
    acte["certificat_deces.png"] = {"tip_act": "certificat_deces", "campuri": cd}

    if include_mostenitor:
        cm = {
            "nume_defunct": f"{defunct['nume']} {defunct['prenume']}", "cnp_defunct": defunct["cnp"],
            "mostenitori": mostenitori, "notar": "BNP Exemplu Notar (fictiv)",
            "numar_certificat": f"{100 + nr}/2026", "data_emiterii": "2026-07-15", "semnatura_stampila": True,
        }
        certificat_mostenitor(cm, os.path.join(folder, "certificat_mostenitor.png"))
        acte["certificat_mostenitor.png"] = {"tip_act": "certificat_mostenitor", "campuri": cm}

    bl = dict(solicitant)
    if cnp_buletin_override:
        bl["cnp"] = cnp_buletin_override
    buletin(bl, os.path.join(folder, "buletin_solicitant.png"))
    acte["buletin_solicitant.png"] = {"tip_act": "act_identitate_solicitant", "campuri": bl}

    return {
        "caz": nume_folder, "flux_id": "deces_succesiune", "scenariu": scenariu,
        "acte_incarcate": acte,
        "rezultat_asteptat": {
            "verdict": verdict, "motive": motive,
            "acte_lipsa": [] if include_mostenitor else ["certificat_mostenitor"],
        },
    }

def main():
    os.makedirs(OUT, exist_ok=True)
    rezultate = []

    # CAZ 1 – complet
    d1 = {"nume": "MARINESCU", "prenume": "GHEORGHE", "cnp": cnp("M", "1951-04-12", "40", "118"),
          "data_decesului": "2026-03-14", "loc": "București", "serie": "DZ 482913", "data_eliberarii": "2026-03-16"}
    s1 = {"nume": "MARINESCU", "prenume": "ANDREI", "cnp": cnp("M", "1982-09-03", "40", "227"),
          "serie": "RX", "numar": "604218", "data_emiterii": "2021-05-10", "data_expirarii": "2031-09-03"}
    m1 = [{"nume": "MARINESCU ELENA", "cnp": cnp("F", "1955-11-21", "40", "305"), "cota": "1/2"},
          {"nume": "MARINESCU ANDREI", "cnp": s1["cnp"], "cota": "1/2"}]
    rezultate.append(caz(1, "caz1_complet", d1, m1, s1, "gata",
                         ["Toate actele cerute sunt prezente.", "CNP-urile sunt valide.",
                          "Solicitantul apare ca moștenitor.", "Buletinul este valabil."]))

    # CAZ 2 – lipsește certificatul de moștenitor
    d2 = {"nume": "DUMITRESCU", "prenume": "VASILE", "cnp": cnp("M", "1948-01-30", "12", "042"),
          "data_decesului": "2026-05-02", "loc": "Cluj-Napoca", "serie": "CJ 117304", "data_eliberarii": "2026-05-05"}
    s2 = {"nume": "DUMITRESCU", "prenume": "IOANA", "cnp": cnp("F", "1979-06-17", "12", "156"),
          "serie": "KX", "numar": "331907", "data_emiterii": "2022-02-01", "data_expirarii": "2032-06-17"}
    rezultate.append(caz(2, "caz2_act_lipsa", d2, [], s2, "lipseste",
                         ["Lipsește certificatul de moștenitor (sau hotărârea judecătorească definitivă).",
                          "Fără el, banca nu poate elibera banii."], include_mostenitor=False))

    # CAZ 3 – CNP greșit pe buletin
    d3 = {"nume": "POPA", "prenume": "MARIA", "cnp": cnp("F", "1950-08-08", "22", "071"),
          "data_decesului": "2026-02-20", "loc": "Iași", "serie": "IS 905561", "data_eliberarii": "2026-02-23"}
    cnp_corect_s3 = cnp("M", "1976-12-05", "22", "349")
    s3 = {"nume": "POPA", "prenume": "MIHAI", "cnp": cnp_corect_s3,
          "serie": "MX", "numar": "778120", "data_emiterii": "2020-11-11", "data_expirarii": "2030-12-05"}
    m3 = [{"nume": "POPA MIHAI", "cnp": cnp_corect_s3, "cota": "1/1"}]
    cnp_gresit = strica_cnp(cnp_corect_s3)
    rezultate.append(caz(3, "caz3_cnp_gresit", d3, m3, s3, "de_verificat",
                         ["CNP-ul de pe buletin nu este valid (cifra de control greșită).",
                          "CNP-ul de pe buletin nu coincide cu CNP-ul moștenitorului din certificatul de moștenitor."],
                         cnp_buletin_override=cnp_gresit))

    # verificări de siguranță
    for r in rezultate:
        for fis, a in r["acte_incarcate"].items():
            c = a["campuri"]
            for k in ("cnp", "cnp_defunct"):
                if k in c:
                    a.setdefault("cnp_valid", {})[k] = cnp_valid(c[k])
    assert all(cnp_valid(x) for x in [d1["cnp"], s1["cnp"], d2["cnp"], s2["cnp"], d3["cnp"], cnp_corect_s3])
    assert not cnp_valid(cnp_gresit)

    with open(os.path.join(OUT, "rezultate_asteptate.json"), "w", encoding="utf-8") as f:
        json.dump(rezultate, f, ensure_ascii=False, indent=2)
    print("Gata ->", OUT)

if __name__ == "__main__":
    main()

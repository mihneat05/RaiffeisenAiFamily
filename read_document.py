"""
read_document.py - P2: citeste un act (poza / PDF) si il intoarce ca JSON validat.

Folosire din cod (P1 o leaga ca tool in agent):
    from read_document import read_document
    rezultat = read_document("cale/catre/act.jpg")   # -> dict

Folosire din terminal:
    python read_document.py cale/catre/act.jpg

Variabile de mediu:
    ANTHROPIC_API_KEY   cheia API Anthropic, SAU
    AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (+ AWS_SESSION_TOKEN, AWS_DEFAULT_REGION)
                        pentru AWS Bedrock (pip install "anthropic[bedrock]")
                        -> pe Bedrock seteaza P2_MODEL la ID-ul Bedrock al modelului
    P2_MODEL            modelul de folosit (optional, implicit claude-sonnet-5-5)

Rezultate posibile (toate sunt dict-uri):
    - act citit:        {"tip_act": "...", "lizibil": true, "nume": ..., "cnp": ..., ...}
    - poza ilizibila:   {"tip_act": "...", "lizibil": false, "motiv": "..."}
    - tip necunoscut:   {"tip_act": "necunoscut", "lizibil": true, "eroare": "tip_act_nerecunoscut"}
    - alte erori:       {"eroare": "fisier_invalid" | "api_error" | "extractie_esuata", ...}
"""
import base64
import io
import json
import logging
import os
import re
import sys
from pathlib import Path

import anthropic
from PIL import Image, ImageOps
from pydantic import ValidationError

from prompts import (
    CLASSIFY_INSTRUCTION,
    SYSTEM_PROMPT,
    build_extract_instruction,
)
from schemas import SCHEMAS, TipAct, to_json_dict

try:  # citeste .env si cand read_document e rulat singur (P1)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
# P2_MODEL are prioritate; altfel acelasi MODEL ca agentul (din .env)
MODEL = os.getenv("P2_MODEL") or os.getenv("MODEL") or "claude-sonnet-5-5"
MAX_PAGES = 3          # cate pagini dintr-un PDF citim
MAX_SIDE = 2000        # latura maxima a imaginii trimise (px)
MAX_RETRIES = 2        # reincercari daca validarea Pydantic pica

logger = logging.getLogger("p2")

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if os.getenv("AWS_ACCESS_KEY_ID") and not os.getenv("ANTHROPIC_API_KEY"):
            # AWS Bedrock: citeste AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY /
            # AWS_SESSION_TOKEN / AWS_DEFAULT_REGION din mediu
            _client = anthropic.AnthropicBedrock(
                aws_region=os.getenv("AWS_DEFAULT_REGION", "us-west-2")
            )
        else:
            _client = anthropic.Anthropic()  # citeste ANTHROPIC_API_KEY din mediu
    return _client


# --------------------------------------------------------------------------
# GDPR: nu punem CNP-uri in log-uri
# --------------------------------------------------------------------------
def mask_cnp(text: str) -> str:
    """Inlocuieste orice secventa de 13 cifre cu o versiune mascata."""
    return re.sub(r"\b(\d)\d{9}(\d{3})\b", r"\1*********\2", str(text))


# --------------------------------------------------------------------------
# Incarcare fisier -> lista de imagini base64
# --------------------------------------------------------------------------
def _normalize_image(data: bytes) -> tuple[str, str]:
    """Roteste dupa EXIF (poze de telefon), micsoreaza, converteste in JPEG."""
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return "image/jpeg", base64.standard_b64encode(buf.getvalue()).decode()


def load_images(path: str) -> list[tuple[str, str]]:
    """Intoarce o lista de (media_type, base64) - una pentru fiecare poza / pagina PDF."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Fisierul nu exista: {path}")

    ext = p.suffix.lower()
    if ext == ".pdf":
        import fitz  # pymupdf

        doc = fitz.open(str(p))
        images = []
        for i, page in enumerate(doc):
            if i >= MAX_PAGES:
                break
            png = page.get_pixmap(dpi=150).tobytes("png")
            images.append(_normalize_image(png))
        if not images:
            raise ValueError("PDF-ul nu are pagini")
        return images

    if ext in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp"):
        return [_normalize_image(p.read_bytes())]

    raise ValueError(f"Format nesuportat: {ext}")


# --------------------------------------------------------------------------
# Apel LLM cu tool use (iesire structurata garantata)
# --------------------------------------------------------------------------
def _call_tool(images: list[tuple[str, str]], instruction: str, tool: dict) -> dict:
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": m, "data": d}}
        for m, d in images
    ]
    content.append({
        "type": "text",
        "text": instruction + f"\n\nRaspunde OBLIGATORIU apeland functia `{tool['name']}`.",
    })

    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=8000,   # include si "gandirea" modelului
        system=SYSTEM_PROMPT,
        tools=[tool],
        # unele modele (ex: claude-sonnet-5-5) accepta doar tool_choice "auto"
        tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": content}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return dict(block.input)
    raise RuntimeError("Modelul nu a intors niciun tool_use")


CLASSIFY_TOOL = {
    "name": "clasifica_act",
    "description": "Spune ce tip de act este si daca poza e lizibila.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tip_act": {"type": "string", "enum": list(TipAct.__args__)},
            "lizibil": {"type": "boolean"},
            "motiv_nelizibil": {"type": ["string", "null"]},
        },
        "required": ["tip_act", "lizibil"],
    },
}


def classify(images: list[tuple[str, str]]) -> dict:
    return _call_tool(images, CLASSIFY_INSTRUCTION, CLASSIFY_TOOL)


def _inline_refs(node, defs):
    """Inlocuieste $ref-urile din schema JSON cu definitia lor (pentru obiecte imbricate)."""
    if isinstance(node, dict):
        if "$ref" in node:
            return _inline_refs(defs[node["$ref"].split("/")[-1]], defs)
        return {k: _inline_refs(v, defs) for k, v in node.items() if k != "$defs"}
    if isinstance(node, list):
        return [_inline_refs(v, defs) for v in node]
    return node


def _extract_tool(tip_act: str) -> dict:
    """Construieste tool-ul de extractie din schema Pydantic a actului."""
    schema = SCHEMAS[tip_act].model_json_schema()
    schema = _inline_refs(schema, schema.get("$defs", {}))
    schema.pop("title", None)
    schema.pop("required", None)
    # tip_act, lizibil si fisier le setam noi, nu le cerem modelului
    for k in ("tip_act", "lizibil", "fisier"):
        schema["properties"].pop(k, None)
    return {
        "name": "extrage_act",
        "description": f"Salveaza datele extrase din actul de tip {tip_act}.",
        "input_schema": schema,
    }


def extract(images: list[tuple[str, str]], tip_act: str, eroare: str | None = None) -> dict:
    instruction = build_extract_instruction(tip_act, eroare)
    return _call_tool(images, instruction, _extract_tool(tip_act))


# --------------------------------------------------------------------------
# Curatare usoara a raspunsului inainte de validare
# --------------------------------------------------------------------------
_EMPTY = {"", "n/a", "na", "none", "null", "-", "necunoscut", "nu se vede"}


def _clean_value(key, v):
    if isinstance(v, str):
        v = v.strip()
        if v.lower() in _EMPTY:
            return None
        if key.startswith("cnp"):
            v = re.sub(r"\s+", "", v)  # doar spatiile; cifrele nu le atingem
        return v
    if isinstance(v, list):
        items = (_clean_value(key, i) for i in v)
        # scoatem elementele goale (None sau obiecte cu toate campurile null)
        return [x for x in items if x is not None and not (isinstance(x, dict) and not any(x.values()))]
    if isinstance(v, dict):
        return {k: _clean_value(k, i) for k, i in v.items()}
    return v


def _clean(raw: dict) -> dict:
    return {k: _clean_value(k, v) for k, v in raw.items()}


# --------------------------------------------------------------------------
# Date: daca LLM-ul scrie 03.09.2031 in loc de 2031-09-03, convertim noi,
# altfel validarea Pydantic ar pica si s-ar pierde tot actul. (P1)
# --------------------------------------------------------------------------
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RO_DATE = re.compile(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$")


def _normalize_dates(raw: dict) -> dict:
    nesigure = list(raw.get("campuri_nesigure") or [])
    for k, v in list(raw.items()):
        if k.startswith("data_") and isinstance(v, str):
            m = _RO_DATE.match(v)
            if m:
                v = raw[k] = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
            if not _ISO.match(v):
                raw[k] = None          # nu stim sa o citim -> null + marcata nesigura
                if k not in nesigure:
                    nesigure.append(k)
    raw["campuri_nesigure"] = nesigure
    return raw


# --------------------------------------------------------------------------
# Functia principala
# --------------------------------------------------------------------------
def _read_document(file: str) -> dict:
    # 1. incarcam fisierul
    try:
        images = load_images(file)
    except Exception as e:
        logger.warning("Fisier invalid: %s", e)
        return {"eroare": "fisier_invalid", "detalii": str(e)}

    try:
        # 2. clasificare + lizibilitate
        meta = classify(images)
        tip = meta.get("tip_act", "necunoscut")

        if not meta.get("lizibil", False):
            return {
                "tip_act": tip,
                "lizibil": False,
                "motiv": meta.get("motiv_nelizibil") or "documentul nu este lizibil",
            }
        if tip == "necunoscut":
            return {"tip_act": "necunoscut", "lizibil": True, "eroare": "tip_act_nerecunoscut"}

        # 3. extractie + validare Pydantic, cu reincercari
        eroare = None
        for attempt in range(MAX_RETRIES + 1):
            raw = _normalize_dates(_clean(extract(images, tip, eroare)))
            raw["tip_act"] = tip
            raw["lizibil"] = True
            try:
                act = SCHEMAS[tip](**raw)
                result = to_json_dict(act)
                logger.info("Act citit: %s", mask_cnp(json.dumps(result, ensure_ascii=False)))
                return result
            except ValidationError as e:
                eroare = str(e)
                logger.warning("Validare esuata (incercarea %d): %s", attempt + 1, mask_cnp(eroare))

        return {"tip_act": tip, "lizibil": True, "eroare": "extractie_esuata"}

    except Exception as e:  # API, credentiale AWS, model fara tool_use etc. - nu oprim aplicatia (P1)
        logger.error("Eroare API: %s", e)
        return {"eroare": "api_error", "detalii": str(e)}


def read_document(file: str) -> dict:
    """Citeste un act si intoarce un dict. Adauga mereu `fisier` (numele fisierului)."""
    result = _read_document(file)
    result["fisier"] = Path(file).name
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) < 2:
        print("Folosire: python read_document.py cale/catre/act.jpg")
        sys.exit(1)
    print(json.dumps(read_document(sys.argv[1]), indent=2, ensure_ascii=False))

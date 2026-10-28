"""reader.py - puntea dintre frontend (P4) și read_document (P2).

Frontendul trimite conținutul fișierului (bytes); read_document (P2) vrea o cale pe disc.
Salvăm temporar fișierul, îl citim și îl ștergem imediat (GDPR: nu păstrăm actele).
"""
import os
import tempfile
from pathlib import Path

from read_document import read_document as _read_path


def read_document(data: bytes, filename: str) -> dict:
    folder = tempfile.mkdtemp(prefix="raif_")
    path = Path(folder) / Path(filename).name
    try:
        path.write_bytes(data)
        rezultat = _read_path(str(path))
    finally:
        try:
            os.remove(path)
            os.rmdir(folder)
        except OSError:
            pass
    rezultat["fisier"] = Path(filename).name
    return rezultat

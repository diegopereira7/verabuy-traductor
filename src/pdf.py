"""Extracción de texto de PDFs y detección de proveedor."""
from __future__ import annotations

import logging
import subprocess
from typing import Optional

from src.config import PROVIDERS

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def extract_text(path: str) -> str:
    """Extrae el texto completo de un PDF.

    Prioriza pdfplumber sobre pdftotext por mejor manejo de tablas.

    Args:
        path: Ruta al fichero PDF.

    Returns:
        Texto completo del PDF.

    Raises:
        RuntimeError: Si no hay herramientas de extracción disponibles.
    """
    if HAS_PDFPLUMBER:
        with pdfplumber.open(path) as p:
            return '\n'.join(pg.extract_text() or '' for pg in p.pages)
    try:
        r = subprocess.run(
            ['pdftotext', '-layout', path, '-'],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    raise RuntimeError("Instala pdfplumber (pip install pdfplumber) o poppler-utils")


def detect_provider(path: str) -> Optional[dict]:
    """Detecta el proveedor de un PDF por patrones en su contenido.

    Args:
        path: Ruta al fichero PDF.

    Returns:
        Dict con datos del proveedor + 'key' y 'text', o None si no se reconoce.
    """
    try:
        text = extract_text(path)
    except (RuntimeError, OSError) as e:
        logger.warning("No se pudo extraer texto de %s: %s", path, e)
        return None
    text_lower = text.lower()
    for pkey, pdata in PROVIDERS.items():
        for pat in pdata['patterns']:
            if pat.lower() in text_lower:
                return {**pdata, 'key': pkey, 'text': text}
    return None

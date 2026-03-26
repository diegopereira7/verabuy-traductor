"""Gestión del historial de facturas procesadas (historial_universal.json)."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from src.config import HIST_FILE, FILE_ENCODING

logger = logging.getLogger(__name__)


class History:
    """Registro persistente de facturas procesadas."""

    def __init__(self, fp: str | Path = HIST_FILE):
        self.fp = Path(fp)
        self.entries: dict = {}
        if self.fp.exists():
            with open(self.fp, 'r', encoding=FILE_ENCODING) as f:
                self.entries = json.load(f)
            logger.debug("Historial cargado: %d entradas desde %s", len(self.entries), self.fp)

    def save(self) -> None:
        """Persiste el historial a disco."""
        with open(self.fp, 'w', encoding=FILE_ENCODING) as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)

    def add(self, inv: str, pdf: str, provider: str, total: float,
            n: int, ok: int, fail: int) -> None:
        """Registra una factura procesada."""
        self.entries[inv] = {
            'pdf': pdf, 'provider': provider, 'total_usd': total,
            'lineas': n, 'ok': ok, 'sin_match': fail,
            'fecha': f"{datetime.now():%Y-%m-%d %H:%M}",
        }
        self.save()

    def was_processed(self, inv: str) -> bool:
        """Comprueba si una factura ya fue procesada."""
        return inv in self.entries

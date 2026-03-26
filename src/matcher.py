"""Motor de matching: vincula líneas de factura con artículos de VeraBuy.

Incluye el pipeline de 5 etapas y funciones de postproceso
(rescate de líneas no parseadas y split de cajas mixtas).
"""
from __future__ import annotations

import logging
import re
from copy import copy

from src.config import FUZZY_THRESHOLD_AUTO
from src.models import InvoiceLine
from src.articulos import ArticulosLoader
from src.sinonimos import SynonymStore

logger = logging.getLogger(__name__)


class Matcher:
    """Pipeline de matching de 5 etapas: sinónimo → marca → exacto → rosa → fuzzy."""

    def __init__(self, art: ArticulosLoader, syn: SynonymStore):
        self.art = art
        self.syn = syn

    def match_line(self, provider_id: int, line: InvoiceLine) -> InvoiceLine:
        """Intenta vincular una línea de factura con un artículo de VeraBuy.

        Args:
            provider_id: ID del proveedor.
            line: Línea de factura a matchear.

        Returns:
            La misma línea con match_status y match_method actualizados.
        """
        # 1. Sinónimo guardado
        s = self.syn.find(provider_id, line)
        if s and s['articulo_id'] > 0:
            line.articulo_id = s['articulo_id']
            line.articulo_name = s['articulo_name']
            line.match_status = 'ok'
            line.match_method = 'sinónimo'
            return line

        # 2. Match con marca del proveedor
        a = self.art.find_branded(line.expected_name(), provider_id,
                                  getattr(line, 'provider_key', ''))
        if a:
            line.articulo_id = a['id']
            line.articulo_name = a['nombre']
            line.match_status = 'ok'
            line.match_method = 'marca'
            self.syn.add(provider_id, line, a['id'], a['nombre'], 'auto-marca')
            return line

        # 3. Match exacto por nombre esperado
        a = self.art.find_by_name(line.expected_name())
        if a:
            line.articulo_id = a['id']
            line.articulo_name = a['nombre']
            line.match_status = 'ok'
            line.match_method = 'exacto'
            self.syn.add(provider_id, line, a['id'], a['nombre'], 'auto')
            return line

        # 4. Match por rosa (si es rosa)
        if line.species == 'ROSES' and line.size and line.stems_per_bunch:
            if line.origin != 'COL':
                a = self.art.find_rose_ec(line.variety, line.size, line.stems_per_bunch)
            else:
                a = self.art.find_rose_col(line.variety, line.size, line.stems_per_bunch, line.grade)
            if a:
                line.articulo_id = a['id']
                line.articulo_name = a['nombre']
                line.match_status = 'ok'
                line.match_method = 'exacto'
                self.syn.add(provider_id, line, a['id'], a['nombre'], 'auto')
                return line

        # 5. Auto-fuzzy ≥90%
        cands = self.art.fuzzy_search(line, threshold=FUZZY_THRESHOLD_AUTO)
        if cands:
            best = cands[0]
            line.articulo_id = best['id']
            line.articulo_name = best['nombre']
            line.match_status = 'ok'
            line.match_method = f"fuzzy {best['similitud']}%"
            self.syn.add(provider_id, line, best['id'], best['nombre'], 'auto-fuzzy')
            return line

        line.match_status = 'sin_match'
        line.match_method = ''
        return line

    def match_all(self, provider_id: int, lines: list[InvoiceLine]) -> list[InvoiceLine]:
        """Matchea todas las líneas de una factura."""
        return [self.match_line(provider_id, l) for l in lines]


# --- Postproceso ---

# Patrones genéricos de líneas que probablemente son producto
_PRODUCT_LINE_RE = re.compile(
    r'(?:'
    r'^\s*\d+\s+(?:QB|HB|TB|QUARTER|HALF|FULL)\b'
    r'|'
    r'^\s*(?:QB|HB|TB)\s+\d'
    r'|'
    r'\b(?:ROSE|HYDRANGEA|CARNATION|CLAVEL|ALSTRO|GYPS|PANICULATA|CRISANTEMO|HYD)\b'
    r'|'
    r'^\s*\d+\s+[A-Z][A-Z\s.\-/]+\d+\s+\d+.*\d+\.\d{2}'
    r')',
    re.I
)
_NOISE_LINE_RE = re.compile(
    r'(?:'
    r'\bTOTAL\b|\bSUBTOTAL\b|\bSUB\s+TOTAL\b|\bGROSS\s+WEIGHT\b|\bNET\s+WEIGHT\b'
    r'|\bFULL\s+EQUIVALENT\b|\bPRODUCT\s+OF\b|\bCERTIFY\b|\bDISCLAIMER\b'
    r'|\bNAME\s+AND\s+TITLE\b|\bFREIGHT\b|\bPOWERED\s+BY\b|\bPACKING\b'
    r'|\bPage\s+\d|\bPieces\s+Product\b|\bBox\s+Units\b|\bREFERENCE\b'
    r'|\bTotal\s+pieces\b|\bTotal\s+Bunch\b|\bTotal\s+Stems\b|\bTotal\s+FULL\b'
    r'|\bTotal\s+USD\b|\bAmount\s+Due\b|\bTOT\.BOX\b|\bTOT\.BOUNCH\b|\bTOT\.\s*STEMS\b'
    r'|\bDISCOUNT\b|\bIVA\b|\bDOLLAR\b|\bSUB\s*TOTAL\b|\bINVOICE\b|\bPLEASE\b'
    r'|\bBENEFIC\b|\bWIRE\s+TRANSFER\b|\bCUSTOMER\b|\bCONSIGNEE\b|\bADDRESS\b'
    r'|\bCARRIER\b|\bSELLER\b|\bCOUNTRY\s+ESPA\b|\bDAE\b|\bM\.?A\.?W\.?B\b'
    r'|\bVARIEDAD\b|\bBOX\b.*\bTXB\b'
    r'|\bMIXED\s+BOX\b|\bTOTALS\b|\bFOB\b|\b\d+\s+TOTALS\b'
    r'|\bFlowers\s+Detail\b|\bBox\s+Detail\b|\bStems\s+Half\b|\bGross\s*$'
    r'|^Carnation\s+[\d,]+\s+\d+\s+\d|^Minicarnation\s+[\d,]+\s+\d+\s+\d'
    r')',
    re.I
)


def rescue_unparsed_lines(text: str, parsed_lines: list[InvoiceLine]) -> list[InvoiceLine]:
    """Detecta líneas de producto en el texto que el parser no capturó.

    Args:
        text: Texto completo del PDF.
        parsed_lines: Líneas ya parseadas por el parser específico.

    Returns:
        Lista de InvoiceLine con match_status='sin_parser'.
    """
    parsed_raws = {l.raw_description.strip() for l in parsed_lines}
    rescued = []
    for ln in text.split('\n'):
        ln_s = ln.strip()
        if not ln_s or len(ln_s) < 10:
            continue
        if ln_s in parsed_raws:
            continue
        if any(pr and pr in ln_s for pr in parsed_raws):
            continue
        if not _PRODUCT_LINE_RE.search(ln_s):
            continue
        if _NOISE_LINE_RE.search(ln_s):
            continue
        if not re.search(r'\d+\.\d{2}', ln_s):
            continue
        il = InvoiceLine(
            raw_description=ln_s,
            species='OTHER',
            variety='(NO PARSEADO)',
            match_status='sin_parser',
            match_method='',
        )
        rescued.append(il)
    return rescued


def split_mixed_boxes(lines: list[InvoiceLine]) -> list[InvoiceLine]:
    """Divide líneas con variedad compuesta (A/B) en líneas individuales.

    Ej: variety='RED/YELLOW' → 2 líneas: RED y YELLOW, cada una con la mitad
    de tallos y total. Se marca box_type='MIX' en las líneas divididas.

    Args:
        lines: Líneas de factura ya parseadas.

    Returns:
        Lista con las líneas originales más las divididas.
    """
    result = []
    for l in lines:
        v = l.variety.strip()
        mix_m = re.search(r'^(.*[A-Za-z])\s*/\s*([A-Za-z].*)$', v)
        if not mix_m or l.box_type == 'MIX':
            result.append(l)
            continue
        c1 = mix_m.group(1).strip().upper()
        c2 = mix_m.group(2).strip().upper()
        half_stems = l.stems // 2
        half_total = round(l.line_total / 2, 2)
        half_bunches = l.bunches // 2 if l.bunches else 0
        for cv in (c1, c2):
            nl = copy(l)
            nl.variety = cv
            nl.stems = half_stems
            nl.line_total = half_total
            nl.bunches = half_bunches
            nl.box_type = 'MIX'
            result.append(nl)
    return result

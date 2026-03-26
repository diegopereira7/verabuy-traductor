"""Procesador no-interactivo de facturas PDF para VeraBuy Web.

Uso: python procesar_pdf.py <ruta_pdf>
Salida: JSON en stdout
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.pdf import detect_provider
from src.parsers import FORMAT_PARSERS
from src.articulos import ArticulosLoader
from src.sinonimos import SynonymStore
from src.matcher import Matcher, rescue_unparsed_lines, split_mixed_boxes
from src.config import SQL_FILE, SYNS_FILE


def run(pdf_path: str) -> dict:
    """Procesa un PDF y devuelve el resultado como dict JSON-serializable."""
    pdata = detect_provider(pdf_path)
    if not pdata:
        return {'ok': False, 'error': 'Proveedor no reconocido en el PDF'}

    fmt = pdata.get('fmt', '')
    parser = FORMAT_PARSERS.get(fmt)
    if not parser:
        return {'ok': False, 'error': f'Sin parser para formato "{fmt}"'}

    if not SQL_FILE.exists():
        return {'ok': False, 'error': f'No se encuentra la BD de artículos: {SQL_FILE}'}

    art = ArticulosLoader()
    art.load_from_sql(str(SQL_FILE))

    syn = SynonymStore(str(SYNS_FILE))
    matcher = Matcher(art, syn)

    header, lines = parser.parse(pdata['text'], pdata)
    lines = split_mixed_boxes(lines)
    rescued = rescue_unparsed_lines(pdata['text'], lines)
    lines = matcher.match_all(pdata['id'], lines)
    lines.extend(rescued)

    ok_count = sum(1 for l in lines if l.match_status == 'ok')
    no_parser = sum(1 for l in lines if l.match_status == 'sin_parser')

    return {
        'ok': True,
        'header': {
            'invoice_number': header.invoice_number,
            'date':           header.date,
            'awb':            header.awb,
            'hawb':           getattr(header, 'hawb', ''),
            'provider_name':  header.provider_name,
            'provider_id':    header.provider_id,
            'total':          header.total,
        },
        'stats': {
            'total_lineas': len(lines),
            'ok':           ok_count,
            'sin_match':    len(lines) - ok_count - no_parser,
            'sin_parser':   no_parser,
        },
        'lines': [{
            'raw':             l.raw_description[:120],
            'species':         l.species,
            'variety':         l.variety,
            'grade':           l.grade,
            'size':            l.size,
            'stems_per_bunch': l.stems_per_bunch,
            'stems':           l.stems,
            'price_per_stem':  round(l.price_per_stem, 5),
            'line_total':      round(l.line_total, 2),
            'label':           l.label,
            'box_type':        l.box_type,
            'articulo_id':     l.articulo_id,
            'articulo_name':   l.articulo_name or '',
            'match_status':    l.match_status,
            'match_method':    l.match_method,
        } for l in lines],
    }


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        print(json.dumps({'ok': False, 'error': 'Uso: procesar_pdf.py <ruta_pdf>'}))
        sys.exit(1)
    result = run(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, default=str))

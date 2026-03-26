"""Auditoría y limpieza de sinónimos: detecta genéricos que tienen equivalente con marca.

Uso:
  py auditar_sinonimos.py              # Solo informe (dry-run)
  py auditar_sinonimos.py --apply      # Aplicar limpieza
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

from src.config import SQL_FILE, SYNS_FILE, BRAND_IGNORE_SUFFIXES
from src.articulos import ArticulosLoader

# ── Constantes ───────────────────────────────────────────────────────────────

# Palabras que NO son marcas (flores, colores, tamaños, calidades, etc.)
EXCLUIR_COMO_MARCA = {
    # Flores
    'ROSA', 'CLAVEL', 'HORTENSIA', 'HYDRANGEA', 'PANICULATA', 'ALSTROMERIA',
    'CRISANTEMO', 'GYPSOPHILA', 'MINI',
    # Orígenes
    'EC', 'COL', 'ECUADOR', 'COLOMBIA',
    # Calidades
    'PREMIUM', 'FANCY', 'SELECT', 'STANDARD', 'STD',
    # Colores
    'ROJO', 'BLANCO', 'ROSA', 'AMARILLO', 'NARANJA', 'VERDE', 'AZUL',
    'LILA', 'CREMA', 'SALMON', 'BICOLOR', 'MIXTO', 'NOVEDADES',
    'RED', 'WHITE', 'PINK', 'YELLOW', 'ORANGE', 'GREEN', 'BLUE',
    'BURGUNDY', 'GRANATE', 'OSCURO', 'CLARO', 'CRIOLLA',
    # Tamaños/Unidades
    'CM', 'GR', 'KG',
    # Tipos
    'MIX', 'FLOWERS', 'ROSES', 'GARDENS', 'NATURAL', 'GRANEL',
    'DIRECT', 'CONT', 'INCH', 'SPRAY',
    # Prefijos de artículo
    'BI', 'SP', 'SA',
} | BRAND_IGNORE_SUFFIXES


def cargar_marcas_sql() -> set[str]:
    """Extrae marcas/farms de los nombres de artículos en el dump SQL."""
    art = ArticulosLoader()
    art.load_from_sql(str(SQL_FILE))
    art._build_brand_index()

    # Marcas del índice de brand_by_provider
    marcas = set(art.brand_by_provider.values())

    # También extraer sufijos frecuentes manualmente
    sufijos = defaultdict(int)
    for a in art.articulos.values():
        parts = a['nombre'].upper().strip().split()
        if len(parts) >= 3:
            last = parts[-1]
            if (len(last) >= 3 and last.isalpha()
                    and last not in EXCLUIR_COMO_MARCA
                    and not re.match(r'^\d+U?$', last)):
                sufijos[last] += 1

    # Solo considerar sufijos con >= 3 artículos
    for suf, count in sufijos.items():
        if count >= 3:
            marcas.add(suf)

    return marcas


def detectar_marca(nombre_articulo: str, marcas: set[str]) -> str | None:
    """Detecta si un nombre de artículo contiene una marca conocida al final."""
    parts = nombre_articulo.upper().strip().split()
    if not parts:
        return None

    # Última palabra
    if parts[-1] in marcas:
        return parts[-1]

    return None


def nombre_base(nombre: str, marcas: set[str]) -> str:
    """Extrae el nombre base sin marca, origen ni tamaño."""
    n = nombre.upper().strip()
    # Quitar marca al final
    parts = n.split()
    if parts and parts[-1] in marcas:
        parts = parts[:-1]
    n = ' '.join(parts)
    # Quitar origen
    n = re.sub(r'\b(EC|COL)\b', '', n)
    # Quitar tamaño y unidades
    n = re.sub(r'\b\d+CM\b', '', n)
    n = re.sub(r'\b\d+U\b', '', n)
    n = re.sub(r'\b\d+GR\b', '', n)
    # Normalizar espacios
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def auditar(apply: bool = False):
    """Ejecuta la auditoría de sinónimos."""
    # Cargar datos
    syns = json.loads(SYNS_FILE.read_text(encoding='utf-8'))
    marcas = cargar_marcas_sql()

    print(f'Marcas/farms detectadas ({len(marcas)}): {", ".join(sorted(marcas))}')
    print()

    # Clasificar sinónimos
    con_marca = {}    # key -> (entry, marca)
    sin_marca = {}    # key -> entry

    for key, entry in syns.items():
        art_name = entry.get('articulo_name', '')
        marca = detectar_marca(art_name, marcas)
        if marca:
            con_marca[key] = (entry, marca)
        else:
            sin_marca[key] = entry

    # Agrupar por articulo_id
    por_articulo: dict[int, dict[str, dict]] = defaultdict(dict)
    for key, entry in syns.items():
        aid = entry.get('articulo_id', 0)
        if aid > 0:
            por_articulo[aid][key] = entry

    # Detectar genéricos que tienen equivalente con marca
    a_eliminar = {}    # key -> (entry, razon)
    a_conservar = {}   # key -> entry

    for aid, entries in por_articulo.items():
        branded_keys = []
        generic_keys = []

        for key, entry in entries.items():
            art_name = entry.get('articulo_name', '')
            marca = detectar_marca(art_name, marcas)
            if marca:
                branded_keys.append((key, entry, marca))
            else:
                generic_keys.append((key, entry))

        if branded_keys and generic_keys:
            # Hay branded Y genéricos para el MISMO artículo
            for gkey, gentry in generic_keys:
                marcas_str = ', '.join(m for _, _, m in branded_keys)
                a_eliminar[gkey] = (gentry, f'Artículo {aid}: existe con marca {marcas_str}')
            for bkey, bentry, marca in branded_keys:
                a_conservar[bkey] = bentry
        else:
            # Solo genéricos O solo branded — conservar todos
            for key, entry in entries.items():
                a_conservar[key] = entry

    # También detectar entradas con provider_id=0 que tienen equivalente con provider real
    entradas_pid0 = {k: v for k, v in syns.items() if v.get('provider_id', 0) == 0}
    for key0, entry0 in entradas_pid0.items():
        if key0 in a_eliminar:
            continue  # Ya marcado
        # Buscar si hay otra entrada con mismo variety/size/spb pero provider_id != 0
        parts = key0.split('|')
        if len(parts) >= 5:
            species, variety, size, spb = parts[1], parts[2], parts[3], parts[4]
            for other_key, other_entry in syns.items():
                if other_key == key0:
                    continue
                other_parts = other_key.split('|')
                if (len(other_parts) >= 5 and other_parts[1] == species
                        and other_parts[2] == variety and other_parts[3] == size
                        and other_parts[4] == spb and other_entry.get('provider_id', 0) != 0):
                    a_eliminar[key0] = (entry0, f'provider_id=0, existe con provider {other_entry.get("provider_id")}')
                    break

    # ── INFORME ──────────────────────────────────────────────────────────────

    print('═' * 60)
    print('INFORME DE AUDITORÍA DE SINÓNIMOS')
    print('═' * 60)
    print()
    print(f'Total sinónimos: {len(syns)}')
    print(f'Con marca detectada: {len(con_marca)}')
    print(f'Genéricos (sin marca): {len(sin_marca)}')
    print()

    if a_eliminar:
        print(f'SINÓNIMOS A ELIMINAR: {len(a_eliminar)}')
        print('─' * 60)
        for key, (entry, razon) in sorted(a_eliminar.items()):
            print(f'  ✗ {key}')
            print(f'    → {entry.get("articulo_name", "")} (id={entry.get("articulo_id")})')
            print(f'    Razón: {razon}')
            print()
    else:
        print('No se encontraron sinónimos genéricos duplicados.')
        print()

    print(f'RESUMEN:')
    print(f'  Sinónimos a eliminar: {len(a_eliminar)}')
    print(f'  Sinónimos a conservar: {len(syns) - len(a_eliminar)}')
    print()

    # Genéricos sin equivalente branded (se conservan)
    genericos_unicos = {k: v for k, v in sin_marca.items() if k not in a_eliminar}
    print(f'Genéricos sin equivalente con marca (se conservan): {len(genericos_unicos)}')

    if not apply:
        print()
        print('Modo dry-run. Usa --apply para ejecutar la limpieza.')
        return

    if not a_eliminar:
        print('Nada que limpiar.')
        return

    # ── APLICAR LIMPIEZA ─────────────────────────────────────────────────────

    # Guardar registro de cambios
    cambios = {
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'eliminados': len(a_eliminar),
        'antes': len(syns),
        'despues': len(syns) - len(a_eliminar),
        'detalle': [{
            'key': k,
            'articulo_id': e.get('articulo_id'),
            'articulo_name': e.get('articulo_name'),
            'razon': r,
        } for k, (e, r) in a_eliminar.items()],
    }

    cambios_file = Path(f'sinonimos_limpieza_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    cambios_file.write_text(json.dumps(cambios, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nRegistro de cambios: {cambios_file}')

    # Eliminar y guardar
    for key in a_eliminar:
        del syns[key]

    SYNS_FILE.write_text(
        json.dumps(syns, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    print(f'Limpieza aplicada: {len(a_eliminar)} entradas eliminadas.')
    print(f'Nuevo total: {len(syns)} sinónimos.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Auditoría de sinónimos')
    parser.add_argument('--apply', action='store_true', help='Aplicar limpieza')
    args = parser.parse_args()
    auditar(apply=args.apply)

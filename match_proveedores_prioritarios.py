"""Matching dirigido para los 7 proveedores prioritarios con 0% o bajo OK.

Limpia las variedades mal parseadas antes de usar search_with_priority().
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.articulos import ArticulosLoader, _normalize
from src.config import SQL_FILE, PROVIDERS

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

EXCEL_FILE = Path('lineas_pendientes_2026.xlsx')
SYNS_FILE = Path('sinonimos_universal.json')

TARGET_PROVIDERS = {
    'Multiflora', 'Daflor', 'Floricola La Rosaleda', 'Life Flowers',
    'Flores de Aposentos', 'Turflor', 'Unique Flowers',
}


def get_provider_id(name: str) -> int:
    name_up = name.upper().strip()
    for pkey, pdata in PROVIDERS.items():
        if pdata['name'].upper() == name_up:
            return pdata['id']
    for pkey, pdata in PROVIDERS.items():
        if name_up in pdata['name'].upper() or pdata['name'].upper() in name_up:
            return pdata['id']
    return 0


def get_provider_key(name: str) -> str:
    name_up = name.upper().strip()
    for pkey, pdata in PROVIDERS.items():
        if pdata['name'].upper() == name_up:
            return pkey
    for pkey, pdata in PROVIDERS.items():
        if name_up in pdata['name'].upper() or pdata['name'].upper() in name_up:
            return pkey
    return ''


# =============================================================================
# Limpieza de variedades por proveedor
# =============================================================================

def clean_variety_life(variety: str, desc: str) -> tuple[str, int]:
    """Life Flowers: 'MARL EXPLORER' → 'EXPLORER'. MARL es una farm/label.
    Also strips other farm prefixes: BRUNA, MERCO, AMALIA COSTA, etc.
    """
    v = variety.upper().strip()
    # Known farm/label prefixes in Life Flowers invoices (longest first)
    farm_prefixes = [
        'MARGARIDA LOPES ', 'CAMPO FLOR ', 'AMALIA COSTA ', 'C ORQUIDEA ',
        'M ANJOS ', 'MARL ', 'MARLX ', 'MARLT ', 'BRUNA ',
        'MERCO ', 'AROMA ', 'FARM ', 'LETI ', 'NATI ',
        'RODRIGO ', 'DANTAS ', 'COSTA ', 'PINTO ', 'SILVA ',
    ]
    for prefix in farm_prefixes:
        if v.startswith(prefix):
            v = v[len(prefix):]
            break
    return v, 0


def clean_variety_rosaleda(variety: str, desc: str) -> tuple[str, int]:
    """Rosaleda: 'EURO ROSALEDA FRUTTETO' → 'FRUTTETO'.
    Prefijos de destino/marca: EURO ROSALEDA, USA ROSALEDA, EUR ROSALEDA.
    """
    v = variety.upper().strip()
    # Strip destination+brand prefixes
    for prefix in ('EURO ROSALEDA ', 'USA ROSALEDA ', 'EUR ROSALEDA ',
                   'ROSALEDA ', 'EU ROSALEDA ', 'EUR ', 'EURO '):
        if v.startswith(prefix):
            v = v[len(prefix):]
            break
    return v, 0


def clean_variety_turflor(variety: str, desc: str) -> tuple[str, int]:
    """Turflor: 'CARNATION RED' → color=ROJO. 'SPRAY CARNATION RAINBOW' → spray.
    Returns (cleaned_variety, 0).
    The variety for carnations is the COLOR, not the flower name.
    """
    v = variety.upper().strip()
    # Carnation varieties: CARNATION <COLOR> → just the color
    # Spray Carnation <COLOR> → keep SPRAY prefix for mini clavel
    if v.startswith('SPRAY CARNATION '):
        color = v[len('SPRAY CARNATION '):]
        return f"SPRAY {color}", 0
    if v.startswith('CARNATION '):
        color = v[len('CARNATION '):]
        return color, 0
    # ASSORTED FANCY, MIX FANCY → MIXTO
    if 'ASSORTED' in v or v == 'MIX FANCY' or v == 'MIXED':
        return 'MIXTO', 0
    return v, 0


def clean_variety_multiflora(variety: str, desc: str) -> tuple[str, int]:
    """Multiflora: alstroemeria ASSORTED → MIXTO, WHISTLER → WHISTLER."""
    v = variety.upper().strip()
    if v == 'ASSORTED':
        # Try to extract grade from description (PERFECTION, SELECT, etc.)
        desc_up = desc.upper()
        grade = ''
        for g in ('PERFECTION', 'SUPERSELECT', 'SELECT', 'FANCY'):
            if g in desc_up:
                grade = g
                break
        return f"MIXTO", 0  # Will be combined with grade in search
    return v, 0


def clean_variety_daflor(variety: str, desc: str) -> tuple[str, int]:
    """Daflor: alstroemeria varieties + roses from descriptions.
    ASSORTED → MIXTO. Also parse roses from (NO PARSEADO) lines.
    """
    v = variety.upper().strip()
    if v == 'ASSORTED':
        return 'MIXTO', 0
    if v == '(NO PARSEADO)':
        desc_up = desc.upper()
        # "Rosa Pink O'hara - 50" or "Rosa White O'Hara - 50"
        m = re.search(r'ROSA\s+(?:PINK|WHITE|RED)?\s*O.?HARA\s*-\s*(\d+)', desc_up)
        if m:
            color_m = re.search(r'ROSA\s+(PINK|WHITE|RED)', desc_up)
            color = color_m.group(1) if color_m else ''
            talla = int(m.group(1))
            return f"OHARA {color}".strip(), talla
        # "Rosa <variety> - <size>"
        m = re.search(r'ROSA\s+(.+?)\s*-\s*(\d+)', desc_up)
        if m:
            return m.group(1).strip(), int(m.group(2))
    return v, 0


def clean_variety_aposentos(variety: str, desc: str) -> tuple[str, int]:
    """Aposentos: carnation named varieties like 'DON PEDRO RED' → extract color.
    'BICOLORES SURTIDOS BICOLOR' → 'BICOLOR'.
    'NOVEDADES CRN NOVELTY' → 'NOVEDADES'.
    Named varieties with color suffix: 'COWBOY ORANGE' → 'NARANJA'.
    """
    v = variety.upper().strip()
    # Remove redundant prefixes
    for prefix in ('NOVEDADES CRN ', 'CRN '):
        if v.startswith(prefix):
            v = v[len(prefix):]
    # Special cases
    if v == 'BICOLORES SURTIDOS BICOLOR':
        return 'BICOLOR', 0
    if v in ('SURTIDO', 'SURTIDOS', 'MIXTO'):
        return 'MIXTO', 0
    if v == 'NOVELTY' or v == 'NOVELTIES':
        return 'NOVEDADES', 0
    # Extract trailing color from named varieties: "DON PEDRO RED" → RED
    # "MOON LIGTH WHITE" → WHITE, "ILIAS YELLOW" → YELLOW
    color_words = {'RED', 'WHITE', 'YELLOW', 'PINK', 'ORANGE', 'GREEN', 'PURPLE',
                   'SALMON', 'PEACH', 'BICOLOR', 'LAVENDER', 'LILAC'}
    words = v.split()
    if words and words[-1] in color_words:
        return words[-1], 0
    return v, 0


def clean_variety_unique(variety: str, desc: str) -> tuple[str, int]:
    """Unique: 'RED FREEDOM 60' → 'FREEDOM' talla=60.
    'IVORY VENDELA' → 'VENDELA'.
    """
    v = variety.upper().strip()
    if v == 'ASSORTED':
        return 'SURTIDO MIXTO', 0
    # Pattern: COLOR VARIETY SIZE → extract variety and size
    m = re.match(r'(?:RED|PINK|WHITE|IVORY|HOT)\s+(.+?)\s+(\d+)$', v)
    if m:
        return m.group(1), int(m.group(2))
    m = re.match(r'(?:RED|PINK|WHITE|IVORY|HOT)\s+(.+)$', v)
    if m:
        return m.group(1), 0
    # Trailing number is talla
    m = re.match(r'(.+?)\s+(\d+)$', v)
    if m:
        return m.group(1), int(m.group(2))
    return v, 0


CLEANERS = {
    'Life Flowers': clean_variety_life,
    'Floricola La Rosaleda': clean_variety_rosaleda,
    'Turflor': clean_variety_turflor,
    'Multiflora': clean_variety_multiflora,
    'Daflor': clean_variety_daflor,
    'Flores de Aposentos': clean_variety_aposentos,
    'Unique Flowers': clean_variety_unique,
}


# =============================================================================
# Matching especial para claveles (Turflor, Aposentos)
# =============================================================================

# Color inglés → español for carnation color matching
COLOR_MAP = {
    'WHITE': 'BLANCO', 'RED': 'ROJO', 'YELLOW': 'AMARILLO', 'PINK': 'ROSA',
    'ORANGE': 'NARANJA', 'GREEN': 'VERDE', 'PURPLE': 'MORADO', 'BICOLOR': 'BICOLOR',
    'NOVELTY': 'NOVEDADES', 'NOVELTIES': 'NOVEDADES', 'RAINBOW': 'RAINBOW',
    'MIXED': 'MIXTO', 'MIX': 'MIXTO', 'ASSORTED': 'MIXTO',
    'SALMON': 'SALMON', 'PEACH': 'MELOCOTON', 'BROWN': 'MARRON',
    'LAVENDER': 'LAVANDA', 'LILAC': 'LILA', 'BURGUNDY': 'GRANATE',
    'CREAM': 'CREMA', 'FUCHSIA': 'FUCSIA', 'FUCSIA': 'FUCSIA',
}


def match_carnation(variety: str, grade: str, provider_id: int,
                    art: ArticulosLoader) -> tuple[dict | None, str, str]:
    """Match a carnation by translating color + grade + provider brand."""
    v = _normalize(variety)
    brands = art._get_brands(provider_id)

    # Determine if spray
    is_spray = 'SPRAY' in v
    if is_spray:
        v = v.replace('SPRAY', '').strip()

    # Translate color
    color = COLOR_MAP.get(v, v)
    # Also try word-by-word
    if color == v:
        words = v.split()
        translated = [COLOR_MAP.get(w, w) for w in words]
        color = ' '.join(translated)

    # Build search patterns for clavel articles
    # Try: CLAVEL FANCY <color> 70CM, CLAVEL SELECT <color> 70CM, etc.
    grade_map = {
        'FANCY': 'FANCY', 'SELECT': 'SELECT', 'STANDARD': 'ESTANDAR',
        'STD': 'ESTANDAR', '': 'FANCY',  # Default to FANCY
    }
    grade_es = grade_map.get(grade.upper(), grade.upper())

    prefix = 'MINI CLAVEL' if is_spray else 'CLAVEL'

    # Search by name in by_name index
    patterns = []
    for sz in [70, 60, 40]:
        for spb in [20, 25, 10]:
            if brands:
                for brand in brands:
                    patterns.append(f"{prefix} {grade_es} {color} {sz}CM {spb}U {brand}")
            patterns.append(f"{prefix} COL {grade_es} {color} {sz}CM {spb}U")
            patterns.append(f"{prefix} {grade_es} {color} {sz}CM {spb}U")

    for pat in patterns:
        pat_norm = _normalize(pat)
        if pat_norm in art.by_name:
            a = art.articulos[art.by_name[pat_norm]]
            conf = 'ALTA' if any(b in pat_norm for b in brands) else 'BAJA'
            return a, conf, f'clavel_{grade_es.lower()}+color'
        # Try without grade
        no_grade = pat_norm.replace(f" {_normalize(grade_es)} ", ' ')
        if no_grade in art.by_name:
            a = art.articulos[art.by_name[no_grade]]
            return a, 'BAJA', 'clavel+color(sin_grade)'

    # Try all grades as fallback
    for fallback_grade in ['FANCY', 'SELECT', 'ESTANDAR']:
        if fallback_grade == grade_es:
            continue
        for sz in [70, 60]:
            for spb in [20, 25]:
                if brands:
                    for brand in brands:
                        pat = f"{prefix} {fallback_grade} {color} {sz}CM {spb}U {brand}"
                        if _normalize(pat) in art.by_name:
                            a = art.articulos[art.by_name[_normalize(pat)]]
                            return a, 'MEDIA', f'clavel_{fallback_grade.lower()}+marca(grade_fallback)'
                pat = f"{prefix} COL {fallback_grade} {color} {sz}CM {spb}U"
                if _normalize(pat) in art.by_name:
                    a = art.articulos[art.by_name[_normalize(pat)]]
                    return a, 'BAJA', f'clavel_{fallback_grade.lower()}+generico'
                pat = f"{prefix} {fallback_grade} {color} {sz}CM {spb}U"
                if _normalize(pat) in art.by_name:
                    a = art.articulos[art.by_name[_normalize(pat)]]
                    return a, 'BAJA', f'clavel_{fallback_grade.lower()}+generico'

    # Fallback: search by provider_id
    for a in art.articulos.values():
        if a['id_proveedor'] == provider_id:
            nombre = _normalize(a['nombre'])
            if color in nombre and prefix.split()[0] in nombre:
                return a, 'MEDIA', 'clavel+proveedor_id'

    return None, '', 'sin_match'


# =============================================================================
# Matching especial para alstroemeria (Multiflora, Daflor)
# =============================================================================

def match_alstroemeria(variety: str, desc: str, provider_id: int,
                       art: ArticulosLoader) -> tuple[dict | None, str, str]:
    """Match alstroemeria by variety name + grade + provider brand."""
    v = _normalize(variety)
    brands = art._get_brands(provider_id)

    # Extract grade from description
    desc_up = desc.upper()
    grade = ''
    for g in ('PERFECTION', 'SUPERSELECT', 'SUPER SELECT', 'SELECTO', 'SELECT', 'FANCY'):
        if g in desc_up:
            grade = g.replace('SUPER SELECT', 'SUPERSELECT').replace('SELECTO', 'SELECT')
            break

    # ASSORTED/MIXTO → search by grade + MIXTO
    if v in ('MIXTO', 'ASSORTED', 'SURTIDO'):
        v = 'MIXTO'

    # Also handle NADYA→NADIA spelling variation
    v_variants = [v]
    if v == 'NADYA':
        v_variants.append('NADIA')
    if v == 'ILSA':
        v_variants.append('ISA')

    # Step 1: Search by_variety with grade prefix (e.g., "FANCY FUJI")
    for vv in v_variants:
        search_keys = []
        if grade:
            search_keys.append(f"{grade} {vv}")
        search_keys.append(vv)
        # Also try COL prefix variants
        if grade:
            search_keys.append(f"COL {grade} {vv}")

        for sk in search_keys:
            candidates = art.by_variety.get(sk, [])
            if candidates:
                # Prefer with brand
                if brands:
                    for c in candidates:
                        if art._has_brand(c, brands):
                            return c, 'ALTA', f'alstro_{grade.lower() or "direct"}+marca'
                # Then by provider_id
                for c in candidates:
                    if c['id_proveedor'] == provider_id:
                        return c, 'MEDIA', f'alstro_{grade.lower() or "direct"}+proveedor'
                # Then generic
                return candidates[0], 'BAJA', f'alstro_{grade.lower() or "direct"}+generico'

    # Step 2: Build full name patterns for by_name search
    patterns = []
    for vv in v_variants:
        for sz in [70, 80]:
            for spb in [10]:
                if brands:
                    for brand in brands:
                        if grade:
                            patterns.append(f"ALSTROMERIA {grade} {vv} {sz}CM {spb}U {brand}")
                        patterns.append(f"ALSTROMERIA {vv} {sz}CM {spb}U {brand}")
                if grade:
                    patterns.append(f"ALSTROMERIA {grade} {vv} {sz}CM {spb}U")
                    patterns.append(f"ALSTROMERIA COL {grade} {vv} {sz}CM {spb}U")
                patterns.append(f"ALSTROMERIA {vv} {sz}CM {spb}U")

    for pat in patterns:
        pat_norm = _normalize(pat)
        if pat_norm in art.by_name:
            a = art.articulos[art.by_name[pat_norm]]
            conf = 'ALTA' if any(b in pat_norm for b in brands) else 'BAJA'
            return a, conf, f'alstro_{grade.lower() or "direct"}'

    # Step 3: search provider articles containing variety
    for vv in v_variants:
        for a in art.articulos.values():
            if a['id_proveedor'] == provider_id:
                nombre = _normalize(a['nombre'])
                if vv in nombre and 'ALSTRO' in nombre:
                    return a, 'MEDIA', 'alstro+proveedor_id'

    # Step 4: any alstroemeria with that variety
    for vv in v_variants:
        for a in art.articulos.values():
            nombre = _normalize(a['nombre'])
            if 'ALSTRO' in nombre and vv in nombre:
                return a, 'BAJA', 'alstro+generico'

    return None, '', 'sin_match'


# =============================================================================
# Main
# =============================================================================

def main():
    logger.info("=== MATCHING PROVEEDORES PRIORITARIOS ===")

    art = ArticulosLoader()
    art.load_from_sql(str(SQL_FILE))

    # Load Excel
    wb = openpyxl.load_workbook(EXCEL_FILE, read_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        vals = list(row)
        prov = vals[1] or ''
        if prov not in TARGET_PROVIDERS:
            continue
        if vals[7]:  # ya tiene código
            continue
        rows.append({
            'pdf': vals[0] or '',
            'proveedor': prov,
            'descripcion': vals[2] or '',
            'especie': vals[3] or '',
            'variedad': vals[4] or '',
            'talla': int(vals[5]) if vals[5] else 0,
            'tallos': vals[6],
        })
    wb.close()
    logger.info(f"Lineas sin match de proveedores prioritarios: {len(rows)}")

    # Load existing synonyms
    with open(SYNS_FILE, 'r', encoding='utf-8') as f:
        syns = json.load(f)
    before_count = len(syns)

    # Process each line
    results_by_prov = defaultdict(lambda: {'total': 0, 'matched': 0, 'alta': 0, 'media': 0, 'baja': 0})
    new_syns = {}

    for row in rows:
        prov = row['proveedor']
        especie = row['especie']
        variety = row['variedad']
        talla = row['talla']
        desc = row['descripcion']
        stats = results_by_prov[prov]
        stats['total'] += 1

        # Reclassify OTHER/(NO PARSEADO) lines from description
        if especie == 'OTHER' and variety == '(NO PARSEADO)':
            desc_up = desc.upper()
            if 'CLAVEL' in desc_up or 'CARNATION' in desc_up:
                especie = 'CARNATIONS'
                # Extract color/variety from desc
                m = re.search(r'CLAVEL\s+SURTIDO(?:\s+(RED/WHITE|MIXTO|[\w]+))?', desc_up)
                if m:
                    variety = m.group(1) or 'MIXTO'
                else:
                    m = re.search(r'CARNATION\s+(\w[\w\s]*?)(?:\s+\d|\s*$)', desc_up)
                    variety = m.group(1).strip() if m else 'MIXTO'
            elif 'ROSA' in desc_up or 'ROSE' in desc_up:
                especie = 'ROSES'
                m = re.search(r'ROSA?\s+(.+?)\s*(?:-\s*(\d+)|\s+(\d+)\s)', desc_up)
                if m:
                    variety = m.group(1).strip()
                    t = m.group(2) or m.group(3)
                    if t:
                        talla = int(t)
            elif 'SPRAY' in desc_up and 'CARNATION' in desc_up:
                especie = 'CARNATIONS'
                variety = 'SPRAY MIXTO'

        # Clean variety
        cleaner = CLEANERS.get(prov)
        cleaned_variety = variety
        extra_talla = 0
        if cleaner:
            cleaned_variety, extra_talla = cleaner(variety, desc)
        if extra_talla and not talla:
            talla = extra_talla

        pid = get_provider_id(prov)
        pkey = get_provider_key(prov)

        result = None
        confidence = ''
        method = 'sin_match'

        # Species-specific matching
        if especie == 'CARNATIONS' and prov in ('Turflor', 'Flores de Aposentos'):
            # Extract grade from description
            grade = ''
            desc_up = desc.upper()
            for g in ('FANCY', 'SELECT', 'STANDARD', 'STD'):
                if g in desc_up:
                    grade = g
                    break
            result, confidence, method = match_carnation(
                cleaned_variety, grade, pid, art)

        elif especie == 'ALSTROEMERIA' and prov in ('Multiflora', 'Daflor'):
            result, confidence, method = match_alstroemeria(
                cleaned_variety, desc, pid, art)

        elif especie == 'ALSTROEMERIA' and prov == 'Turflor':
            result, confidence, method = match_alstroemeria(
                cleaned_variety, desc, pid, art)

        else:
            # General matching with cleaned variety
            result, confidence, method = art.search_with_priority(
                variety=cleaned_variety,
                size=talla,
                provider_id=pid,
                provider_key=pkey,
            )

        if result:
            stats['matched'] += 1
            if confidence == 'ALTA':
                stats['alta'] += 1
            elif confidence == 'MEDIA':
                stats['media'] += 1
            else:
                stats['baja'] += 1

            # Build synonym key
            uni_key = f"{pid}|{especie}|{_normalize(variety)}|{talla}|0|"
            if uni_key not in syns and confidence in ('ALTA', 'MEDIA'):
                entry = {
                    'articulo_id': result['id'],
                    'articulo_name': result['nombre'],
                    'origen': 'auto-matching',
                    'provider_id': pid,
                    'species': especie,
                    'variety': _normalize(variety),
                    'size': talla,
                    'stems_per_bunch': 0,
                    'grade': '',
                }
                new_syns[uni_key] = entry

    # Print results per provider
    print("\n" + "=" * 70)
    print("  RESULTADOS POR PROVEEDOR")
    print("=" * 70)
    for prov in sorted(results_by_prov.keys()):
        s = results_by_prov[prov]
        pct = s['matched'] / s['total'] * 100 if s['total'] else 0
        print(f"  {prov:30s}  {s['matched']:4d}/{s['total']:4d} ({pct:5.1f}%)  "
              f"ALTA={s['alta']}  MEDIA={s['media']}  BAJA={s['baja']}")
    print("-" * 70)
    total = sum(s['total'] for s in results_by_prov.values())
    matched = sum(s['matched'] for s in results_by_prov.values())
    pct = matched / total * 100 if total else 0
    print(f"  {'TOTAL':30s}  {matched:4d}/{total:4d} ({pct:5.1f}%)")
    print(f"  Sinonimos nuevos ALTA/MEDIA: {len(new_syns)}")
    print("=" * 70)

    # Merge new synonyms into universal
    added = 0
    upgraded = 0
    for k, v in new_syns.items():
        if k in syns:
            old = syns[k]
            if old.get('origen') in ('auto', 'auto-fuzzy'):
                syns[k] = v
                upgraded += 1
        else:
            syns[k] = v
            added += 1

    with open(SYNS_FILE, 'w', encoding='utf-8') as f:
        json.dump(syns, f, indent=2, ensure_ascii=False)

    after_count = len(syns)
    print(f"\n  sinonimos_universal.json: {before_count} -> {after_count}")
    print(f"  Nuevos: {added}, Actualizados: {upgraded}")


if __name__ == '__main__':
    main()

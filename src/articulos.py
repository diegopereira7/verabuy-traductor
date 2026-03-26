"""Cargador e indexador de artículos desde el dump SQL de VeraBuy."""
from __future__ import annotations

import logging
import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from src.config import (
    FILE_ENCODING, SPECIES_PREFIXES, BRAND_IGNORE_SUFFIXES, BRAND_MIN_ARTICLES,
    strip_provider_suffix, translate_carnation_color, DEFAULT_SIZE_CARNATIONS,
)
from src.models import InvoiceLine

logger = logging.getLogger(__name__)


class ArticulosLoader:
    """Carga artículos del dump SQL y los indexa para búsqueda rápida."""

    def __init__(self):
        self.articulos: Dict[int, dict] = {}
        self.by_name: Dict[str, int] = {}
        self.rosas_ec: Dict[str, int] = {}
        self.rosas_col: Dict[str, int] = {}
        self.by_species: Dict[str, List] = {}
        self.brand_by_provider: Dict[int, str] = {}
        self.loaded = False

    def load_from_sql(self, sql_path: str) -> int:
        """Carga artículos desde un dump SQL de INSERT statements.

        Args:
            sql_path: Ruta al fichero .sql.

        Returns:
            Número de artículos cargados.
        """
        count = 0
        for sp in set(SPECIES_PREFIXES.values()):
            self.by_species[sp] = []

        with open(sql_path, 'r', encoding=FILE_ENCODING) as f:
            for raw in f:
                ln = raw.strip()
                if not ln.startswith('('):
                    continue
                ln = ln.rstrip(',;')
                try:
                    art = self._parse_row(ln)
                    if not art:
                        continue
                    self.articulos[art['id']] = art
                    nombre = art['nombre']
                    if nombre:
                        self.by_name[nombre.upper()] = art['id']
                        clean = strip_provider_suffix(nombre.upper())
                        if clean != nombre.upper():
                            self.by_name[clean] = art['id']
                        self._index_species(art)
                    count += 1
                except (ValueError, IndexError):
                    continue

        self._build_brand_index()
        self.loaded = True
        logger.info("Artículos cargados: %d, rosas EC: %d", count, len(self.rosas_ec))
        return count

    # --- Búsquedas ---

    def find_by_name(self, name: str) -> Optional[dict]:
        """Busca un artículo por nombre exacto."""
        name = name.upper().strip()
        if name in self.by_name:
            return self.articulos[self.by_name[name]]
        no_orig = re.sub(r'^(ROSA)\s+(EC|COL)\s+', r'\1 ', name)
        if no_orig != name and no_orig in self.by_name:
            return self.articulos[self.by_name[no_orig]]
        return None

    def find_branded(self, name: str, provider_id: int, provider_key: str = '') -> Optional[dict]:
        """Busca artículo con el sufijo de marca del proveedor.

        Args:
            name: Nombre esperado genérico (ej: 'ROSA EC MONDIAL 50CM 25U').
            provider_id: ID del proveedor en VeraBuy.
            provider_key: Clave del proveedor en PROVIDERS.

        Returns:
            Artículo con marca si existe (ej: 'ROSA MONDIAL 50CM 25U CERES'), None si no.
        """
        brands = set()
        # Marca del índice SQL (por id_proveedor del artículo)
        b = self.brand_by_provider.get(provider_id)
        if b:
            brands.add(b)
        # Marca de la clave del proveedor en PROVIDERS
        if provider_key:
            brands.add(provider_key.upper())
        # Buscar también marcas de otros providers con el mismo fmt (aliases)
        # Ej: cantiza(2222) y valtho(435) comparten fmt='cantiza'
        from src.config import PROVIDERS
        for pkey, pdata in PROVIDERS.items():
            if pdata.get('id') == provider_id:
                brands.add(pkey.upper())
                # Buscar marcas de otros providers con mismo fmt
                fmt = pdata.get('fmt', '')
                for pkey2, pdata2 in PROVIDERS.items():
                    if pdata2.get('fmt') == fmt and pdata2.get('id') != provider_id:
                        b2 = self.brand_by_provider.get(pdata2['id'])
                        if b2:
                            brands.add(b2)
                break
        if not brands:
            return None
        name = name.upper().strip()
        base = re.sub(r'^(ROSA)\s+(EC|COL)\s+', r'\1 ', name)
        for brand in brands:
            branded = f"{base} {brand}"
            if branded in self.by_name:
                return self.articulos[self.by_name[branded]]
            branded2 = f"{name} {brand}"
            if branded2 in self.by_name:
                return self.articulos[self.by_name[branded2]]
        return None

    def find_rose_ec(self, variety: str, size: int, spb: int) -> Optional[dict]:
        """Busca una rosa EC por variedad, talla y tallos por ramo."""
        key = f"{variety.upper()} {size}CM {spb}U"
        if key in self.rosas_ec:
            return self.articulos[self.rosas_ec[key]]
        for k, aid in self.rosas_ec.items():
            if k.startswith(variety.upper()) and f"{size}CM" in k and f"{spb}U" in k:
                return self.articulos[aid]
        return None

    def find_rose_col(self, variety: str, size: int, spb: int, grade: str = '') -> Optional[dict]:
        """Busca una rosa COL por variedad, talla, SPB y grado."""
        targets = [
            f"{grade.upper()} {variety.upper()} {size}CM {spb}U",
            f"{variety.upper()} {size}CM {spb}U",
        ]
        for t in targets:
            if t.strip() in self.rosas_col:
                return self.articulos[self.rosas_col[t.strip()]]
        return None

    def fuzzy_search(self, line: InvoiceLine, threshold: float = 0.4) -> list:
        """Búsqueda fuzzy por similitud dentro del pool de la especie."""
        sp_map = {
            'ROSES': 'ROSES_EC', 'ROSES_EC': 'ROSES_EC', 'ROSES_COL': 'ROSES_COL',
            'CARNATIONS': 'CARNATIONS', 'HYDRANGEAS': 'HYDRANGEAS',
            'ALSTROEMERIA': 'ALSTROEMERIA', 'GYPSOPHILA': 'GYPSOPHILA',
            'CHRYSANTHEMUM': 'CHRYSANTHEMUM',
        }
        if line.origin == 'COL' and line.species == 'ROSES':
            sp_key = 'ROSES_COL'
        else:
            sp_key = sp_map.get(line.species, 'ROSES_EC')
        pool = self.by_species.get(sp_key, [])
        if not pool:
            return []
        query = self._query_key(line)
        cands = []
        for rest, aid in pool:
            r = SequenceMatcher(None, query, rest).ratio()
            if r >= threshold:
                cands.append({
                    'id': aid, 'nombre': self.articulos[aid]['nombre'],
                    'similitud': round(r * 100, 1), 'key': rest,
                })
        return sorted(cands, key=lambda x: x['similitud'], reverse=True)[:5]

    # --- Indexación interna ---

    def _index_species(self, art: dict) -> None:
        nombre = art['nombre'].upper()
        for prefix, sp in SPECIES_PREFIXES.items():
            if nombre.startswith(prefix):
                rest = strip_provider_suffix(nombre[len(prefix):].strip())
                self.by_species[sp].append((rest, art['id']))
                if sp == 'ROSES_EC':
                    rm = re.match(r'(.+?)\s+(\d+)CM\s+(\d+)U', rest)
                    if rm:
                        key = f"{rm.group(1).strip()} {rm.group(2)}CM {rm.group(3)}U"
                        self.rosas_ec[key] = art['id']
                elif sp == 'ROSES_COL':
                    rm = re.match(r'(?:([A-Z0-9]+)\s+)?(.+?)\s+(\d+)CM\s+(\d+)U', rest)
                    if rm:
                        self.rosas_col[rest] = art['id']
                break
        else:
            clean = strip_provider_suffix(nombre)
            if re.match(r'ROSA\s+[A-Z]', clean):
                rest = clean[5:].strip()
                self.by_species['ROSES_EC'].append((rest, art['id']))
                self.by_species['ROSES_COL'].append((rest, art['id']))
                rm = re.match(r'(.+?)\s+(\d+)CM\s+(\d+)U', rest)
                if rm:
                    key = f"{rm.group(1).strip()} {rm.group(2)}CM {rm.group(3)}U"
                    self.rosas_ec[key] = art['id']
                    self.rosas_col[key] = art['id']

    def _build_brand_index(self) -> None:
        """Calcula el sufijo de marca más frecuente por proveedor."""
        prov_suffixes: Dict[int, list] = {}
        for a in self.articulos.values():
            pid = a.get('id_proveedor', 0)
            if not pid:
                continue
            parts = a['nombre'].upper().rsplit(None, 1)
            if (len(parts) == 2 and len(parts[1]) > 2
                    and parts[1].isalpha() and parts[1] not in BRAND_IGNORE_SUFFIXES):
                prov_suffixes.setdefault(pid, []).append(parts[1])
        for pid, suffixes in prov_suffixes.items():
            top = Counter(suffixes).most_common(1)[0]
            if top[1] >= BRAND_MIN_ARTICLES:
                self.brand_by_provider[pid] = top[0]

    def _query_key(self, line: InvoiceLine) -> str:
        v = line.variety.upper()
        s = line.size
        u = line.stems_per_bunch
        g = line.grade.upper()
        if line.species in ('ROSES', 'ROSES_EC', 'ROSES_COL'):
            return f"{v} {s}CM {u}U" if s and u else v
        if line.species == 'CARNATIONS':
            color = translate_carnation_color(v)
            sz = s if s else DEFAULT_SIZE_CARNATIONS
            if getattr(line, 'provider_key', '') == 'golden':
                return f"FANCY {color} {sz}CM {u}U"
            base = f"COL {g} {color} {sz}CM {u}U" if g else f"COL {color} {sz}CM {u}U"
            return base.replace('  ', ' ').strip()
        if line.species in ('HYDRANGEAS', 'ALSTROEMERIA', 'CHRYSANTHEMUM'):
            return f"{v} {s}CM {u}U" if s and u else v
        if line.species == 'GYPSOPHILA':
            return v
        return v

    @staticmethod
    def _parse_row(line: str) -> Optional[dict]:
        if not line.startswith('('):
            return None
        inner = line[1:].rstrip(')')
        flds = ArticulosLoader._split_sql(inner)
        if len(flds) < 10:
            return None

        def cs(v: str) -> str:
            v = v.strip()
            if v == 'NULL':
                return ''
            if v.startswith("'") and v.endswith("'"):
                return v[1:-1].replace("\\'", "'")
            return v

        def ci(v: str) -> int:
            v = v.strip()
            return int(v) if v.replace('-', '').isdigit() else 0

        return {
            'id': ci(flds[0]), 'nombre': cs(flds[8]), 'familia': cs(flds[9]),
            'tamano': cs(flds[5]), 'paquete': ci(flds[7]), 'id_proveedor': ci(flds[3]),
        }

    @staticmethod
    def _split_sql(s: str) -> list:
        """Divide una fila SQL respetando strings entre comillas simples."""
        parts = []
        cur = ''
        inq = False
        esc = False
        for ch in s:
            if esc:
                cur += ch
                esc = False
                continue
            if ch == '\\':
                cur += ch
                esc = True
                continue
            if ch == "'" and not inq:
                inq = True
                cur += ch
                continue
            if ch == "'" and inq:
                inq = False
                cur += ch
                continue
            if ch == ',' and not inq:
                parts.append(cur)
                cur = ''
                continue
            cur += ch
        if cur:
            parts.append(cur)
        return parts

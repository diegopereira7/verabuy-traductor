from __future__ import annotations

import re

from src.models import InvoiceHeader, InvoiceLine


class SayonaraParser:
    """
    C.I. Cultivos Sayonara SAS -- Crisantemos (id_proveedor=2166).

    Estructura de la factura:
    - Líneas PRODUCTO: tienen HB/QB + bunches + stems + precio (son facturables)
      Ej: "Pom Csh Europa White Bonita CO-... 5 HB 200 1,000 0.950 190.00"
      Ej: "Pom Csh Europa Custom Pack CO-... MERCO 2 HB 80 400 0.950 76.00"
    - Líneas DETALLE: "Exportacion {variedad}" — contenido de Custom Pack/Mix
      Solo tienen tallos + precio unitario, NO se facturan aparte
    - Línea TOTAL: "Pom Csh Europa 3,400 646.00" — resumen, ignorar
    """

    _TYPE_MAP = [
        ('Disbud Cremon', 'BI CREMON',   10),
        ('Disbud Spider', 'BI SPIDER',   10),
        ('Pom Csh',       'SP CUSHION',   5),
        ('Pom Btn',       'SP BUTTON',    5),
        ('Pom Dsy',       'SP DAISY',     5),
        ('Pom Nov',       'SP NOVELTY',   5),
        ('Pom CDN',       'SP CDN',       5),
        ('Santini',       'SA SANTINI',  25),
    ]

    _COLOR_MAP = [
        ('Bronze Dark', 'BRONCE OSCURO'), ('White', 'BLANCO'), ('Yellow', 'AMARILLO'),
        ('Red', 'ROJO'), ('Pink', 'ROSA'), ('Purple', 'LILA'), ('Green', 'VERDE'),
        ('Orange', 'NARANJA'), ('Bronze', 'BRONCE'), ('Cream', 'CREMA'),
        ('Salmon', 'SALMON'), ('Blue', 'AZUL'), ('Bicolor', 'BICOLOR'), ('Mix', 'MIXTO'),
    ]

    # Regex: línea facturable = tiene N HB/QB + stems + precio
    _PACK_RE = re.compile(r'(\d+)\s+(HB|QB)\s+(\d+)\s+([\d,]+)\s+([\d.]+)\s+([\d,.]+)')

    # Líneas de detalle (Exportacion) — ignorar como línea facturable
    _DETAIL_RE = re.compile(r'Exportacion\b', re.I)

    # Línea total (solo tipo + número grande) — ignorar
    _TOTAL_RE = re.compile(r'^Pom\s+\w+\s+Europa\s+[\d,]+\s+[\d,.]+\s*$', re.I)

    def _detect_type(self, line: str):
        """Detecta el tipo de producto en la línea. Retorna (prefix, tipo_vb, bunch) o None."""
        for prefix, tipo, bunch in self._TYPE_MAP:
            if prefix.lower() in line.lower():
                return prefix, tipo, bunch
        return None

    def _extract_variety(self, line: str, prefix: str) -> tuple[str, str]:
        """Extrae variedad y color de la parte después del prefijo de tipo.

        Returns:
            (variety_part, color_es) — ej: ('BONITA', 'BLANCO'), ('', 'MIXTO')
        """
        # Extraer texto entre el prefijo del tipo y CO-
        idx = line.lower().find(prefix.lower())
        if idx < 0:
            return '', 'MIXTO'

        rest = line[idx + len(prefix):].strip()
        # Quitar "Europa"
        rest = re.sub(r'\bEuropa\b', '', rest, flags=re.I).strip()

        # Custom Pack / Mix → MIXTO sin variedad específica
        if re.match(r'Custom\s+Pack|Mix\b', rest, re.I):
            return '', 'MIXTO'

        # Buscar color conocido
        color_es = 'MIXTO'
        variety = ''
        for en, es in self._COLOR_MAP:
            m = re.search(re.escape(en), rest, re.I)
            if m:
                color_es = es
                # Variedad es lo que viene después del color hasta CO- o dígitos
                after = rest[m.end():].strip()
                var_m = re.match(r'([A-Za-z][A-Za-z\s.\-/]*?)(?=\s+CO-|\s+\d|\s*$)', after)
                if var_m:
                    variety = var_m.group(1).strip().upper()
                break

        return variety, color_es

    def _extract_label(self, line: str) -> str:
        """Extrae el label/destino de un Custom Pack (ej: MERCO, PATIÑO, CORUÑA)."""
        # Después de CO-XXXXXXXXXX viene el label antes de N HB
        m = re.search(r'CO-\d+\s+([A-ZÀ-Ú][A-ZÀ-Ú\s]{2,}?)\s+\d+\s+(?:HB|QB)', line, re.I)
        if m:
            label = m.group(1).strip()
            # Filtrar falsos positivos
            if label and label not in ('CO', 'COLOMBIA'):
                return label
        return ''

    def parse(self, text: str, pdata: dict):
        h = InvoiceHeader()
        h.provider_key = pdata['key']
        h.provider_id = pdata['id']
        h.provider_name = pdata['name']

        m = re.search(r'No\.\s+(\d+)', text, re.I)
        h.invoice_number = m.group(1) if m else ''
        m = re.search(r'Invoice\s+Date\s+([\w\-/]+)', text, re.I)
        h.date = m.group(1) if m else ''
        m = re.search(r'Master\s+AWB\s+([\d\-]+)', text, re.I)
        h.awb = re.sub(r'\s+', '', m.group(1)) if m else ''
        m = re.search(r'House\s+AWB\s+([\w\-]+)', text, re.I)
        h.hawb = m.group(1) if m else ''
        try:
            m = re.search(r'(?:TOTAL|Total\s+USD)[:\s]*([\d,]+\.\d+)', text, re.I)
            h.total = float(m.group(1).replace(',', '')) if m else 0.0
        except Exception:
            h.total = 0.0

        lines = []
        for ln in text.split('\n'):
            ln = ln.strip()
            if not ln:
                continue

            # Ignorar líneas de detalle (Exportacion) — son sub-líneas de packs
            if self._DETAIL_RE.search(ln):
                continue

            # Ignorar línea total
            if self._TOTAL_RE.match(ln):
                continue

            # Detectar tipo de producto
            detected = self._detect_type(ln)
            if not detected:
                continue

            prefix, tipo, bunch = detected

            # Solo procesar líneas facturables (con HB/QB + stems + precio)
            pack_m = self._PACK_RE.search(ln)
            if not pack_m:
                continue

            boxes = int(pack_m.group(1))
            btype = pack_m.group(2).upper()
            spb = int(pack_m.group(3))
            stems = int(pack_m.group(4).replace(',', ''))
            price = float(pack_m.group(5))
            total = float(pack_m.group(6).replace(',', ''))

            variety, color_es = self._extract_variety(ln, prefix)
            label = self._extract_label(ln)

            var_stored = f"{tipo} {variety} {color_es}".replace('  ', ' ').strip()

            il = InvoiceLine(
                raw_description=ln,
                species='CHRYSANTHEMUM',
                variety=var_stored,
                grade='',
                origin='COL',
                size=70,
                stems_per_bunch=bunch,
                bunches=boxes,
                stems=stems,
                price_per_stem=price,
                line_total=total,
                label=label,
                box_type=btype,
                provider_key='sayonara',
            )
            lines.append(il)

        return h, lines

from __future__ import annotations

import re

from src.models import InvoiceHeader, InvoiceLine


class SayonaraParser:
    """
    C.I. Cultivos Sayonara SAS -- Crisantemos, Limonium, Alstroemeria (id_proveedor=2166).
    Las lineas de Custom Pack/caja son agrupadores y se ignoran.
    Articulos: "CRISANTEMO {TIPO} {VARIEDAD} {COLOR} 70CM {BUNCH}U SAYONARA"
    """
    # (prefijo_factura, tipo_verabuy, bunch)  -- ordenados mas largo primero
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
        ('Bronze Dark','BRONCE OSCURO'),('White','BLANCO'),('Yellow','AMARILLO'),
        ('Red','ROJO'),('Pink','ROSA'),('Purple','LILA'),('Green','VERDE'),
        ('Orange','NARANJA'),('Bronze','BRONCE'),('Cream','CREMA'),
        ('Salmon','SALMON'),('Blue','AZUL'),('Bicolor','BICOLOR'),('Mix','MIXTO'),
    ]
    # Marcadores de lineas de caja/pack que se deben ignorar
    _SKIP_RE = re.compile(r'Custom\s+Pack|^\s*Pack\s+|^\s*Box\s+|^\s*CAJA\b', re.I)

    def _parse_product(self, name:str):
        """Devuelve (tipo_vb, variedad, color_es, bunch) o None si no reconoce."""
        for prefix, tipo, bunch in self._TYPE_MAP:
            if name.lower().startswith(prefix.lower()):
                rest = name[len(prefix):].strip()
                rest = re.sub(r'\bEuropa\b', '', rest, flags=re.I).strip()
                color_es = 'MIXTO'; variety = ''
                for en, es in self._COLOR_MAP:
                    if rest.lower().startswith(en.lower()):
                        color_es = es
                        variety = rest[len(en):].strip().upper()
                        break
                return tipo, variety, color_es, bunch
        return None

    def _build_variety(self, tipo:str, variety:str, color:str) -> str:
        """Construye la cadena 'variety' que se almacena en InvoiceLine."""
        parts = [tipo]
        if variety: parts.append(variety)
        parts.append(color)
        return ' '.join(parts)

    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'No\.\s+(\d+)',text,re.I);            h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Invoice\s+Date\s+([\w\-/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'Master\s+AWB\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'HAWB[:\s]+([\w\-]+)',text,re.I);     h.hawb=m.group(1) if m else ''
        try:
            m=re.search(r'(?:TOTAL|Total\s+USD)[:\s]*([\d,]+\.\d+)',text,re.I)
            h.total=float(m.group(1).replace(',','')) if m else 0.0
        except: h.total=0.0
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            if not ln: continue
            if self._SKIP_RE.search(ln): continue   # ignorar lineas de caja/pack

            # Buscar tipo de producto EN CUALQUIER POSICION de la linea (puede haber N HB antes)
            parsed=None
            for prefix, _, _ in self._TYPE_MAP:
                type_m=re.search(re.escape(prefix), ln, re.I)
                if type_m:
                    # Extraer descripcion desde donde empieza el tipo hasta CO- o numeros
                    desc_start=ln[type_m.start():]
                    desc_m=re.match(r'([A-Za-z][A-Za-z\s.\-/]+?)(?=\s+CO-|\s+\d|\s+HB\b|\s+QB\b)',desc_start)
                    if desc_m:
                        parsed=self._parse_product(desc_m.group(1).strip())
                    break

            if not parsed: continue
            tipo, variety, color_es, bunch = parsed

            # Extraer stems y precio
            stems=0; price=0.0; btype=''
            bm=re.search(r'(\d+)\s+(HB|QB)\b',ln,re.I)
            if bm: btype=bm.group(2).upper()
            sm=re.search(r'\b(\d+)\s+ST\b',ln,re.I)
            if sm: stems=int(sm.group(1))
            if not stems:
                nm=re.search(r'(?:HB|QB)\s+\d+\s+(\d+)\s+([\d.]+)',ln,re.I)
                if nm:
                    try: stems=int(nm.group(1)); price=float(nm.group(2))
                    except: pass
            if not price:
                prices=re.findall(r'([\d,]+\.[\d]{2,3})',ln)
                if len(prices)>=2:
                    try: price=float(prices[-2].replace(',','.')); total_=float(prices[-1].replace(',','.'))
                    except: price=0.0
                elif len(prices)==1:
                    try: price=float(prices[-1].replace(',','.'))
                    except: pass
            if not price and stems: price=0.0
            total=round(price*stems,2) if stems else 0.0
            var_stored=self._build_variety(tipo,variety,color_es)
            il=InvoiceLine(raw_description=ln,species='CHRYSANTHEMUM',variety=var_stored,
                           grade='',origin='COL',size=70,stems_per_bunch=bunch,
                           stems=stems,price_per_stem=price,line_total=total,
                           box_type=btype,provider_key='sayonara')
            lines.append(il)
        return h, lines

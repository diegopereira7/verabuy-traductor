from __future__ import annotations

import re

from src.models import InvoiceHeader, InvoiceLine


class LatinParser:
    """
    Latin Flowers Farms SAS CI -- Hortensias (id_proveedor=6323).
    Articulos en BD: "HYDRANGEA {GRADO} {COLOR_ES} 60CM 1U LATIN"
    Siempre 1U en VeraBuy, independientemente del bunch en la factura.
    """
    _COLOR_MAP = {
        'DARK GREEN':'VERDE OSCURO','LIGHT PINK':'ROSA CLARO','DUSTY PINK':'ROSA VIEJO',
        'PINK BLUSH':'ROSA','LIGHT PEACH':'MELOCOTON','LIGHT MOCCA':'MOCCA',
        'LIGHT BLUE':'AZUL CLARO','BLUE BOGOTANA':'AZUL CRIOLLA','BLUE CRIOLLA':'AZUL CRIOLLA',
        'WHITE':'BLANCO','BLUE':'AZUL','RED':'ROJO','PINK':'ROSA','GREEN':'VERDE',
        'MIX':'MIXTO','PEACH':'MELOCOTON','SALMON':'SALMON','BURGUNDY':'GRANATE',
    }

    def _map_color(self, color_en:str) -> str:
        for en, es in sorted(self._COLOR_MAP.items(), key=lambda x:-len(x[0])):
            if color_en == en or color_en.startswith(en):
                return es
        return color_en

    def _translate_variety(self, desc:str) -> str:
        """Convierte descripcion raw en variedad VeraBuy (porcion tras 'HYDRANGEA ')."""
        d = desc.upper().strip()
        d = re.sub(r'^HYDRANGEA\s+', '', d)
        d = re.sub(r'\s*-\s*VERALEZA\b.*$', '', d)
        d = re.sub(r'\s+PREMIUM\s*$', '', d)
        if d.startswith('MIX'):
            return 'PREMIUM MIXTO'
        is_tinted = d.startswith('TINTED')
        if is_tinted: d = re.sub(r'^TINTED\s+', '', d)
        if d.startswith('EMERALD'):
            return 'EMERALD BICOLOR'
        if d.startswith('ANTIQUE'):
            d = re.sub(r'^ANTIQUE\s+', '', d).strip()
            return f"ANTIQUE {self._map_color(d)}"
        grado = 'PREMIUM TENIDA' if is_tinted else 'PREMIUM'
        return f"{grado} {self._map_color(d.strip())}"

    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'LF(\d+)',text,re.I);                      h.invoice_number='LF'+m.group(1) if m else ''
        m=re.search(r'Date\s+([\d\-]+)',text,re.I);             h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s+No\.?\s*([\d]+)',text,re.I);        h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'HAWB[:\s]+(ECM\d+)',text,re.I);           h.hawb=m.group(1) if m else ''
        try:
            m=re.search(r'Total\s+USD\s*([\d,]+\.\d+)',text,re.I); h.total=float(m.group(1).replace(',','')) if m else 0.0
        except: h.total=0.0
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(\d+)\s+(QB|HB)\s+(HYDRANGEA\s+[A-Z][A-Z\s.\-]+?)\s+\w+\s+\d{4}\w*\s+(\d+)\s+(\d+)\s+([\d.]+)',ln,re.I)
            if not pm: continue
            btype=pm.group(2).upper()
            desc=pm.group(3).strip().upper()
            stems=int(pm.group(5))
            try: pps=float(pm.group(6))
            except: pps=0.0
            total=round(pps*stems,2)
            before=ln[:pm.start()].strip()
            label=re.sub(r'\s*-?\s*S\.?O\.?\s*$','',before).strip() if before else ''
            variety=self._translate_variety(desc)
            il=InvoiceLine(raw_description=ln,species='HYDRANGEAS',variety=variety,origin='COL',
                           size=60,stems_per_bunch=1,stems=stems,price_per_stem=pps,
                           line_total=total,box_type=btype,label=label,provider_key='latin')
            lines.append(il)
        return h, lines

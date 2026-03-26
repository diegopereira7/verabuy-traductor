from __future__ import annotations

import re

from src.models import InvoiceHeader, InvoiceLine


class AlegriaParser:
    """Formato tabular: # BOX BOXTYPE VARIEDAD STxB columnas_talla"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE[:\s]*(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'DATE\s+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'M\.?A\.?W\.?B\.?\s*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'H\.?A\.?W\.?B\.?\s*(\S+)',text,re.I); h.hawb=m.group(1) if m else ''
        # Parse lines: find rows with QB/HB + variety + STxB
        lines=[]; seen={}
        for ln in text.split('\n'):
            ln=ln.strip()
            # Pattern: [N] QB/HB VARIETY SPB ... columns ... T.STEMS PRICE TOTAL
            pm=re.search(r'(\d+)\s+(QB|HB|QUA|HAL)\s+([A-Z][A-Z\s.\-/]+?)\s+(\d+)\s*X\s*\.00',ln)
            if not pm:
                pm=re.search(r'(QB|HB|QUA|HAL)\s+([A-Z][A-Z\s.\-/]+?)\s+(\d+)\s*X\s*\.00',ln)
                if pm:
                    btype=pm.group(1); var=pm.group(2).strip(); spb=int(pm.group(3))
                else: continue
            else:
                btype=pm.group(2); var=pm.group(3).strip(); spb=int(pm.group(4))
            if not var or re.match(r'^(TOT|SUB|TOTAL|DESCUENTO)',var.upper()): continue
            # Extract data after the "SPBx .00" marker
            # Format: ...25X .00 {bunches} {stems} {price} {total}...
            after = re.split(r'\d+\s*X\s*\.00\s+', ln, maxsplit=1)
            sz=0; stems=0; price=0.0; total=0.0
            if len(after) > 1:
                nm=re.search(r'(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)', after[1])
                if nm:
                    try: stems=int(nm.group(2)); price=float(nm.group(3)); total=float(nm.group(4))
                    except: pass
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                           size=sz,stems_per_bunch=spb,stems=stems,
                           price_per_stem=price,line_total=total,box_type=btype)
            lines.append(il)
        return h, lines

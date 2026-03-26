from __future__ import annotations

import re

from src.models import InvoiceHeader, InvoiceLine


class LifeParser:
    """PIECES TOTAL EQ.FULL MARKS VARIETY LENGTH STEM BUNCH TOTAL_STEMS PRICE TOTAL"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Date\s*(\d{4}/\d{2}/\d{2})',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'M\.?A\.?W\.?B[:\s]*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]; current_var=''; current_sz=0; current_spb=20
        for ln in text.split('\n'):
            ln=ln.strip()
            # Line with variety: mark, variety, CM, SPB, BUNCHES
            pm=re.search(r'\w+\s+([A-Z][a-zA-Z\s.\-/]{3,}?)\s+(\d{2})CM\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)',ln)
            if pm:
                var=pm.group(1).strip(); sz=int(pm.group(2)); spb=int(pm.group(3))
                bunches=int(pm.group(4)); stems=int(pm.group(5)); price=float(pm.group(6))
                current_var=var; current_sz=sz; current_spb=spb
                il=InvoiceLine(raw_description=ln,species='ROSES',variety=var.upper(),
                               size=sz,stems_per_bunch=spb,bunches=bunches,stems=stems,
                               price_per_stem=price,line_total=price*stems)
                lines.append(il)
            else:
                # Data-only row (variety carried from previous)
                pm2=re.search(r'HB\s+\S+\s+([A-Z][a-zA-Z\s.\-/]+?)\s+(\d{2})CM',ln)
                if pm2:
                    current_var=pm2.group(1).strip(); current_sz=int(pm2.group(2))
        return h, lines

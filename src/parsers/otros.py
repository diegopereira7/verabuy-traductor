from __future__ import annotations

import re

from src.models import InvoiceHeader, InvoiceLine


class BrissasParser:
    """Formato: ORDER MARK BX BOX VARIETIES CM STEMS TOTAL_STEMS UNIT TOTAL"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'Invoice\s+#[:\s]+(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Date[:\s]+([\d/\-]+)',text,re.I); h.date=m.group(1) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(?:HB|QB|TB)\s+(?:ROSE\s+)?([A-Z][A-Z\s.\-/]+?)\s+(\d{2})\s+(\d+)\s+([\d.]+)\s+([\d.]+)',ln)
            if not pm: continue
            var=pm.group(1).strip(); sz=int(pm.group(2))
            stems=int(pm.group(3))
            try: total=float(pm.group(5))
            except: total=0.0
            spb=25
            bt_m=re.search(r'(HB|QB|TB)',ln); btype=bt_m.group(1) if bt_m else ''
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                           size=sz,stems_per_bunch=spb,stems=stems,line_total=total,box_type=btype)
            lines.append(il)
        return h, lines


class AlunaParser:
    """Formato: FULLBOXES PIECES STEMS VARIETY GRADE ... PRICE TOTAL"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'DATE[:\s]+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([A-Z][A-Z\s.\-/]+?)\s+(\d{2})\s+\w+',ln)
            if not pm: continue
            var=pm.group(4).strip(); sz=int(pm.group(5))
            try: stems=int(pm.group(3).replace(',',''))
            except: stems=0
            nm=re.search(r'\$\s*([\d,.]+)\s+\$\s*([\d,.]+)',ln)
            price=0.0; total=0.0
            if nm:
                try: price=float(nm.group(1).replace(',','.')); total=float(nm.group(2).replace(',','.'))
                except: pass
            spb=25
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,origin='COL',
                           size=sz,stems_per_bunch=spb,stems=stems,
                           price_per_stem=price,line_total=total)
            lines.append(il)
        return h, lines


class DaflorParser:
    """Formato: Boxes DESCRIPTION Box_ID Tariff No.Box P.O. Un.Box T.Un Unit Price TOTAL"""
    SPECIES_MAP={'alstroemeria':'ALSTROEMERIA','carnation':'CARNATIONS','rose':'ROSES',
                 'chrysanth':'CHRYSANTHEMUM','hydrangea':'HYDRANGEAS','gypsophila':'GYPSOPHILA'}
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+Nro\.?\s*(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Data Invoice\s+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s*/\s*VL\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(\d+)\s+(QB|HB|QUA|HAL)\s+([A-Z][A-Z\s.\-/]+?)\s*[-\u2013]\s*([A-Za-z]+)',ln)
            if not pm:
                pm=re.search(r'(QB|HB)\s+([A-Z][A-Z\s.\-/]+?)\s*[-\u2013]\s*([A-Za-z]+)\s',ln)
                if not pm: continue
                qty_m=re.search(r'^(\d+)',ln.strip()); qty=int(qty_m.group(1)) if qty_m else 1
                btype=pm.group(1); desc=pm.group(2).strip(); grade=pm.group(3).strip()
            else:
                qty=int(pm.group(1)); btype=pm.group(2); desc=pm.group(3).strip(); grade=pm.group(4).strip()
            sp='ALSTROEMERIA'
            for k,v in self.SPECIES_MAP.items():
                if k in desc.lower(): sp=v; break
            nm=re.search(r'(\d+)\s+(\d+)\s+Stems\s+\$([\d.]+)\s+\$([\d.]+)',ln)
            upb=0; stems=0; price=0.0; total=0.0
            if nm:
                try: upb=int(nm.group(1)); stems=int(nm.group(2)); price=float(nm.group(3)); total=float(nm.group(4))
                except: pass
            il=InvoiceLine(raw_description=ln,species=sp,variety=desc,grade=grade,origin='COL',
                           stems_per_bunch=upb,stems=stems,price_per_stem=price,line_total=total,box_type=btype)
            lines.append(il)
        return h, lines


class EqrParser:
    """Formato: Description 'Roses Color Variety CM x Stems Stem'"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'Invoice\s+#\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Invoice\s+Date\s+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'Way\s+Bill[^:]*:\s*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        try:
            m=re.search(r'Amount\s+\$([\d,.]+)',text,re.I)
            h.total=float(m.group(1).replace(',','')) if m else 0.0
        except: h.total=0.0
        lines=[]
        for ln in text.split('\n'):
            pm=re.search(r'Roses?\s+(?:\w+\s+)?([A-Z][a-zA-Z\s.\-/]+?)\s+(\d{2})\s+Cm?\s+x\s+(\d+)\s+Stem',ln,re.I)
            if not pm: continue
            var=pm.group(1).strip(); sz=int(pm.group(2)); stems=int(pm.group(3))
            spb=25
            nm=re.search(r'\$\s*([\d.]+)',ln); price=float(nm.group(1)) if nm else 0.0
            total_m=re.search(r'\$\s*[\d.]+\s*$',ln)
            try: total=float(total_m.group(0).strip().lstrip('$')) if total_m else 0.0
            except: total=0.0
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var.upper(),
                           size=sz,stems_per_bunch=spb,stems=stems,
                           price_per_stem=price,line_total=total)
            lines.append(il)
        return h, lines


class BosqueParser:
    """Formato: #BOX PRODUCT-VARIETY TARIFF LENGTH BUNCHS STEMS T.STEMS PRICE AMOUNT"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'No\.:\s*(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'(?:MAWB|MAWB No)\s*[:\s]*([\d]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(?:\d+\s+)?(HB|QB|TB)\s+ROSAS?\s+([A-Z][A-Z\s.\-/]+?)\s+(\d{2})',ln)
            if not pm: continue
            btype=pm.group(1); var=pm.group(2).strip(); sz=int(pm.group(3))
            nm=re.search(r'(\d+)\s+(\d+)\s+\$\s*([\d.]+)\s+\$([\d.]+)',ln)
            bun=0; stems=0; price=0.0; total=0.0
            if nm:
                try: bun=int(nm.group(1)); stems=int(nm.group(2)); price=float(nm.group(3)); total=float(nm.group(4))
                except: pass
            spb=25
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                           size=sz,stems_per_bunch=spb,bunches=bun,stems=stems,
                           price_per_stem=price,line_total=total,box_type=btype)
            lines.append(il)
        return h, lines


class MultifloraParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+#[:\s]*(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'SHIPPING\s+DATE[:\s]+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB[:\s]*([\d\-/]+)',text,re.I); h.awb=re.sub(r'[/\s]','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(PF-\w+)\s+ALSTRO\s+(.+?)\s+(?:ALSTR)?\s+(\d+)\s+Box\s+\w+\s+\d+\s+(\d+)\s+([\d.]+)',ln)
            if not pm: continue
            code=pm.group(1); desc=pm.group(2).strip()
            try: upb=int(pm.group(4)); price_per_bunch=float(pm.group(5))
            except: upb=0; price_per_bunch=0.0
            grade='FANCY' if 'FANCY' in desc.upper() or 'FCY' in desc.upper() else 'SELECT' if 'SPE' in desc.upper() else 'PREMIUM'
            var_clean=re.sub(r'PERFECTION\s*','',desc,flags=re.I).strip()
            il=InvoiceLine(raw_description=ln,species='ALSTROEMERIA',variety=var_clean.upper(),
                           grade=grade,origin='COL',stems_per_bunch=upb,
                           price_per_bunch=price_per_bunch,line_total=0.0)
            lines.append(il)
        return h, lines


class FlorsaniParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'N[o\xba]\s*(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'DATE[:\s]+([\d/\-]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB#[:\s]*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(\d+)\s+(?:HE?|QB?)\s+(?:\w+\s+)?Gypsophila\s+(\w+)',ln,re.I)
            if not pm: continue
            qty=int(pm.group(1)); variety=f"Gypsophila {pm.group(2)}".upper()
            nm=re.search(r'(\d{2})\s+(\d+)\s+(\d+)\s+([\d.]+)',ln)
            sz=int(nm.group(1)) if nm else 80; spb=int(nm.group(2)) if nm else 0
            stems=int(nm.group(3)) if nm else 0; price=float(nm.group(4)) if nm else 0.0
            total=price*(stems if stems else qty)
            il=InvoiceLine(raw_description=ln,species='GYPSOPHILA',variety=variety,
                           size=sz,stems_per_bunch=spb,stems=stems,
                           price_per_stem=price,line_total=total)
            lines.append(il)
        return h, lines


class MaxiParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'No\.\s*(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'DATE.*?(\d{2}/\d{2}/\d{4})',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB[:\s]*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        try:
            m=re.search(r'PAY THIS AMOUNT US \$\s*([\d,.]+)',text,re.I)
            h.total=float(m.group(1).replace(',','')) if m else 0.0
        except: h.total=0.0
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'ROSE\s+([A-Z][A-Z\s.\-/]+?)\s+(\d{2})\s*Cm\s+(?:\d+\s+)?(\d+)\s+([\d,.]+)\s+(\d+)\s+([\d,.]+)',ln,re.I)
            if not pm: continue
            var=pm.group(1).strip(); sz=int(pm.group(2))
            try: stems=int(pm.group(5)); total=float(pm.group(6).replace(',',''))
            except: stems=0; total=0.0
            spb=25
            price=total/stems if stems else 0.0
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,origin='COL',
                           size=sz,stems_per_bunch=spb,stems=stems,
                           price_per_stem=price,line_total=total)
            lines.append(il)
        return h, lines


class PrestigeParser:
    """DESCRIPTION CODE HB/QB UNIT QTY UNIT_VALUE TOTAL"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+No\.?\s*(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'FECHA EXPEDICION\s*([\d\-]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'GU[I\xcdI]A\s+MASTER\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'([A-Z][A-Z\s.\-/]+?)\s+ROSE\s+(\d{2})\s+CM\s+\w+\s+(\d+)\s+(\d+)\s+\$\s*([\d,]+)\s+([\d,.]+)',ln,re.I)
            if not pm:
                pm=re.search(r'([A-Z][A-Z\s.\-/]+?)\s+(\d{2})\s+CM\s+\w+\s+(\d+)\s+(\d+)\s+\$\s*([\d,.]+)\s+([\d,.]+)',ln,re.I)
                if not pm: continue
            var=pm.group(1).strip(); sz=int(pm.group(2))
            try: spb=int(pm.group(3)); stems=int(pm.group(4)); total=float(pm.group(6).replace(',',''))
            except: continue
            price=total/stems if stems else 0.0
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,origin='COL',
                           size=sz,stems_per_bunch=spb,stems=stems,
                           price_per_stem=price,line_total=total)
            lines.append(il)
        return h, lines


class RoselyParser:
    """BOXES VARIETY *SPB LENGTH BUNCHS STEMS PRICE AMOUNT"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+TO',text,re.I); h.invoice_number='ROSELY'  # no number visible
        m2=re.search(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[^\d]*([\d]+)[^\d]*([\w]+)[^\d]*([\d]+)',text,re.I)
        h.date='' if not m2 else f"{m2.group(2)}/{m2.group(3)}/{m2.group(4)}"
        m=re.search(r'MAWB[:\s]*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(\d+)\s+(TB|HB|QB)\s+([A-Z][A-Z\s.\-/]+?)\s+\*(\d+)\s+(\d{2})\s+\d+\s+(\d+)\s+\$\s*([\d.]+)\s+\$([\d.]+)',ln)
            if not pm: continue
            btype=pm.group(2); var=pm.group(3).strip(); spb=int(pm.group(4))
            sz=int(pm.group(5)); stems=int(pm.group(6))
            try: price=float(pm.group(7)); total=float(pm.group(8))
            except: price=0.0; total=0.0
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                           size=sz,stems_per_bunch=spb,stems=stems,
                           price_per_stem=price,line_total=total,box_type=btype)
            lines.append(il)
        return h, lines


class CondorParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'PROFORMA\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'(\d{2}[A-Z]{3}\d{4})',text); h.date=m.group(1) if m else ''
        m=re.search(r'MAWB\s+No\.?\s*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'([\d.]+)\s+(QB|HB)\s+(HYD\s+[A-Z][A-Z\s.\-/]+?)\s*(?:\[[\d]+\])?\s+\d+\s+\d{4}\w*\s+(\d+)\s+([\d.]+)',ln,re.I)
            if not pm: continue
            btype=pm.group(2); desc=pm.group(3).strip().upper()
            # HYD WHITE -> HYDRANGEA WHITE
            var=re.sub(r'^HYD\s+','HYDRANGEA ',desc)
            try: stems=int(pm.group(4)); price=float(pm.group(5))
            except: stems=0; price=0.0
            total=price*stems
            il=InvoiceLine(raw_description=ln,species='HYDRANGEAS',variety=var,origin='COL',
                           stems_per_bunch=35,stems=stems,price_per_stem=price,line_total=total,box_type=btype)
            lines.append(il)
        return h, lines


class MalimaParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'Invoice Numbers?\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Ship Date\s+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'(?:MAWB|AWB)[:\s]*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        try:
            m=re.search(r'Amount Due\s+\$([\d,.]+)',text,re.I)
            h.total=float(m.group(1).replace(',','')) if m else 0.0
        except: h.total=0.0
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'\d+\s+(HB|QB)\s+MALIMA\s+EUROPA\s+[\d.]+\s+(XLENCE[^$]+?)\s+(GYPSOPHILA)\s+(\d+)\s+\$([\d.]+)\s+(\d+)\s+\$([\d.]+)\s+\$([\d.]+)',ln,re.I)
            if not pm: continue
            btype=pm.group(1); variety=pm.group(2).strip().upper()
            try:
                bunches=int(pm.group(4)); ppb=float(pm.group(5))
                stems=int(pm.group(6)); total=float(pm.group(8))
            except: bunches=0; ppb=0.0; stems=0; total=0.0
            spb=stems//bunches if bunches else 25
            il=InvoiceLine(raw_description=ln,species='GYPSOPHILA',variety=variety,
                           stems_per_bunch=spb,bunches=bunches,stems=stems,
                           price_per_bunch=ppb,line_total=total,box_type=btype)
            lines.append(il)
        return h, lines


class MonterosaParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'DATE[:\s]+([\d\-/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'M\s*A\s*W\s*B[:\s]*([\d\-/]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            # Formato: QB {pieces} {order} {mark} {variety} {stem_size} {T_bunch} {T_bunches} {stems} {price} {total}
            pm=re.search(r'(?:QB|HB)\s+(?:\w+\s+){0,3}([A-Z][A-Z\s.\-/]+?)\s+(\d{2})\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)',ln)
            if not pm: continue
            var=pm.group(1).strip(); sz=int(pm.group(2))
            try: bunches=int(pm.group(4)); stems=int(pm.group(5)); total=float(pm.group(7))
            except: continue
            spb=stems//bunches if bunches else 25; price=total/stems if stems else 0.0
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                           size=sz,stems_per_bunch=spb,bunches=bunches,stems=stems,
                           price_per_stem=price,line_total=total)
            lines.append(il)
        return h, lines


class SecoreParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'Invoice\s+N[o\xba]\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'(\d+[-]\w+[-]\d+)',text); h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s+([\d\s]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1))[:12] if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'ROSE\s+([A-Z][A-Z\s.\-/]+?)\s+(\d{2})\s+CM',ln,re.I)
            if not pm: continue
            var=pm.group(1).strip(); sz=int(pm.group(2))
            nm=re.search(r'(\d+)\s+(HALF|QUARTER|FULL)\s+(\d+)\s+([\d.]+)\s+([\d.]+)',ln,re.I)
            if not nm: continue
            try: upb=int(nm.group(1)); stems=int(nm.group(3)); price=float(nm.group(4)); total=float(nm.group(5))
            except: continue
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                           size=sz,stems_per_bunch=upb,stems=stems,
                           price_per_stem=price,line_total=total)
            lines.append(il)
        return h, lines


class TessaParser:
    """Boxes Order BoxT Loc. Description Len Bun/Box Stems Price Total Label"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'Invoice\s+Number\s*(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Invoice\s+Date\s+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        try:
            m=re.search(r'Total Invoice USD\s+\$([\d,.]+)',text,re.I)
            h.total=float(m.group(1).replace(',','')) if m else 0.0
        except: h.total=0.0
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(HB|QB)\s+\w+\s+([A-Z][A-Z\s.\-/]+?)\s+(\d{2})\s+(\d+)\s+(\d+)\s+\$([\d.]+)\s+\$([\d.]+)',ln)
            if not pm: continue
            btype=pm.group(1); var=pm.group(2).strip()
            try: sz=int(pm.group(3)); spb=int(pm.group(4)); stems=int(pm.group(5)); price=float(pm.group(6)); total=float(pm.group(7))
            except: continue
            label_m=re.search(r'\$[\d.]+\s+(\w+)\s*$',ln); label=label_m.group(1) if label_m else ''
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                           size=sz,stems_per_bunch=spb,stems=stems,
                           price_per_stem=price,line_total=total,label=label,box_type=btype)
            lines.append(il)
        return h, lines


class UmaParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Invoice\s+Date\s+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        try:
            m=re.search(r'Amount\s+Due\s+\$\s*([\d,.]+)',text,re.I)
            h.total=float(m.group(1).replace(',','')) if m else 0.0
        except: h.total=0.0
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(hb|qb)\s+\d+\s+(Gyp\w+\s+\w+\s+\w+(?:\s+\w+)?)\s+(\d+)\s+(\d+)\s+\$\s*([\d.]+)\s+\$\s*([\d.]+)',ln,re.I)
            if not pm: continue
            btype=pm.group(1).upper(); var=pm.group(2).strip().upper()
            try: stems=int(pm.group(3)); spb=int(pm.group(4)); price=float(pm.group(5)); total=float(pm.group(6))
            except: continue
            il=InvoiceLine(raw_description=ln,species='GYPSOPHILA',variety=var,
                           stems_per_bunch=spb,stems=stems,
                           price_per_stem=price,line_total=total,box_type=btype)
            lines.append(il)
        return h, lines


class ValleVerdeParser:
    """Boxs Order BoxT Id. Description Len. Bun/BoxT. Bunch Stems Price Total"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Date[:\s]+([\d\-]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'M\.\s*A\.W\.B\.[:\s]*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]; label=''
        for ln in text.split('\n'):
            ln=ln.strip()
            lbl_m=re.search(r'\b(R\d{2}[\w\-]*)\b',ln)
            if lbl_m: label=lbl_m.group(1)
            pm=re.search(r'(?:HB|QB|HB)\s+(?:\w+\s+)?([A-Z][A-Z\s.\-/]+?)\s+(\d{2})\s+\d+\s+(\d+)\s+(\d+)\s+([\d,]+)\s+([\d,]+)',ln)
            if not pm: continue
            var=pm.group(1).strip(); sz=int(pm.group(2))
            try: bunches=int(pm.group(3)); stems=int(pm.group(4)); price=float(pm.group(5).replace(',','.')); total=float(pm.group(6).replace(',','.'))
            except: continue
            spb=stems//bunches if bunches else 25
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                           size=sz,stems_per_bunch=spb,bunches=bunches,stems=stems,
                           price_per_stem=price,line_total=total,label=label)
            lines.append(il)
        return h, lines

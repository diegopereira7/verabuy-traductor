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
    """Formato: Boxes DESCRIPTION Box_ID Tariff No.Box P.O. Un.Box T.Un Unit Price TOTAL
    FIX: el PDF usa mixed-case (Alstroemeria, Roses), no solo MAYÚSCULAS.
    FIX: tamaño (50) aparece tras el guión de grado para rosas.
    """
    SPECIES_MAP={'alstroemeria':'ALSTROEMERIA','carnation':'CARNATIONS','rose':'ROSES',
                 'chrysanth':'CHRYSANTHEMUM','hydrangea':'HYDRANGEAS','gypsophila':'GYPSOPHILA'}
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+Nro\.?\s*(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Data Invoice\s+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s*/\s*VL\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'HAWB\s*/\s*VHL\s+([\w\-]+)',text,re.I); h.hawb=m.group(1).strip() if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            # FIX: usar re.I para mixed-case: "1 QB Alstroemeria Assorted - Fancy"
            pm=re.search(r'(\d+)\s+(QB|HB)\s+([A-Za-z][A-Za-z\s.\-/\u00b4\u2019\']+?)\s*[-\u2013]\s*([A-Za-z]+)',ln,re.I)
            if not pm:
                pm=re.search(r'(QB|HB)\s+([A-Za-z][A-Za-z\s.\-/\u00b4\u2019\']+?)\s*[-\u2013]\s*([A-Za-z]+)',ln,re.I)
                if not pm: continue
                btype=pm.group(1).upper(); desc=pm.group(2).strip(); grade=pm.group(3).strip()
            else:
                btype=pm.group(2).upper(); desc=pm.group(3).strip(); grade=pm.group(4).strip()
            # Detectar especie
            sp='ALSTROEMERIA'
            for k,v in self.SPECIES_MAP.items():
                if k in desc.lower(): sp=v; break
            # Extraer tamaño para rosas: "Roses Pink O'hara - 50"
            sz=0
            sz_m=re.search(r'[-\u2013]\s*(\d{2})\s', ln)
            if sz_m and sp == 'ROSES':
                sz = int(sz_m.group(1))
            # FIX: buscar "200 200 Stems $0.150 $30.00" con case-insensitive
            nm=re.search(r'(\d+)\s+(\d+)\s+Stems\s+\$([\d.]+)\s+\$([\d.]+)',ln,re.I)
            upb=0; stems=0; price=0.0; total=0.0
            if nm:
                try: upb=int(nm.group(1)); stems=int(nm.group(2)); price=float(nm.group(3)); total=float(nm.group(4))
                except: pass
            # Limpiar nombre de variedad: quitar prefijo de especie
            var_clean = re.sub(r'^(?:Alstroemeria|Roses?)\s+', '', desc, flags=re.I).strip()
            il=InvoiceLine(raw_description=ln,species=sp,variety=var_clean.upper(),grade=grade.upper(),origin='COL',
                           size=sz,stems_per_bunch=upb,stems=stems,price_per_stem=price,line_total=total,box_type=btype)
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
    """FIX: código con espacios (PF -A LS001), múltiples especies (ALSTRO, CHRY, DIANTHUS).
    FIX: formatos Box perfection, Quarter tall, Half tall.
    """
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+#[:\s]*(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'SHIPPING\s+DATE[:\s]+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB[:\s]*([\d\-/]+)',text,re.I); h.awb=re.sub(r'[/\s]','',m.group(1))[:14] if m else ''
        m=re.search(r'TOTAL\s+DUE\s+USD\s+([\d,.]+)',text,re.I)
        h.total=float(m.group(1).replace(',','')) if m else 0.0
        lines=[]; text_lines=text.split('\n')
        for i, ln in enumerate(text_lines):
            ln=ln.strip()
            # Patrón genérico: buscar "N Box/Quarter/Half TYPE N N PRICE TOTAL"
            # "PF -A LS001 ALSTRO PERFECTION AST ASSORTED ALSTR 1 Box perfection 16 16 3.3000 52.8000 0.25"
            # "SC -A LSWHI ALSTRO Select WHI WHITE 10ST(Bunches) 0603190107 2 Quarter tall 18 36 1.8000 64.8000 0.50"
            # "EX -B COGAI CHRY EX SPE Box Chry Special Pack 10(Stems) 1 Half tall 200 200 0.2800 56.0000 0.50"
            # "70 -D IAGBT DIANTHUS 70cm GRE Green Ball 10st 10 St(Stems) DIANT 1 Half tall 200 200 0.4400 88.0000 0.50"
            pm=re.search(r'(\d+)\s+(?:Box|Quarter|Half)\s+\w+\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',ln)
            if not pm: continue
            qty=int(pm.group(1)); upb=int(pm.group(2)); total_units=int(pm.group(3))
            ppb=float(pm.group(4)); total=float(pm.group(5))
            # Detectar especie y variedad del texto de la línea
            sp='ALSTROEMERIA'; var='ASSORTED'; grade='FANCY'; sz=0
            if 'ALSTRO' in ln.upper():
                sp='ALSTROEMERIA'
                if 'WHISTLER' in ln.upper(): var='WHISTLER'
                elif 'WHITE' in ln.upper(): var='WHITE'
                elif 'SPECIAL' in ln.upper() or 'SPE' in ln.upper(): var='SPECIAL PACK'
                else: var='ASSORTED'
                if 'SELECT' in ln.upper() or 'SPE ' in ln.upper(): grade='SELECT'
                elif 'AST' in ln.upper(): grade='FANCY'
                else: grade='FANCY'
            elif 'CHRY' in ln.upper():
                sp='CHRYSANTHEMUM'
                var='SPECIAL PACK' if 'SPECIAL' in ln.upper() else 'ASSORTED'
                grade=''
            elif 'DIANTHUS' in ln.upper():
                sp='OTHER'
                dm=re.search(r'DIANTHUS\s+\d+cm\s+\w+\s+([\w\s]+?)(?:\d|St)',ln,re.I)
                var=dm.group(1).strip().upper() if dm else 'GREEN BALL'
                sz_m=re.search(r'(\d{2})cm',ln,re.I)
                sz=int(sz_m.group(1)) if sz_m else 0
                grade=''
            # Label: buscar en la línea siguiente (ej: "NAVARRA", "R11")
            label=''
            if i+1 < len(text_lines):
                next_ln=text_lines[i+1].strip()
                # Labels suelen estar solos o después de "10ST(Bunches)"
                lm=re.search(r'(?:Bunches\)|Stems\))\s+(\w+)',next_ln) or re.search(r'^([A-Z][A-Z0-9]+)$',next_ln)
                if lm: label=lm.group(1)
            il=InvoiceLine(raw_description=ln,species=sp,variety=var,grade=grade,origin='COL',
                           size=sz,stems_per_bunch=upb,bunches=total_units,stems=total_units*10 if sp=='ALSTROEMERIA' else total_units,
                           price_per_bunch=ppb,line_total=total,label=label)
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
    """DESCRIPTION CODE HB/QB_UNIT HB/QB_QTY STEMS $ UNIT_VALUE TOTAL
    FIX: 3 columnas numéricas (UNIT, QTY, STEMS) en vez de 2.
    FIX: decimales con coma (0,33 no 0.33).
    """
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+No\.?\s*(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'FECHA EXPEDICION\s*([\d\-]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'GU[I\xcdÌ]A\s+MASTER\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'GU[I\xcdÌ]A\s+HIJA\s+([\d\w\s\-\(\)]+)',text,re.I)
        h.hawb=re.sub(r'\s+','',m.group(1)).strip() if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            # "MOMENTUM ROSE 50 CM ROSA0682 1 250 250 $ 0,33 82,50"
            # groups: variety, size, code, unit, qty, stems, price, total
            pm=re.search(r'([A-Z][A-Z\s.\-/]+?)\s+ROSE\s+(\d{2})\s+CM\s+\w+\s+(\d+)\s+(\d+)\s+(\d+)\s+\$\s*([\d,]+)\s+([\d,.]+)',ln,re.I)
            if not pm:
                # Sin "ROSE": "ASSORTED 50 CM ROSA0091 1 250 250 ..."
                pm=re.search(r'([A-Z][A-Z\s.\-/]+?)\s+(\d{2})\s+CM\s+\w+\s+(\d+)\s+(\d+)\s+(\d+)\s+\$\s*([\d,]+)\s+([\d,.]+)',ln,re.I)
                if not pm: continue
            var=pm.group(1).strip(); sz=int(pm.group(2))
            try:
                stems=int(pm.group(5))
                price_str=pm.group(6).replace(',','.')
                total_str=pm.group(7).replace(',','.')
                # total puede ser "82,50" o "484,50"
                price=float(price_str)
                total=float(total_str)
            except: continue
            spb=25
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
    """FIX: decimales con coma (0,48 no 0.48), tarifa de 12 dígitos, stems de 3 dígitos."""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'PROFORMA\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'(\d{2}[A-Z]{3}\d{4})',text); h.date=m.group(1) if m else ''
        m=re.search(r'MAWB\s+No\.?\s*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'HAWB\s+No\.?\s*([\w\-]+)',text,re.I); h.hawb=m.group(1).strip() if m else ''
        m=re.search(r'TOTAL\s+USD\s+([\d.,]+)',text,re.I)
        h.total=float(m.group(1).replace(',','.')) if m else 0.0
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            # FIX: "15,00 QB HYD WHITE PREMIUM[00001] 350603199010 525 0,48 252,00"
            # - qty usa coma decimal (15,00)
            # - tarifa es 12 dígitos (no 4)
            # - stems puede ser 3 dígitos
            # - precio y total usan coma decimal
            pm=re.search(r'[\d,]+\s+(QB|HB)\s+(HYD\s+[A-Za-z][A-Za-z\s.\-/]+?)\s*(?:\[[\d]+\])?\s+\d{6,}\s+(\d+)\s+([\d,]+)\s+([\d,]+)',ln,re.I)
            if not pm: continue
            btype=pm.group(1).upper(); desc=pm.group(2).strip().upper()
            var=re.sub(r'^HYD\s+','',desc).strip()
            try:
                stems=int(pm.group(3))
                price=float(pm.group(4).replace(',','.'))
                total=float(pm.group(5).replace(',','.'))
            except: stems=0; price=0.0; total=0.0
            il=InvoiceLine(raw_description=ln,species='HYDRANGEAS',variety=var,origin='COL',
                           stems_per_bunch=1,bunches=stems,stems=stems,
                           price_per_stem=price,line_total=total,box_type=btype)
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
    """Boxes Order BoxT Loc. Description Len Bun/Box Stems Price Total Label
    FIX: Loc puede ser "XL 2" o solo un número, y Description puede estar
    en la misma línea o en la siguiente (PINK\\nMONDIAL).
    """
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'Invoice\s+Number\s*(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Invoice\s+Date\s+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s+([\d\-\s]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1))[:14] if m else ''
        m=re.search(r'HAWB\s+([\w\-]+)',text,re.I); h.hawb=m.group(1).strip() if m else ''
        try:
            m=re.search(r'(?:Invoice Amount|TOTALS.*?)\$([\d,.]+)',text,re.I)
            h.total=float(m.group(1).replace(',','')) if m else 0.0
        except: h.total=0.0
        lines=[]; text_lines=text.split('\n')
        for i, ln in enumerate(text_lines):
            ln=ln.strip()
            # Patrón: ...HB/QB [loc] [num] VARIETY SIZE BUNCHES STEMS $PRICE $TOTAL LABEL
            # Ejemplo: "1 910573351 HB XL 2 MONDIAL 60 12 300 $0.45 $135.00 R17"
            pm=re.search(r'(HB|QB)\s+(?:\w+\s+)?(?:\d+\s+)?([A-Z][A-Z\s.\-/]+?)\s+(\d{2})\s+(\d+)\s+(\d+)\s+\$([\d.]+)\s+\$([\d.]+)',ln)
            if pm:
                btype=pm.group(1); var=pm.group(2).strip()
                try: sz=int(pm.group(3)); spb=int(pm.group(4)); stems=int(pm.group(5)); price=float(pm.group(6)); total=float(pm.group(7))
                except: continue
                label_m=re.search(r'\$[\d.]+\s+(\w+)\s*$',ln); label=label_m.group(1) if label_m else ''
                il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                               size=sz,stems_per_bunch=spb,stems=stems,
                               price_per_stem=price,line_total=total,label=label,box_type=btype)
                lines.append(il)
                continue
            # FIX: línea sin variedad visible (variedad en la línea siguiente)
            # "1 910927987 QB 3 60 4 100 $0.45 $45.00 R18"
            # siguiente línea: "R2 PINK"  o "MONDIAL"
            pm2=re.search(r'(HB|QB)\s+(\d+)\s+(\d{2})\s+(\d+)\s+(\d+)\s+\$([\d.]+)\s+\$([\d.]+)',ln)
            if pm2:
                btype=pm2.group(1)
                try: sz=int(pm2.group(3)); spb=int(pm2.group(4)); stems=int(pm2.group(5)); price=float(pm2.group(6)); total=float(pm2.group(7))
                except: continue
                label_m=re.search(r'\$[\d.]+\s+(\w+)\s*$',ln); label=label_m.group(1) if label_m else ''
                # Buscar variedad en líneas siguientes
                var_parts=[]
                for j in range(i+1, min(i+3, len(text_lines))):
                    next_ln=text_lines[j].strip()
                    if not next_ln: continue
                    # Buscar palabras que son nombre de variedad (mayúsculas, no números)
                    vm=re.findall(r'[A-Z][A-Z]+', next_ln)
                    if vm:
                        for w in vm:
                            if w not in ('TESSA','TOTALS','AWB','HAWB','USD','FUE'):
                                var_parts.append(w)
                        break
                var=' '.join(var_parts) if var_parts else 'DESCONOCIDA'
                il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                               size=sz,stems_per_bunch=spb,stems=stems,
                               price_per_stem=price,line_total=total,label=label,box_type=btype)
                lines.append(il)
        return h, lines


class UmaParser:
    """FIX: descripciones largas con cm/gr y farm.
    FIX: comas decimales y espacios en totales ($ 1 40,00 = $140.00).
    Formato: COD QTY BOX X PRODUCT FARM TOTAL_STEMS ST.BUNCH BUNCHES PRICE TOTAL
    """
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Invoice\s+Date\s+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        try:
            m=re.search(r'Amount\s+Due\s+\$\s*([\d\s,.]+)',text,re.I)
            h.total=float(re.sub(r'[\s,]','',m.group(1)).replace(',','.')) if m else 0.0
        except: h.total=0.0
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            # "96885 1 hb 560 Gypso Xlence Natural 80 cm / 550 gr Violeta Flowers 560 20 28 $ 5,00 $ 1 40,00"
            # Estrategia: buscar "hb/qb" + capturar todo hasta los números finales
            pm=re.search(r'(hb|qb)\s+\d+\s+((?:Gyp|Gyps)\w+[^$]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+\$\s*([\d\s,]+?)\s+\$\s*([\d\s,]+?)$',ln,re.I)
            if not pm: continue
            btype=pm.group(1).upper()
            desc_raw=pm.group(2).strip()
            # Extraer variedad limpia: "Gypso Xlence Natural 80 cm / 550 gr Violeta Flowers" -> "XLENCE NATURAL"
            var_m=re.search(r'(?:Gyp(?:so)?|Gypsophila)\s+(?:Xl?\s+)?(.+?)(?:\d+\s*cm|\d+\s*gr|/|Violeta|Flowers)',desc_raw,re.I)
            var=var_m.group(1).strip().upper() if var_m else desc_raw.upper()
            # Extraer tamaño
            sz_m=re.search(r'(\d{2})\s*cm',desc_raw,re.I)
            sz=int(sz_m.group(1)) if sz_m else 0
            # Extraer farm
            farm_m=re.search(r'(?:Violeta|Fiorella|Margarita)\s+Flowers',desc_raw,re.I)
            farm=farm_m.group(0).strip() if farm_m else ''
            try:
                stems=int(pm.group(3)); spb=int(pm.group(4)); bunches=int(pm.group(5))
                price=float(re.sub(r'\s','',pm.group(6)).replace(',','.'))
                total=float(re.sub(r'\s','',pm.group(7)).replace(',','.'))
            except: continue
            # "Gypso Xlence Natural" -> "GYPSOPHILA XLENCE NATURAL"
            full_var='GYPSOPHILA ' + var if 'GYPSOPHILA' not in var else var
            il=InvoiceLine(raw_description=ln,species='GYPSOPHILA',variety=full_var,
                           size=sz,stems_per_bunch=spb,bunches=bunches,stems=stems,
                           price_per_bunch=price,line_total=total,box_type=btype,farm=farm)
            lines.append(il)
        return h, lines


class VerdesEstacionParser:
    """Formato Verdes La Estacion: #/TOTAL HB/QB FRAC FRAC VARIETY SIZECM STEMS STEMS LABEL CO TARIFF $ PRICE $ TOTAL
    Líneas de continuación (caja mixta) no tienen el prefijo #/TOTAL.
    Ejemplo: "1/39 HB 0,50 1,00 FREEDOM 50CM 240 240 MARL CO 0603110000 $ 0,30 $ 72,00"
    """
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+([\d.]+)',text,re.I); h.invoice_number=m.group(1).replace('.','') if m else ''
        m=re.search(r'(\d{1,2}/\d{2}/\d{4})',text); h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'HWB\s+([\w\-]+)',text,re.I); h.hawb=m.group(1).strip() if m else ''
        lines=[]; label=''; btype='HB'
        for ln in text.split('\n'):
            ln=ln.strip()
            # Detectar línea principal: "1/39 HB 0,50 1,00 FREEDOM 50CM 240 240 MARL CO ..."
            pm=re.search(r'\d+/\d+\s+(HB|QB)',ln)
            if pm:
                btype=pm.group(1)
            # Extraer variedad, tamaño, stems, label, precio, total
            # "FREEDOM 50CM 240 240 MARL CO 0603110000 $ 0,30 $ 72,00"
            vm=re.search(r'([A-Z][A-Z\s]+?)\s+(\d{2})CM\s+(\d+)\s+(\d+)\s+(\w*)\s+CO\s+\d+\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)',ln)
            if not vm: continue
            var=vm.group(1).strip(); sz=int(vm.group(2)); stems=int(vm.group(4))
            cur_label=vm.group(5).strip()
            if cur_label and cur_label not in ('CO',): label=cur_label
            try:
                price=float(vm.group(6).replace(',','.'))
                total=float(vm.group(7).replace(',','.'))
            except: price=0.0; total=0.0
            # SPB: extraer de "ROSES*25 STEMS" en el texto
            spb_m=re.search(r'ROSES\*(\d+)\s+STEMS',text)
            spb=int(spb_m.group(1)) if spb_m else 25
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,origin='COL',
                           size=sz,stems_per_bunch=spb,stems=stems,
                           price_per_stem=price,line_total=total,label=label,box_type=btype)
            lines.append(il)
        return h, lines


class ValleVerdeParser:
    """Boxs Order BoxT Id. Description Len. Bun/BoxT. Bunch Stems Price Total
    FIX: variedades en mixed-case (Nectarine, Brighton, Iguazu).
    FIX: label R19 aparece como "R19" en la columna Id antes de la variedad.
    """
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Date[:\s]+([\d\-]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'M\.\s*A\.?\s*W\.?\s*B\.?[:\s]*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'H\.\s*A\.?\s*W\.?\s*B\.?[:\s]*([\w\-]+)',text,re.I); h.hawb=m.group(1).strip() if m else ''
        lines=[]; label=''
        for ln in text.split('\n'):
            ln=ln.strip()
            lbl_m=re.search(r'\b(R\d{1,2}[\w\-]*)\b',ln)
            if lbl_m: label=lbl_m.group(1)
            # FIX: [A-Za-z] para mixed-case variedades
            # "1 1-1 HB Nectarine 50 12 12 300 0,300 90,000"
            # "3-3 HB R19 Brighton 50 2 2 50 0,330 16,500"
            pm=re.search(r'(?:HB|QB)\s+(?:R\d+\s+)?([A-Za-z][A-Za-z\s.\-/]+?)\s+(\d{2})\s+\d+\s+(\d+)\s+(\d+)\s+([\d,]+)\s+([\d,]+)',ln)
            if not pm: continue
            var=pm.group(1).strip().upper(); sz=int(pm.group(2))
            try: bunches=int(pm.group(3)); stems=int(pm.group(4)); price=float(pm.group(5).replace(',','.')); total=float(pm.group(6).replace(',','.'))
            except: continue
            spb=stems//bunches if bunches else 25
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                           size=sz,stems_per_bunch=spb,bunches=bunches,stems=stems,
                           price_per_stem=price,line_total=total,label=label)
            lines.append(il)
        return h, lines

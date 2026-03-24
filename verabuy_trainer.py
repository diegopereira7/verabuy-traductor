#!/usr/bin/env python3
"""
VERABUY — Entrenador Universal de Traductores v1.0

Procesa facturas PDF de todos los proveedores habituales y genera
los sinónimos necesarios para el traductor de VeraBuy.

Uso: python verabuy_trainer.py
"""
import json, os, re, sys, subprocess, glob
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, List, Dict
try:
    from tabulate import tabulate
except ImportError:
    print("Falta 'tabulate'. Ejecuta: pip install tabulate"); input("Enter..."); sys.exit(1)
try:
    import pdfplumber; HAS_PDF=True
except ImportError:
    HAS_PDF=False

SCRIPT_DIR  = Path(__file__).parent.resolve()
PDF_DIR     = SCRIPT_DIR / 'facturas'
EXPORT_DIR  = SCRIPT_DIR / 'exportar'
SYNS_FILE   = SCRIPT_DIR / 'sinonimos_universal.json'
HIST_FILE   = SCRIPT_DIR / 'historial_universal.json'

# ──────────────────────────────────────────────────────────────────────────────
# REGISTRO DE PROVEEDORES
# id=0 → proveedor aún no dado de alta en la BD; actualiza cuando lo tengas
# ──────────────────────────────────────────────────────────────────────────────
PROVIDERS = {
    'cantiza'    : {'id':2222,  'name':'Cantiza Flores',         'fmt':'cantiza',      'patterns':['cantizafloral.com','CANTIZA FLORES']},
    'valtho'     : {'id':435,   'name':'Valthomig',              'fmt':'cantiza',      'patterns':['VALTHOMIG']},
    'agrivaldani': {'id':2228,  'name':'Agrivaldani',            'fmt':'agrivaldani',  'patterns':['AGRIVALDANI']},
    'luxus'      : {'id':1429,  'name':'Luxus Blumen',           'fmt':'agrivaldani',  'patterns':['LUXUSBLUMEN','LUXUS BLUMEN']},
    'brissas'    : {'id':0,     'name':'Brissas',                'fmt':'brissas',      'patterns':['RUC: 1716780331001','BRISSAS']},
    'alegria'    : {'id':8870,  'name':'La Alegria Farm',        'fmt':'alegria',      'patterns':['LA ALEGRIAFARM','rosasdelaalegria']},
    'olimpo'     : {'id':430,   'name':'Olimpo Flowers',         'fmt':'alegria',      'patterns':['OLIMPO FLOWERS']},
    'fairis'     : {'id':0,     'name':'Fairis Garden',          'fmt':'alegria',      'patterns':['FAIRIS GARDEN','fairisgarden']},
    'aluna'      : {'id':3375,  'name':'Inversiones del Neusa',  'fmt':'aluna',        'patterns':['INVERSIONES DEL NEUSA','alunaflowers']},
    'daflor'     : {'id':9750,  'name':'Daflor',                 'fmt':'daflor',       'patterns':['DAFLOR S.A','diagudelo@daflor']},
    'turflor'    : {'id':306,   'name':'Turflor',                'fmt':'daflor',       'patterns':['TURFLOR']},
    'eqr'        : {'id':2229,  'name':'EQR USA',                'fmt':'eqr',          'patterns':['EQUATOROSES','EQR USA']},
    'bosque'     : {'id':0,     'name':'Bosque Flowers',         'fmt':'bosque',       'patterns':['BOSQUEFLOWERS','bosqueflowers']},
    'colibri'    : {'id':313,   'name':'Colibri Flowers',        'fmt':'colibri',      'patterns':['COLIBRI FLOWERS']},
    'golden'     : {'id':310,   'name':'Benchmark Growers',      'fmt':'golden',       'patterns':['Benchmark Growers','benchmarkgrowers']},
    'latin'      : {'id':6323,  'name':'Latin Flowers',          'fmt':'latin',        'patterns':['LATIN FLOWERS','latinflowers.com.co']},
    'multiflora' : {'id':8342,  'name':'Multiflora',             'fmt':'multiflora',   'patterns':['MULTIFLORA CORPORATION','multiflorasales']},
    'florsani'   : {'id':419,   'name':'Florsani',               'fmt':'florsani',     'patterns':['FLORSANI','FLORICOLA SAN ISIDRO','1792059232001']},
    'maxi'       : {'id':281,   'name':'Maxiflores',             'fmt':'maxi',         'patterns':['MAXIFLORES','C.I. MAXIFLORES']},
    'mystic'     : {'id':442,   'name':'Mystic Flowers',         'fmt':'mystic',       'patterns':['MYSTICFLOWERS']},
    'fiorentina' : {'id':6916,  'name':'Fiorentina Flowers',     'fmt':'mystic',       'patterns':['FIORENTINA FLOWERS']},
    'stampsy'    : {'id':2220,  'name':'Stampsybox',             'fmt':'mystic',       'patterns':['STAMPSYBOX']},
    'prestige'   : {'id':11391, 'name':'Prestige Roses',         'fmt':'prestige',     'patterns':['PRESTIGE ROSES']},
    'rosely'     : {'id':0,     'name':'Rosely Flowers',         'fmt':'rosely',       'patterns':['ROSELY FLOWERS','roselyflowers']},
    'condor'     : {'id':11915, 'name':'Condor Andino',          'fmt':'condor',       'patterns':['CONDOR ANDINO']},
    'malima'     : {'id':7563,  'name':'Starflowers (Malima)',   'fmt':'malima',       'patterns':['STARFLOWERS','MALIMA EUROPA']},
    'monterosa'  : {'id':1434,  'name':'Monterosas Farms',       'fmt':'monterosa',    'patterns':['MONTEROSASLIMITADA','MONTEROSAS']},
    'secore'     : {'id':7338,  'name':'Secore Floral',          'fmt':'secore',       'patterns':['Sécore Floral','SECORE FLORAL','Score Floral']},
    'tessa'      : {'id':13001, 'name':'Tessa Corp',             'fmt':'tessa',        'patterns':['TESSA CORP','tessacorporation']},
    'uma'        : {'id':440,   'name':'Uma Flowers',            'fmt':'uma',          'patterns':['UMAFLOWERS','umaflowers']},
    'valleverde' : {'id':2219,  'name':'Valle Verde Farms',      'fmt':'valleverde',   'patterns':['VALLEVERDE FARMS','VALLE VERDE FARMS','valleverderoses','1792027691001']},
    'verdesestacion':{'id':11748,'name':'Verdes La Estacion',   'fmt':'aluna',        'patterns':['VERDES LA ESTACION','900.408.822']},
    'sayonara'   : {'id':2166,  'name':'Sayonara',               'fmt':'sayonara',     'patterns':['CULTIVOS SAYONARA','SAYONARA']},
    'life'       : {'id':4471,  'name':'Life Flowers',           'fmt':'life',         'patterns':['LIFEFLOWERS','lifeflowersecuador']},
    'latina'     : {'id':12990, 'name':'Floricola Latinafarms',  'fmt':'alegria',      'patterns':['FLORICOLA LATINAFARMS','LATINA']},
}

# Regex que elimina el sufijo de proveedor al final del nombre de artículo
# Ej: "ROSA EC EXPLORER 60CM 25U CANTIZA" → "ROSA EC EXPLORER 60CM 25U"
_PROVIDER_SUFFIX_RE = re.compile(
    r'\s+(' + '|'.join(re.escape(k.upper()) for k in PROVIDERS) + r')\s*$', re.I)
def _strip_provider_suffix(name:str) -> str:
    return _PROVIDER_SUFFIX_RE.sub('', name).strip()

# ──────────────────────────────────────────────────────────────────────────────
class C:
    if sys.platform=='win32': os.system('')
    OK='\033[92m'; WARN='\033[93m'; ERR='\033[91m'; BOLD='\033[1m'; DIM='\033[2m'
    RESET='\033[0m'; CYAN='\033[96m'; MAG='\033[95m'

def clear(): os.system('cls' if sys.platform=='win32' else 'clear')

_CARNATION_COLOR_MAP = {
    'WHITE':'BLANCO','BLANCA':'BLANCO','RED':'ROJO','ROJA':'ROJO',
    'PINK':'ROSA','ROSE':'ROSA','YELLOW':'AMARILLO','AMARILLA':'AMARILLO',
    'MIX':'MIXTO','MIXED':'MIXTO','ORANGE':'NARANJA','PURPLE':'MORADO',
    'VIOLET':'VIOLETA','LILAC':'LILA','PEACH':'MELOCOTON','SALMON':'SALMON',
    'GREEN':'VERDE','NOVELTY':'NOVEDADES','NOVELTIES':'NOVEDADES',
    'BICOLOR':'BICOLOR','DARK':'OSCURO','LIGHT':'CLARO',
}
def _translate_carnation_color(v:str) -> str:
    """Traduce palabras de color de claveles del inglés al español."""
    v_up=v.upper().strip()
    if v_up in _CARNATION_COLOR_MAP: return _CARNATION_COLOR_MAP[v_up]
    return ' '.join(_CARNATION_COLOR_MAP.get(w,w) for w in v_up.split())

# ──────────────────────────────────────────────────────────────────────────────
# DATACLASSES
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class InvoiceHeader:
    invoice_number:str=''; date:str=''; awb:str=''; hawb:str=''
    provider_key:str=''; provider_id:int=0; provider_name:str=''
    total:float=0.0; airline:str=''; incoterm:str=''

@dataclass
class InvoiceLine:
    # Datos de factura
    raw_description:str=''
    species:str='ROSES'          # ROSES CARNATIONS HYDRANGEAS ALSTROEMERIA GYPSOPHILA CHRYSANTHEMUM OTHER
    variety:str=''               # nombre de variedad / color según especie
    grade:str=''                 # FANCY SELECT PREMIUM STANDARD
    origin:str='EC'              # EC COL
    size:int=0                   # cm
    stems_per_bunch:int=0
    bunches:int=0
    stems:int=0
    price_per_stem:float=0.0
    price_per_bunch:float=0.0
    line_total:float=0.0
    label:str=''; farm:str=''; box_type:str=''; provider_key:str=''
    # Resultado del match
    articulo_id:Optional[int]=None
    articulo_name:str=''
    match_status:str='pendiente'
    match_method:str=''

    def expected_name(self) -> str:
        """Construye el nombre esperado en VeraBuy según especie y origen."""
        v=self.variety.upper(); s=self.size; u=self.stems_per_bunch; g=self.grade.upper()
        if self.species=='ROSES':
            orig='EC' if self.origin=='EC' else 'COL'
            if orig=='EC': return f"ROSA EC {v} {s}CM {u}U" if s and u else f"ROSA EC {v}"
            return f"ROSA COL {v} {s}CM {u}U" if s and u else f"ROSA COL {v}"
        if self.species=='CARNATIONS':
            color=_translate_carnation_color(v)
            sz=s if s else 70  # tamaño estándar si no viene en la factura
            if self.provider_key=='golden':
                prefix='MINI CLAVEL' if u==10 else 'CLAVEL'
                return f"{prefix} FANCY {color} {sz}CM {u}U GOLDEN"
            if 'SPRAY' in v.upper():
                return f"CLAVEL SPRAY {g} {color} {sz}CM {u}U".replace('  ',' ') if g else f"CLAVEL SPRAY {color} {sz}CM {u}U"
            return f"CLAVEL COL {g} {color} {sz}CM {u}U".replace('  ',' ') if g else f"CLAVEL COL {color} {sz}CM {u}U"
        if self.species=='HYDRANGEAS':
            if self.provider_key=='latin':
                return f"HYDRANGEA {v} 60CM 1U LATIN"
            return f"HYDRANGEA {v} {s}CM {u}U" if s and u else f"HYDRANGEA {v}"
        if self.species=='ALSTROEMERIA':
            orig='COL' if self.origin=='COL' else 'EC'
            return f"ALSTROMERIA {orig} {g} {v} {s}CM {u}U".replace('  ',' ') if s else f"ALSTROMERIA {orig} {v}"
        if self.species=='GYPSOPHILA':
            return f"PANICULATA {v}"
        if self.species=='CHRYSANTHEMUM':
            if self.provider_key=='sayonara':
                return f"CRISANTEMO {v} {s}CM {u}U SAYONARA"
            return f"CRISANTEMO {v} {s}CM {u}U" if s else f"CRISANTEMO {v}"
        return v

    def match_key(self) -> str:
        return f"{self.species}|{self.variety.upper()}|{self.size}|{self.stems_per_bunch}|{self.grade.upper()}"

# ──────────────────────────────────────────────────────────────────────────────
# CARGADOR DE ARTÍCULOS
# ──────────────────────────────────────────────────────────────────────────────
class ArticulosLoader:
    def __init__(self):
        self.articulos:Dict[int,dict]={}
        self.by_name:Dict[str,int]={}
        self.rosas_ec:Dict[str,int]={}
        self.rosas_col:Dict[str,int]={}
        self.by_species:Dict[str,List]={}   # species_prefix → [(normalized_key, id)]
        self.loaded=False

    def load_from_sql(self, sql_path):
        count=0
        species_prefixes={
            'ROSA EC':'ROSES_EC','ROSA COL':'ROSES_COL',
            'MINI CLAVEL':'CARNATIONS','CLAVEL':'CARNATIONS','HYDRANGEA':'HYDRANGEAS',
            'ALSTROMERIA':'ALSTROEMERIA','ALSTROEMERIA':'ALSTROEMERIA',
            'PANICULATA':'GYPSOPHILA','CRISANTEMO':'CHRYSANTHEMUM',
            'DIANTHUS':'OTHER',
        }
        for sp in set(species_prefixes.values()): self.by_species[sp]=[]
        with open(sql_path,'r',encoding='utf-8') as f:
            for raw in f:
                ln=raw.strip()
                if not ln.startswith('('): continue
                ln=ln.rstrip(',;')
                try:
                    art=self._parse_row(ln)
                    if not art: continue
                    self.articulos[art['id']]=art
                    nombre=art['nombre']
                    if nombre:
                        self.by_name[nombre.upper()]=art['id']
                        clean=_strip_provider_suffix(nombre.upper())
                        if clean!=nombre.upper(): self.by_name[clean]=art['id']
                        self._index_species(art, species_prefixes)
                    count+=1
                except: continue
        self.loaded=True
        return count

    def _index_species(self, art, prefixes):
        nombre=art['nombre'].upper()
        for prefix, sp in prefixes.items():
            if nombre.startswith(prefix):
                # Strip producer suffix (CANTIZA, GOLDEN, COLIBRI, etc.)
                rest=_strip_provider_suffix(nombre[len(prefix):].strip())
                self.by_species[sp].append((rest, art['id']))
                # Special fast-access dicts for roses
                if sp=='ROSES_EC':
                    rm=re.match(r'(.+?)\s+(\d+)CM\s+(\d+)U',rest)
                    if rm:
                        key=f"{rm.group(1).strip()} {rm.group(2)}CM {rm.group(3)}U"
                        self.rosas_ec[key]=art['id']
                elif sp=='ROSES_COL':
                    rm=re.match(r'(?:([A-Z0-9]+)\s+)?(.+?)\s+(\d+)CM\s+(\d+)U',rest)
                    if rm:
                        self.rosas_col[rest]=art['id']
                break
        else:
            # "ROSA VARIEDAD XCMYU PROVEEDOR" — sin prefijo EC/COL
            # Se añade a los dos pools para que funcione tanto desde EC como COL
            clean=_strip_provider_suffix(nombre)
            if re.match(r'ROSA\s+[A-Z]', clean):
                rest=clean[5:].strip()  # quitar "ROSA "
                self.by_species['ROSES_EC'].append((rest, art['id']))
                self.by_species['ROSES_COL'].append((rest, art['id']))
                rm=re.match(r'(.+?)\s+(\d+)CM\s+(\d+)U', rest)
                if rm:
                    key=f"{rm.group(1).strip()} {rm.group(2)}CM {rm.group(3)}U"
                    self.rosas_ec[key]=art['id']
                    self.rosas_col[key]=art['id']

    def find_rose_ec(self, variety, size, spb):
        key=f"{variety.upper()} {size}CM {spb}U"
        if key in self.rosas_ec: return self.articulos[self.rosas_ec[key]]
        for k,aid in self.rosas_ec.items():
            if k.startswith(variety.upper()) and f"{size}CM" in k and f"{spb}U" in k:
                return self.articulos[aid]
        return None

    def find_rose_col(self, variety, size, spb, grade=''):
        targets=[
            f"{grade.upper()} {variety.upper()} {size}CM {spb}U",
            f"{variety.upper()} {size}CM {spb}U",
        ]
        for t in targets:
            if t.strip() in self.rosas_col: return self.articulos[self.rosas_col[t.strip()]]
        return None

    def find_by_name(self, name:str):
        name=name.upper().strip()
        if name in self.by_name: return self.articulos[self.by_name[name]]
        # Fallback: quitar "EC " o "COL " para artículos tipo "ROSA VARIEDAD XCMYU PROVEEDOR"
        no_orig=re.sub(r'^(ROSA)\s+(EC|COL)\s+',r'\1 ',name)
        if no_orig!=name and no_orig in self.by_name:
            return self.articulos[self.by_name[no_orig]]
        return None

    def fuzzy_search(self, line:InvoiceLine, threshold=0.4):
        """Búsqueda fuzzy según especie."""
        sp_map={'ROSES':'ROSES_EC','ROSES_EC':'ROSES_EC','ROSES_COL':'ROSES_COL',
                'CARNATIONS':'CARNATIONS','HYDRANGEAS':'HYDRANGEAS',
                'ALSTROEMERIA':'ALSTROEMERIA','GYPSOPHILA':'GYPSOPHILA',
                'CHRYSANTHEMUM':'CHRYSANTHEMUM'}
        if line.origin=='COL' and line.species=='ROSES': sp_key='ROSES_COL'
        else: sp_key=sp_map.get(line.species,'ROSES_EC')
        pool=self.by_species.get(sp_key,[])
        if not pool: return []
        query=self._query_key(line)
        cands=[]
        for rest, aid in pool:
            r=SequenceMatcher(None, query, rest).ratio()
            if r>=threshold:
                cands.append({'id':aid,'nombre':self.articulos[aid]['nombre'],'similitud':round(r*100,1),'key':rest})
        return sorted(cands,key=lambda x:x['similitud'],reverse=True)[:5]

    def _query_key(self, line:InvoiceLine) -> str:
        v=line.variety.upper(); s=line.size; u=line.stems_per_bunch; g=line.grade.upper()
        if line.species in ('ROSES','ROSES_EC','ROSES_COL'):
            return f"{v} {s}CM {u}U" if s and u else v
        if line.species=='CARNATIONS':
            color=_translate_carnation_color(v)
            sz=s if s else 70
            if getattr(line,'provider_key','')=='golden':
                return f"FANCY {color} {sz}CM {u}U"
            return (f"COL {g} {color} {sz}CM {u}U" if g else f"COL {color} {sz}CM {u}U").replace('  ',' ').strip()
        if line.species in ('HYDRANGEAS','ALSTROEMERIA','CHRYSANTHEMUM'):
            return f"{v} {s}CM {u}U" if s and u else v
        if line.species=='GYPSOPHILA':
            return v
        return v

    def _parse_row(self,line):
        if not line.startswith('('): return None
        inner=line[1:].rstrip(')')
        flds=self._split(inner)
        if len(flds)<10: return None
        def cs(v):
            v=v.strip()
            if v=='NULL': return ''
            if v.startswith("'") and v.endswith("'"): return v[1:-1].replace("\\'","'")
            return v
        def ci(v):
            v=v.strip(); return int(v) if v.replace('-','').isdigit() else 0
        return {'id':ci(flds[0]),'nombre':cs(flds[8]),'familia':cs(flds[9]),
                'tamano':cs(flds[5]),'paquete':ci(flds[7]),'id_proveedor':ci(flds[3])}

    @staticmethod
    def _split(s):
        parts=[];cur='';inq=False;esc=False
        for ch in s:
            if esc: cur+=ch;esc=False;continue
            if ch=='\\': cur+=ch;esc=True;continue
            if ch=="'" and not inq: inq=True;cur+=ch;continue
            if ch=="'" and inq: inq=False;cur+=ch;continue
            if ch==',' and not inq: parts.append(cur);cur='';continue
            cur+=ch
        if cur: parts.append(cur)
        return parts

# ──────────────────────────────────────────────────────────────────────────────
# SINÓNIMOS
# ──────────────────────────────────────────────────────────────────────────────
class SynonymStore:
    def __init__(self, fp=SYNS_FILE):
        self.fp=Path(fp); self.syns={}
        if self.fp.exists():
            with open(self.fp,'r',encoding='utf-8') as f: self.syns=json.load(f)

    def save(self):
        with open(self.fp,'w',encoding='utf-8') as f: json.dump(self.syns,f,indent=2,ensure_ascii=False)

    def _k(self, provider_id, line:InvoiceLine): return f"{provider_id}|{line.match_key()}"

    def find(self, provider_id, line:InvoiceLine): return self.syns.get(self._k(provider_id,line))

    def add(self, provider_id, line:InvoiceLine, aid, aname, origin='manual'):
        k=self._k(provider_id,line)
        self.syns[k]={'articulo_id':aid,'articulo_name':aname,'origen':origin,
                       'provider_id':provider_id,'species':line.species,
                       'variety':line.variety.upper(),'size':line.size,
                       'stems_per_bunch':line.stems_per_bunch,'grade':line.grade.upper()}
        self.save()

    def count(self): return len(self.syns)

    def export_sql(self):
        if not self.syns: return '-- No hay sinónimos'
        lines=["-- Sinónimos Universales — verabuy_trainer.py",
               f"-- {datetime.now():%Y-%m-%d %H:%M} — {len(self.syns)} sinónimos","",
               "INSERT INTO `sinonimos_producto`",
               "    (`id_proveedor`,`nombre_factura`,`especie`,`talla`,`stems_per_bunch`,",
               "     `id_articulo`,`nombre_articulo`,`confianza`,`origen`)",
               "VALUES"]
        vals=[];pend=[]
        for syn in sorted(self.syns.values(),key=lambda s:(s['provider_id'],s['species'],s['variety'])):
            if syn['articulo_id']==0: pend.append(syn); continue
            en=syn['articulo_name'].replace("'","\\'")
            sp=syn.get('species','ROSES')
            vals.append(f"    ({syn['provider_id']},'{syn['variety']}','{sp}',{syn['size']},{syn['stems_per_bunch']},{syn['articulo_id']},'{en}',100,'{syn['origen']}')")
        if vals: lines.append(',\n'.join(vals)+';')
        if pend:
            lines+=['',f'-- PENDIENTES DE ALTA ({len(pend)}):']
            for p in pend: lines.append(f"--   {p.get('species','')} {p['variety']} {p['size']}CM {p['stems_per_bunch']}U")
        return '\n'.join(lines)

# ──────────────────────────────────────────────────────────────────────────────
# MATCHER
# ──────────────────────────────────────────────────────────────────────────────
class Matcher:
    def __init__(self, art:ArticulosLoader, syn:SynonymStore):
        self.art=art; self.syn=syn

    def match_line(self, provider_id:int, l:InvoiceLine) -> InvoiceLine:
        # 1. Sinónimo guardado
        s=self.syn.find(provider_id,l)
        if s and s['articulo_id']>0:
            l.articulo_id=s['articulo_id']; l.articulo_name=s['articulo_name']
            l.match_status='ok'; l.match_method='sinónimo'; return l
        # 2. Match exacto por nombre esperado
        a=self.art.find_by_name(l.expected_name())
        if a:
            l.articulo_id=a['id']; l.articulo_name=a['nombre']
            l.match_status='ok'; l.match_method='exacto'
            self.syn.add(provider_id,l,a['id'],a['nombre'],'auto'); return l
        # 3. Match por rosa (si es rosa)
        if l.species=='ROSES' and l.size and l.stems_per_bunch:
            fn=self.art.find_rose_ec if l.origin!='COL' else self.art.find_rose_col
            a=fn(l.variety,l.size,l.stems_per_bunch) if l.origin!='COL' else self.art.find_rose_col(l.variety,l.size,l.stems_per_bunch,l.grade)
            if a:
                l.articulo_id=a['id']; l.articulo_name=a['nombre']
                l.match_status='ok'; l.match_method='exacto'
                self.syn.add(provider_id,l,a['id'],a['nombre'],'auto'); return l
        # 4. Auto-fuzzy ≥90%
        cands=self.art.fuzzy_search(l,threshold=0.90)
        if cands:
            best=cands[0]; l.articulo_id=best['id']; l.articulo_name=best['nombre']
            l.match_status='ok'; l.match_method=f"fuzzy {best['similitud']}%"
            self.syn.add(provider_id,l,best['id'],best['nombre'],'auto-fuzzy'); return l
        l.match_status='sin_match'; l.match_method=''; return l

    def match_all(self, provider_id, lines): return [self.match_line(provider_id,l) for l in lines]

# ──────────────────────────────────────────────────────────────────────────────
# HISTORIAL
# ──────────────────────────────────────────────────────────────────────────────
class History:
    def __init__(self, fp=HIST_FILE):
        self.fp=Path(fp); self.entries={}
        if self.fp.exists():
            with open(self.fp,'r',encoding='utf-8') as f: self.entries=json.load(f)
    def save(self):
        with open(self.fp,'w',encoding='utf-8') as f: json.dump(self.entries,f,indent=2,ensure_ascii=False)
    def add(self,inv,pdf,provider,total,n,ok,fail):
        self.entries[inv]={'pdf':pdf,'provider':provider,'total_usd':total,'lineas':n,'ok':ok,'sin_match':fail,'fecha':f"{datetime.now():%Y-%m-%d %H:%M}"}
        self.save()
    def was_processed(self,inv): return inv in self.entries

# ══════════════════════════════════════════════════════════════════════════════
# PARSERS
# ══════════════════════════════════════════════════════════════════════════════

def _pdf_text(path):
    try:
        r=subprocess.run(['pdftotext','-layout',path,'-'],capture_output=True,text=True,timeout=15)
        if r.returncode==0 and r.stdout.strip(): return r.stdout
    except: pass
    if HAS_PDF:
        with pdfplumber.open(path) as p: return '\n'.join(pg.extract_text() or '' for pg in p.pages)
    raise RuntimeError("Instala poppler-utils o: pip install pdfplumber")

def detect_provider(path:str) -> Optional[dict]:
    try: text=_pdf_text(path)
    except: return None
    for pkey,pdata in PROVIDERS.items():
        for pat in pdata['patterns']:
            if pat.lower() in text.lower():
                return {**pdata,'key':pkey,'text':text}
    return None

# ─── Cantiza / Valtho / Vatho ─────────────────────────────────────────────────
class CantizaParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        def f(p,d=''):
            m=re.search(p,text,re.I|re.DOTALL); return m.group(1).strip() if m else d
        h.invoice_number=f(r'(?:Invoice\s+Numbers?|CUSTOMER\s+INVOICE)\s+(\S+)')
        h.date=f(r'Invoice\s+Date\s+([\d/]+)')
        h.awb=re.sub(r'\s+','',f(r'MAWB\s+([\d\-\s]+?)(?:\s{2,}|HAWB)'))
        h.hawb=f(r'HAWB\s+(\S+)')
        try: h.total=float(f(r'Amount\s+Due\s+\$?([\d,]+\.?\d*)','0').replace(',',''))
        except: h.total=0.0
        lines=[]
        label=''; btype=''; farm=''
        for raw in text.split('\n'):
            ln=raw.strip()
            if not ln: continue
            bm=re.search(r'HB\s+CAN[- ]?([\dX.]+)',ln)
            if bm: btype=f"HB CAN-{bm.group(1)}"
            if re.search(r'MIXED\s+BOX',ln):
                lm=re.search(r'\$[\d.]+\s+([A-Z][\w\s\-]*?)\s*$',ln)
                if lm:
                    raw2=lm.group(1).strip()
                    if raw2 and raw2!='TOTALS': label=re.split(r'\s{4,}',raw2)[0].strip()
                fm=re.search(r'(C\d+)\s+\d+\s+\$',ln)
                if fm: farm=fm.group(1)
                continue
            pm=re.search(r'(\w[\w\s]*?)\s+(\d+)CM\s+N\s+(\d+)ST\s+CZ',ln)
            if not pm: continue
            var=re.sub(r'^[\d*X.]+\s+','',pm.group(1).strip()).strip()
            var=re.sub(r'\([\d*X.]+\)','',var).strip()
            if not var: continue
            sz,spb=int(pm.group(2)),int(pm.group(3))
            fm2=re.search(r'(?:ROSES|CARNATION)\s+(C\d+)',ln)
            if fm2: farm=fm2.group(1).upper()
            nm=re.search(rf'(?:C\d+)\s+(\d+)\s+\$([\d.]+)\s+(\d+)\s+\$([\d.]+)\s+\$([\d.]+)',ln)
            bunches=int(nm.group(1)) if nm else 0
            ppb=float(nm.group(2)) if nm else 0.0
            stems=int(nm.group(3)) if nm else 0
            pps=float(nm.group(4)) if nm else 0.0
            total=float(nm.group(5)) if nm else 0.0
            if stems==0 and bunches>0: stems=bunches*spb
            il=InvoiceLine(raw_description=f"{var} {sz}CM N {spb}ST CZ",species='ROSES',variety=var,
                           size=sz,stems_per_bunch=spb,bunches=bunches,stems=stems,
                           price_per_stem=pps,price_per_bunch=ppb,line_total=total,
                           label=label,farm=farm,box_type=btype)
            lines.append(il)
        return h,lines

# ─── Agrivaldani / Luxus ──────────────────────────────────────────────────────
class AgrivaldaniParser:
    """
    Formato Agrivaldani/Luxus.
    QUARTER/HALF/FULL = tipo de caja (nunca variedad).
    La variedad puede estar en la misma línea que los números
    o en una línea propia justo antes (carry-forward).

    Casos:
      Luxus:       "1 HALF FREEDOM 40 25 12 300 0.22 22.00"
      Agrivaldani: variedad en sub-cabecera, datos en siguiente línea
      Agrivaldani1:"1-1 R15  1 QUARTER EXPLORER 50 25 1 25 0.30 7.50"
                   "MUNDIAL 50 25 1 25 0.38 9.50"
                   "CARROUSEL  1"  ← sólo variedad + cantidad, hereda tamaño
    """
    _NOISE = re.compile(r'^(TOTAL|FOB|USD|ORDER|BOX|TYPE|VARIETIES|STEMS|PRICE|BUNCH|CARPE\s+DIEM\s+STEMS)', re.I)
    _BTYPE = re.compile(r'\b(QUARTER|HALF|FULL)\b', re.I)
    _VARONLY = re.compile(r'^([A-Z][A-Z\s]{2,25}?)\s+(\d+)\s*$')  # "CARROUSEL  1"

    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'Invoice\s+#[:\s]+(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Date[:\s]+([\d/\-]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB[:\s]+([\d\-\s]+?)(?:\s{2,}|HAWB)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'HAWB[:\s]+(\S+)',text,re.I); h.hawb=m.group(1) if m else ''
        try:
            m=re.search(r'TOTAL:\s+[A-Z\s]+AND\s+[\d/]+\s+USD',text,re.I)
            # fallback: last number before USD
            m2=re.search(r'\$([\d,]+\.?\d*)\s*$',text,re.M)
            h.total=float(m2.group(1).replace(',','')) if m2 else 0.0
        except: h.total=0.0

        raw_lines=text.split('\n')
        lines=[]; current_variety=''; current_sz=50; current_spb=25; current_btype=''

        for ln in raw_lines:
            ln=ln.strip()
            if not ln: continue

            bt=self._BTYPE.search(ln)
            if bt: current_btype=bt.group(1).upper()

            # ── Limpiar prefijos de orden y tipo de caja ──
            clean=re.sub(r'^\d+\s*[-–]\s*\d+\s+\S+\s+','',ln)              # "1 - 1 R15 "
            clean=re.sub(r'^\d+\s+(?:QUARTER|HALF|FULL)\s+','',clean,flags=re.I)  # "1 QUARTER "
            clean=re.sub(r'^(?:QUARTER|HALF|FULL)\s+','',clean,flags=re.I)         # "HALF " residual

            # ── Patrón A: variedad + CM + SPB + (bunches) + stems + price + total ──
            # "FREEDOM 40 25 12 300 0.22 22.00"  /  "E. BLACK 50 25 1 25 0.30 15.00"
            pm=re.search(
                r'^([A-Z][A-Z\s.]{1,28}?)\s+'  # variedad (admite puntos y espacios)
                r'(\d{2})\s+(\d{2})\s+'         # CM  SPB
                r'\d*\s*(\d+)\s+'               # (bunches?)  stems
                r'([\d.]+)\s+([\d.]+)',          # price  total
                clean, re.I
            )
            if pm:
                candidate=pm.group(1).strip()
                sz=int(pm.group(2)); spb=int(pm.group(3))
                stems=int(pm.group(4))
                try: price=float(pm.group(5)); total=float(pm.group(6))
                except: price=0.0; total=0.0
                if not self._NOISE.match(candidate):
                    current_variety=candidate; current_sz=sz; current_spb=spb
                elif current_variety:
                    sz=current_sz; spb=current_spb
                else:
                    continue
                if not current_variety: continue
                il=InvoiceLine(raw_description=ln,species='ROSES',variety=current_variety,
                               size=sz,stems_per_bunch=spb,stems=stems,
                               price_per_stem=price,line_total=total,box_type=current_btype)
                lines.append(il); continue

            # ── Patrón B: variedad + bunches + stems + price + total (sin CM/SPB) ──
            # "M. DARK BLUE  1  25  0.90  22.50"  — hereda CM/SPB del contexto
            pm2=re.search(
                r'^([A-Z][A-Z\s.]{1,28}?)\s+'   # variedad
                r'(\d{1,3})\s+(\d{1,3})\s+'     # bunches  stems
                r'([\d.]+)\s+([\d.]+)',           # price  total
                clean, re.I
            )
            if pm2 and current_sz:
                candidate=pm2.group(1).strip()
                if not self._NOISE.match(candidate) and len(candidate)>2:
                    current_variety=candidate
                if not current_variety: continue
                try:
                    stems=int(pm2.group(3)); price=float(pm2.group(4)); total=float(pm2.group(5))
                except: continue
                il=InvoiceLine(raw_description=ln,species='ROSES',variety=current_variety,
                               size=current_sz,stems_per_bunch=current_spb,stems=stems,
                               price_per_stem=price,line_total=total,box_type=current_btype)
                lines.append(il); continue

            # ── Patrón C: solo números ── hereda variedad y CM/SPB
            # "50  25  1  25  0.38  9.50"  o  "60  25  100  0.90  22.50"
            nm=re.search(r'^(\d{2})\s+(\d{2})\s+\d*\s*(\d+)\s+([\d.]+)\s+([\d.]+)',clean)
            if nm and current_variety:
                sz=int(nm.group(1)); spb=int(nm.group(2)); stems=int(nm.group(3))
                try: price=float(nm.group(4)); total=float(nm.group(5))
                except: price=0.0; total=0.0
                il=InvoiceLine(raw_description=ln,species='ROSES',variety=current_variety,
                               size=sz,stems_per_bunch=spb,stems=stems,
                               price_per_stem=price,line_total=total,box_type=current_btype)
                lines.append(il); continue

            # ── Variedad sola (actualiza current_variety para siguiente línea) ──
            vo=self._VARONLY.match(clean)
            if vo:
                candidate=vo.group(1).strip()
                if not self._NOISE.match(candidate): current_variety=candidate

            # ── Sub-cabecera Agrivaldani: "TYPE  CARPE DIEM  STEMS  BOX..." ──
            hm=re.search(r'TYPE\s+([A-Z][A-Z\s]{2,20}?)\s+STEMS',ln,re.I)
            if hm:
                candidate=hm.group(1).strip()
                if not self._NOISE.match(candidate): current_variety=candidate

        # Deduplicar: agrupa múltiples cajas de misma variedad/talla/SPB
        seen={}
        for il in lines:
            k=f"{il.variety}|{il.size}|{il.stems_per_bunch}"
            if k not in seen: seen[k]=il
            else: seen[k].stems+=il.stems; seen[k].line_total+=il.line_total
        return h, list(seen.values())

# ─── Brissas ──────────────────────────────────────────────────────────────────
class BrissasParser:
    """Formato: ORDER MARK BX BOX VARIETIES CM STEMS TOTAL_STEMS UNIT TOTAL"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'Invoice\s+#[:\s]+(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Date[:\s]+([\d/\-]+)',text,re.I); h.date=m.group(1) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(?:HB|QB|TB)\s+(?:ROSE\s+)?([A-Z][A-Z\s]+?)\s+(\d{2})\s+(\d+)\s+([\d.]+)\s+([\d.]+)',ln)
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

# ─── Alegria / Olimpo / Fairis / Latina ──────────────────────────────────────
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
            pm=re.search(r'(\d+)\s+(QB|HB|QUA|HAL)\s+([A-Z][A-Z\s]+?)\s+(\d+)\s+X\s*\.00',ln)
            if not pm:
                pm=re.search(r'(QB|HB|QUA|HAL)\s+([A-Z][A-Z\s]+?)\s+(\d+)\s+X\s*\.00',ln)
                if pm:
                    btype=pm.group(1); var=pm.group(2).strip(); spb=int(pm.group(3))
                else: continue
            else:
                btype=pm.group(2); var=pm.group(3).strip(); spb=int(pm.group(4))
            if not var or re.match(r'^(TOT|SUB|TOTAL|DESCUENTO)',var.upper()): continue
            # Find sizes from column headers context and prices
            # Size: look for a column-based number pattern after the STxB
            size_m=re.search(r'X\s*\.00\s+(?:\d+\s+)*(\d+)\s+\S*\s+\d+\s+([\d.]+)\s+([\d.]+)',ln)
            sz=0
            total=0.0
            if size_m:
                try: total=float(size_m.group(3))
                except: pass
            # Try to get size from price area
            stems_m=re.search(r'(\d{2,3})\s+([\d.]+)\s+([\d.]+)\s*$',ln)
            stems=0; price=0.0
            if stems_m:
                try: stems=int(stems_m.group(1)); price=float(stems_m.group(2)); total=float(stems_m.group(3))
                except: pass
            k=f"{var}|{sz}|{spb}"
            if k not in seen:
                seen[k]=True
                il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                               size=sz,stems_per_bunch=spb,stems=stems,
                               price_per_stem=price,line_total=total,box_type=btype)
                lines.append(il)
        return h, lines

# ─── Aluna ───────────────────────────────────────────────────────────────────
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
            pm=re.search(r'([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([A-Z][A-Z\s]+?)\s+(\d{2})\s+\w+',ln)
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

# ─── Daflor / Turflor ─────────────────────────────────────────────────────────
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
            pm=re.search(r'(\d+)\s+(QB|HB|QUA|HAL)\s+([A-Z][A-Z\s\-]+?)\s*[-–]\s*([A-Za-z]+)',ln)
            if not pm:
                pm=re.search(r'(QB|HB)\s+([A-Z][A-Z\s\-]+?)\s*[-–]\s*([A-Za-z]+)\s',ln)
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

# ─── EQR ─────────────────────────────────────────────────────────────────────
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
            pm=re.search(r'Roses?\s+(?:\w+\s+)?([A-Z][a-zA-Z\s]+?)\s+(\d{2})\s+Cm?\s+x\s+(\d+)\s+Stem',ln,re.I)
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

# ─── Bosque ──────────────────────────────────────────────────────────────────
class BosqueParser:
    """Formato: #BOX PRODUCT-VARIETY TARIFF LENGTH BUNCHS STEMS T.STEMS PRICE AMOUNT"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'No\.:\s*(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'(?:MAWB|MAWB No)\s*[:\s]*([\d]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(?:\d+\s+)?(HB|QB|TB)\s+ROSAS?\s+([A-Z][A-Z\s]+?)\s+(\d{2})',ln)
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

# ─── Colibri ─────────────────────────────────────────────────────────────────
class ColibriParser:
    """
    Claveles Colibri.
    Formato: [N] H/Q  Carnation [COLOR] [X SPB] [- GRADE]  [BOX_IDs]  [Total] ST  [PRICE]  [TOTAL]
    - No hay talla en CM.
    - El número antes de ST ya es el total de tallos de esa línea.
    - X 20 indica tallos por ramo; si no aparece se asume 20.
    """
    GRADE_MAP={'FAN':'FANCY','SEL':'SELECT','STD':'STANDARD','PRE':'PREMIUM','FCY':'FANCY'}

    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+No\.\s*(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Date Invoice[:\s]+([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'AWB[:\s]+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            # Patrón: [N] H/Q  Carnation DESCRIPCIÓN ...  [N] ST  PRICE  TOTAL
            # La descripción termina en 3+ espacios o en un número de 6 dígitos (box ID)
            pm=re.search(
                r'(\d+)\s*[HQ]\s+'                                    # N cajas
                r'Carnation\s+'                                        # especie
                r'((?:[A-Za-z][A-Za-z\s/\-]*?))'                      # color/descripción
                r'(?=\s{3,}|\s+\d{6}|\s+X\s+\d|\s*[-–]\s*\w+\s{2,})',# fin descripción
                ln, re.I
            )
            if not pm: continue
            color=pm.group(2).strip().upper()

            # Extraer SPB del "X 20" — solo 2-3 dígitos, no IDs de caja
            spb_m=re.search(r'\bX\s+(\d{2,3})\b', ln)
            spb=int(spb_m.group(1)) if spb_m else 20

            # Extraer grado (FAN / SEL / etc.) de la línea
            grade_m=re.search(r'\b(FAN|SEL|STD|PRE|FCY)\b', ln, re.I)
            grade_raw=grade_m.group(1).upper() if grade_m else 'FAN'
            grade=self.GRADE_MAP.get(grade_raw[:3], 'FANCY')

            # Total de tallos: número antes de "ST"
            st_m=re.search(r'(\d+)\s+ST', ln)
            stems=int(st_m.group(1)) if st_m else 0

            # Precio y total
            prices=re.findall(r'([\d,]+\.[\d]{3})', ln)
            price=0.0; total=0.0
            if len(prices)>=2:
                try: price=float(prices[-2].replace(',','.')); total=float(prices[-1].replace(',','.'))
                except: pass
            elif len(prices)==1:
                try: total=float(prices[-1].replace(',','.'))
                except: pass

            # Caja mixta: "CARN MIX RED/YELLOW" → dos líneas, tallos y total ÷ 2
            # BICOLOR es una variedad en sí misma (flor bicolor), no se parte
            mix_m=re.search(r'([A-Za-z]+)\s*/\s*([A-Za-z]+)', color)
            if mix_m:
                c1=mix_m.group(1).strip().upper()
                c2=mix_m.group(2).strip().upper()
                half=stems//2; half_t=round(total/2,3)
                for cv in (c1,c2):
                    lines.append(InvoiceLine(raw_description=ln,species='CARNATIONS',variety=cv,
                                             grade=grade,origin='COL',size=0,
                                             stems_per_bunch=spb,stems=half,
                                             price_per_stem=price,line_total=half_t))
            else:
                lines.append(InvoiceLine(raw_description=ln,species='CARNATIONS',variety=color,
                                         grade=grade,origin='COL',size=0,
                                         stems_per_bunch=spb,stems=stems,
                                         price_per_stem=price,line_total=total))
        return h, lines

# ─── Golden / Benchmark ───────────────────────────────────────────────────────
class GoldenParser:
    """
    Benchmark Growers SAS (Golden) — Claveles y Miniclaveles.
    Formato: N H/Q Un/Box TotStems ItemDescription Grade/Color [BoxID] [ItemCode] Price Total
    - Grade/Color mezcla ruta (R45, PUERTO…) + color abreviado (WH, RD, MIX…)
    - Líneas con 2+ colores se dividen en sublíneas (50/50)
    - Artículos en BD: "CLAVEL FANCY {COLOR} 70CM 20U GOLDEN"
    """
    _LABELS = {'PUERTO','ASTURIAS','BARRAL','PYTI','DANI','GIJON','CRISTIAN'}
    _COLOR_MAP = {
        'WH':'BLANCO','WHITE':'BLANCO',
        'RD':'ROJO','RED':'ROJO',
        'PK':'ROSA','PINK':'ROSA',
        'YW':'AMARILLO','YELLOW':'AMARILLO',
        'BIC':'BICOLOR','BICOL':'BICOLOR','BICOLORES':'BICOLOR','BICOLOR':'BICOLOR',
        'NOV':'NOVEDADES','NOVEDADES':'NOVEDADES',
    }
    _SKIP = {'FCY','FANCY','CARN','CARNATION','MINI','MCAT','AST','CB','MC','S2','AT','X',
             'BUNCH','CONSUMER','ASSORTED','MINICARNS'}

    def _parse_grade_color(self, field:str):
        """Retorna (label, [colores_en_español]) del campo Grade/Color de Benchmark."""
        field = re.sub(r'(?<!\w)R-(\d+)', r'R\1', field.upper())
        tokens = re.split(r'[\s/]+', field)
        label = ''; colors = []
        for tok in tokens:
            tok = tok.strip('+- ')
            if not tok: continue
            rm = re.match(r'^R(\d+)$', tok)
            if rm: label = 'R' + rm.group(1); continue
            if tok in self._LABELS: label = tok; continue
            if tok in ('MIX','MIXED'): continue   # indicador; los colores vienen después
            if tok in self._SKIP: continue
            if tok in self._COLOR_MAP:
                c = self._COLOR_MAP[tok]
                if c not in colors: colors.append(c)
                continue
        if not colors: colors = ['MIXTO']
        return label, colors

    def _parse_invoice_line(self, ln:str):
        """Parsea una línea de factura anclando en el campo Item Description fijo."""
        desc_m = re.search(r'(CONSUMER\s+BUNCH\s+CARNATION\s+FANCY|MINICARNS\s+ASSORTED)', ln, re.I)
        if not desc_m: return None
        item_desc = desc_m.group(1).upper()
        before = ln[:desc_m.start()].strip()
        after  = ln[desc_m.end():].strip()
        bm = re.match(r'(\d+)\s+(H|Q)\s+(\d+)\s+(\d+)', before)
        if not bm: return None
        btype = bm.group(2).upper()
        upb   = int(bm.group(3))
        stems = int(bm.group(4))
        price_m = re.search(r'([\d.]+)\s+([\d.]+)\s*$', after)
        if not price_m: return None
        try: price=float(price_m.group(1)); total=float(price_m.group(2))
        except: return None
        grade_color = after[:price_m.start()].strip()
        ic_m = re.search(r'\b(CB|MC)\s+\S+\s*$', grade_color, re.I)
        if ic_m: grade_color = grade_color[:ic_m.start()].strip()
        return {'btype':btype,'upb':upb,'stems':stems,
                'item_desc':item_desc,'grade_color':grade_color,
                'price_per_stem':price,'total':total}

    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+No\.?\s*(\d+)',text,re.I);       h.invoice_number=m.group(1) if m else ''
        m=re.search(r'INVOICE\s+DATE\s+([\d/]+)',text,re.I);     h.date=m.group(1) if m else ''
        m=re.search(r'MAWB\s+No\.?\s*([\d\-]+)',text,re.I);      h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'HAWB\s+No\.?\s*([\d\-]+)',text,re.I);      h.hawb=re.sub(r'\s+','',m.group(1)) if m else ''
        m=re.search(r'Ship\s+Date\s+([\d/]+)',text,re.I);        # ship date (no campo en header, ignorar)
        try:
            m=re.search(r'TOTAL\s+([\d,]+\.\d+)',text,re.I); h.total=float(m.group(1).replace(',','')) if m else 0.0
        except: h.total=0.0
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            if not ln: continue
            parsed=self._parse_invoice_line(ln)
            if not parsed: continue
            is_mini='MINICARNS' in parsed['item_desc']
            sp='CARNATIONS'
            spb=10 if is_mini else 20   # 10U miniclavel, 20U clavel fancy
            label, colors = self._parse_grade_color(parsed['grade_color'])
            stems_total=parsed['stems']; total=parsed['total']; price=parsed['price_per_stem']
            btype=parsed['btype']
            n=len(colors)
            if n<=1:
                il=InvoiceLine(raw_description=ln,species=sp,variety=colors[0],grade='FANCY',origin='COL',
                               size=70,stems_per_bunch=spb,stems=stems_total,price_per_stem=price,
                               line_total=total,box_type=btype,label=label,provider_key='golden')
                lines.append(il)
            else:
                base=stems_total//n
                for i,color in enumerate(colors):
                    st=base if i<n-1 else stems_total-base*(n-1)
                    lt=round(st*price,2)
                    il=InvoiceLine(raw_description=ln,species=sp,variety=color,grade='FANCY',origin='COL',
                                   size=70,stems_per_bunch=spb,stems=st,price_per_stem=price,
                                   line_total=lt,box_type=btype,label=label,provider_key='golden')
                    lines.append(il)
        return h, lines

# ─── Latin Flowers (Hortensias) ──────────────────────────────────────────────
class LatinParser:
    """
    Latin Flowers Farms SAS CI — Hortensias (id_proveedor=6323).
    Artículos en BD: "HYDRANGEA {GRADO} {COLOR_ES} 60CM 1U LATIN"
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
        """Convierte descripción raw en variedad VeraBuy (porción tras 'HYDRANGEA ')."""
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
        grado = 'PREMIUM TEÑIDA' if is_tinted else 'PREMIUM'
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
            pm=re.search(r'(\d+)\s+(QB|HB)\s+(HYDRANGEA\s+[A-Z][A-Z\s\-]+?)\s+\w+\s+\d{4}\w*\s+(\d+)\s+(\d+)\s+([\d.]+)',ln,re.I)
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

# ─── Multiflora (Alstroemerias) ──────────────────────────────────────────────
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

# ─── Florsani (Gypsophila) ───────────────────────────────────────────────────
class FlorsaniParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'N[oº]\s*(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
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

# ─── Maxi ────────────────────────────────────────────────────────────────────
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
            pm=re.search(r'ROSE\s+([A-Z][A-Z\s]+?)\s+(\d{2})\s*Cm\s+(?:\d+\s+)?(\d+)\s+([\d,.]+)\s+(\d+)\s+([\d,.]+)',ln,re.I)
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

# ─── Mystic / Fiorentina / Stampsy ──────────────────────────────────────────
class MysticParser:
    """BOX TB [Box_code] VARIETY CAN/CANTID BUNCHES/BUNCHE LENGT STEMS PRICE/UNIT TOTAL
    - Box_code puede estar ausente (Fiorentina, Stampsy)
    - CAN = nº de ramos en la caja; BUNCHES = tallos por ramo (U); LENGT = tamaño CM
    - Algunas líneas llevan la variedad en la línea anterior (carry-forward)
    """
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+#\s*(\S+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'Date\s*:\s*([\d/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'A\.W\.B\.?\s*N[oº\s]*[:\s]*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        try:
            m=re.search(r'Total Invoice USD\s*\$?\s*([\d,.]+)',text,re.I)
            h.total=float(m.group(1).replace(',','')) if m else 0.0
        except: h.total=0.0
        lines=[]
        current_variety=''
        for ln in text.split('\n'):
            raw=ln; ln=ln.strip()
            # Patrón A: con código de caja corto (Mystic: "H VNG VARIETY CAN BUNCHES LENGT STEMS PRICE")
            # [A-Z]{2,5} no captura — solo casa con códigos tipo "VNG", no con palabras como "ORANGE"
            pm=re.search(r'\b(H|Q)\b\s+[A-Z]{2,5}\s+([A-Z][A-Z\s]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d,.]+)',ln)
            if not pm:
                # Patrón B: sin código de caja (Fiorentina, Stampsy)
                pm=re.search(r'\b(H|Q)\b\s+([A-Z][A-Z\s]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d,.]+)',ln)
            if pm:
                btype=pm.group(1); current_variety=pm.group(2).strip()
                try:
                    bunches=int(pm.group(3))  # CAN/CANTID = nº ramos
                    spb=int(pm.group(4))       # BUNCHES/BUNCHE = tallos por ramo (U)
                    sz=int(pm.group(5))        # LENGT = tamaño CM
                    stems=int(pm.group(6))     # STEMS = total tallos
                    price=float(pm.group(7).replace(',','.'))
                except: continue
                total=price*stems
                il=InvoiceLine(raw_description=raw,species='ROSES',variety=current_variety,
                               size=sz,stems_per_bunch=spb,bunches=bunches,stems=stems,
                               price_per_stem=price,line_total=total,box_type=btype)
                lines.append(il); continue
            # Carry-forward: línea H/Q con números pero sin variedad (variedad en línea anterior)
            pm2=re.search(r'\b(H|Q)\b\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d,.]+)',ln)
            if pm2 and current_variety:
                btype=pm2.group(1)
                try:
                    bunches=int(pm2.group(2)); spb=int(pm2.group(3))
                    sz=int(pm2.group(4)); stems=int(pm2.group(5))
                    price=float(pm2.group(6).replace(',','.'))
                except: continue
                total=price*stems
                il=InvoiceLine(raw_description=raw,species='ROSES',variety=current_variety,
                               size=sz,stems_per_bunch=spb,bunches=bunches,stems=stems,
                               price_per_stem=price,line_total=total,box_type=btype)
                lines.append(il); continue
            # Línea solo con variedad (antes de la línea de números)
            # Requiere sangría inicial — así excluimos cabeceras tipo "BOX TB Box code..."
            vm=re.match(r'^\s{5,}([A-Z][A-Z ]+[A-Z])\s{5,}',raw)
            if vm: current_variety=vm.group(1).strip()
        return h, lines

# ─── Prestige ────────────────────────────────────────────────────────────────
class PrestigeParser:
    """DESCRIPTION CODE HB/QB UNIT QTY UNIT_VALUE TOTAL"""
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+No\.?\s*(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'FECHA EXPEDICION\s*([\d\-]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'GU[IÍ]A\s+MASTER\s+([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'([A-Z][A-Z\s]+?)\s+ROSE\s+(\d{2})\s+CM\s+\w+\s+(\d+)\s+(\d+)\s+\$\s*([\d,]+)\s+([\d,.]+)',ln,re.I)
            if not pm:
                pm=re.search(r'([A-Z][A-Z\s]+?)\s+(\d{2})\s+CM\s+\w+\s+(\d+)\s+(\d+)\s+\$\s*([\d,.]+)\s+([\d,.]+)',ln,re.I)
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

# ─── Rosely ──────────────────────────────────────────────────────────────────
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
            pm=re.search(r'(\d+)\s+(TB|HB|QB)\s+([A-Z][A-Z\s]+?)\s+\*(\d+)\s+(\d{2})\s+\d+\s+(\d+)\s+\$\s*([\d.]+)\s+\$([\d.]+)',ln)
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

# ─── Condor (Hortensias) ─────────────────────────────────────────────────────
class CondorParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'PROFORMA\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'(\d{2}[A-Z]{3}\d{4})',text); h.date=m.group(1) if m else ''
        m=re.search(r'MAWB\s+No\.?\s*([\d\-]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'([\d.]+)\s+(QB|HB)\s+(HYD\s+[A-Z][A-Z\s]+?)\s*(?:\[[\d]+\])?\s+\d+\s+\d{4}\w*\s+(\d+)\s+([\d.]+)',ln,re.I)
            if not pm: continue
            btype=pm.group(2); desc=pm.group(3).strip().upper()
            # HYD WHITE → HYDRANGEA WHITE
            var=re.sub(r'^HYD\s+','HYDRANGEA ',desc)
            try: stems=int(pm.group(4)); price=float(pm.group(5))
            except: stems=0; price=0.0
            total=price*stems
            il=InvoiceLine(raw_description=ln,species='HYDRANGEAS',variety=var,origin='COL',
                           stems_per_bunch=35,stems=stems,price_per_stem=price,line_total=total,box_type=btype)
            lines.append(il)
        return h, lines

# ─── Malima / Starflowers (Gypsophila) ───────────────────────────────────────
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

# ─── Monterosa ───────────────────────────────────────────────────────────────
class MonterosaParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'INVOICE\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'DATE[:\s]+([\d\-/]+)',text,re.I); h.date=m.group(1) if m else ''
        m=re.search(r'M\s*A\s*W\s*B[:\s]*([\d\-/]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1)) if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'(?:QB|HB)\s+(?:\w+\s+)?([A-Z][A-Z\s\-]+?)\s+(\d{2})\s+(\d+)\s+(\d+)\s+([\d.]+)',ln)
            if not pm: continue
            var=pm.group(1).strip(); sz=int(pm.group(2))
            try: bunches=int(pm.group(3)); stems=int(pm.group(4)); total=float(pm.group(5))
            except: continue
            spb=stems//bunches if bunches else 25; price=total/stems if stems else 0.0
            il=InvoiceLine(raw_description=ln,species='ROSES',variety=var,
                           size=sz,stems_per_bunch=spb,bunches=bunches,stems=stems,
                           price_per_stem=price,line_total=total)
            lines.append(il)
        return h, lines

# ─── Secore ──────────────────────────────────────────────────────────────────
class SecoreParser:
    def parse(self, text:str, pdata:dict):
        h=InvoiceHeader(); h.provider_key=pdata['key']; h.provider_id=pdata['id']; h.provider_name=pdata['name']
        m=re.search(r'Invoice\s+N[oº]\s+(\d+)',text,re.I); h.invoice_number=m.group(1) if m else ''
        m=re.search(r'(\d+[-]\w+[-]\d+)',text); h.date=m.group(1) if m else ''
        m=re.search(r'AWB\s+([\d\s]+)',text,re.I); h.awb=re.sub(r'\s+','',m.group(1))[:12] if m else ''
        lines=[]
        for ln in text.split('\n'):
            ln=ln.strip()
            pm=re.search(r'ROSE\s+([A-Z][A-Z\s]+?)\s+(\d{2})\s+CM',ln,re.I)
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

# ─── Tessa ───────────────────────────────────────────────────────────────────
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
            pm=re.search(r'(HB|QB)\s+\w+\s+([A-Z][A-Z\s]+?)\s+(\d{2})\s+(\d+)\s+(\d+)\s+\$([\d.]+)\s+\$([\d.]+)',ln)
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

# ─── Uma (Gypsophila) ────────────────────────────────────────────────────────
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

# ─── Valle Verde ──────────────────────────────────────────────────────────────
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
            pm=re.search(r'(?:HB|QB|HB)\s+(?:\w+\s+)?([A-Z][A-Z\s]+?)\s+(\d{2})\s+\d+\s+(\d+)\s+(\d+)\s+([\d,]+)\s+([\d,]+)',ln)
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

# ─── Sayonara (Crisantemos / Pompons) ────────────────────────────────────────
class SayonaraParser:
    """
    C.I. Cultivos Sayonara SAS — Crisantemos, Limonium, Alstroemeria (id_proveedor=2166).
    Las líneas de Custom Pack/caja son agrupadores y se ignoran.
    Artículos: "CRISANTEMO {TIPO} {VARIEDAD} {COLOR} 70CM {BUNCH}U SAYONARA"
    """
    # (prefijo_factura, tipo_verabuy, bunch)  — ordenados más largo primero
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
    # Marcadores de líneas de caja/pack que se deben ignorar
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
            if self._SKIP_RE.search(ln): continue   # ignorar líneas de caja/pack

            # Buscar tipo de producto EN CUALQUIER POSICIÓN de la línea (puede haber N HB antes)
            parsed=None
            for prefix, _, _ in self._TYPE_MAP:
                type_m=re.search(re.escape(prefix), ln, re.I)
                if type_m:
                    # Extraer descripción desde donde empieza el tipo hasta CO- o números
                    desc_start=ln[type_m.start():]
                    desc_m=re.match(r'([A-Za-z][A-Za-z\s\-]+?)(?=\s+CO-|\s+\d|\s+HB\b|\s+QB\b)',desc_start)
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

# ─── Life Flowers ─────────────────────────────────────────────────────────────
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
            pm=re.search(r'\w+\s+([A-Z][a-zA-Z\s]{3,}?)\s+(\d{2})CM\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)',ln)
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
                pm2=re.search(r'HB\s+\S+\s+([A-Z][a-zA-Z\s]+?)\s+(\d{2})CM',ln)
                if pm2:
                    current_var=pm2.group(1).strip(); current_sz=int(pm2.group(2))
        return h, lines

# ──────────────────────────────────────────────────────────────────────────────
# MAPA DE FORMATOS → PARSERS
# ──────────────────────────────────────────────────────────────────────────────
FORMAT_PARSERS = {
    'cantiza'    : CantizaParser(),
    'agrivaldani': AgrivaldaniParser(),
    'brissas'    : BrissasParser(),
    'alegria'    : AlegriaParser(),
    'aluna'      : AlunaParser(),
    'daflor'     : DaflorParser(),
    'eqr'        : EqrParser(),
    'bosque'     : BosqueParser(),
    'colibri'    : ColibriParser(),
    'golden'     : GoldenParser(),
    'latin'      : LatinParser(),
    'multiflora' : MultifloraParser(),
    'florsani'   : FlorsaniParser(),
    'maxi'       : MaxiParser(),
    'mystic'     : MysticParser(),
    'prestige'   : PrestigeParser(),
    'rosely'     : RoselyParser(),
    'condor'     : CondorParser(),
    'malima'     : MalimaParser(),
    'monterosa'  : MonterosaParser(),
    'secore'     : SecoreParser(),
    'tessa'      : TessaParser(),
    'uma'        : UmaParser(),
    'valleverde' : ValleVerdeParser(),
    'sayonara'   : SayonaraParser(),
    'life'       : LifeParser(),
}

# ──────────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────────
def show_banner():
    print(f"""
  {C.BOLD}{C.CYAN}╔═══════════════════════════════════════════════════════╗
  ║     VERABUY — Entrenador Universal de Traductores   ║
  ╚═══════════════════════════════════════════════════════╝{C.RESET}""")

def find_pdfs():
    pdfs=[]
    for d in [SCRIPT_DIR]+([PDF_DIR] if PDF_DIR.exists() else []):
        for f in sorted(d.glob('*.pdf')):
            pdfs.append(str(f))
    return pdfs

def find_articulos_sql():
    for pat in ['articulos*.sql','*articulos*.sql']:
        for f in sorted(SCRIPT_DIR.glob(pat)):
            if f.stat().st_size>100_000: return str(f)
    return None

def show_result(header, lines, syns):
    tok=sum(1 for l in lines if l.match_status=='ok')
    tfail=sum(1 for l in lines if l.match_status=='sin_match')
    tusd=sum(l.line_total for l in lines)
    print(f"\n  {C.BOLD}{header.provider_name} — {header.invoice_number}{C.RESET}  |  {header.date}  |  AWB: {header.awb}")
    tbl=[]
    for i,l in enumerate(lines,1):
        st=f"{C.OK}✓ {l.match_method}{C.RESET}" if l.match_status=='ok' else f"{C.ERR}✗ SIN MATCH{C.RESET}"
        tbl.append([i,l.species[:4],l.variety[:20],f"{l.size}cm" if l.size else '-',l.stems_per_bunch,l.stems,f"${l.price_per_stem:.4f}" if l.price_per_stem else '-',f"${l.line_total:.2f}",l.label[:8],st])
    print(); print(tabulate(tbl,headers=['#','Sp','Variedad','Talla','St/B','Stems','$/St','Total','Label','Match'],tablefmt='simple'))
    uniq={l.match_key():l for l in lines}
    uok=sum(1 for l in uniq.values() if l.match_status=='ok')
    rate=(uok/len(uniq)*100) if uniq else 0
    col=C.OK if rate>=80 else C.WARN if rate>=50 else C.ERR
    bar=f"{'█'*int(rate/5)}{'░'*(20-int(rate/5))}"
    print(f"\n  {C.BOLD}Resumen:{C.RESET} {len(lines)} líneas | {sum(l.stems for l in lines)} stems | ${tusd:,.2f}")
    print(f"  Match:  {col}{bar} {rate:.0f}%{C.RESET} ({tok} OK, {tfail} sin match) | Sinónimos: {syns.count()}")
    return tok, tfail

def resolve_unmatched(provider_id, lines, art, syns):
    seen=set(); um=[]
    for l in lines:
        if l.match_status!='sin_match': continue
        k=l.match_key()
        if k not in seen: seen.add(k); um.append(l)
    if not um: print(f"\n  {C.OK}¡Todo con match!{C.RESET}"); return 0
    print(f"\n  {C.BOLD}RESOLVER {len(um)} LÍNEAS SIN MATCH{C.RESET}")
    print(f"  {C.DIM}[nº] candidato | [id] artículo directo | [n] nuevo | [Enter] saltar | [q] terminar{C.RESET}")
    res=0
    for i,l in enumerate(um,1):
        print(f"\n  {C.CYAN}[{i}/{len(um)}]{C.RESET} {C.BOLD}{l.expected_name()}{C.RESET}  {C.DIM}({l.species}, {l.label}, {l.farm}){C.RESET}")
        cands=art.fuzzy_search(l, threshold=0.4)
        if cands:
            for j,c in enumerate(cands,1):
                sc=C.OK if c['similitud']>=70 else C.WARN
                print(f"    {sc}{j}{C.RESET}. {c['nombre']} {C.DIM}(id={c['id']}, {c['similitud']}%){C.RESET}")
        else: print(f"    {C.DIM}Sin candidatos{C.RESET}")
        try: resp=input(f"  {C.MAG}→ {C.RESET}").strip()
        except: break
        if resp.lower()=='q': break
        elif resp=='': continue
        elif resp.lower()=='n':
            syns.add(provider_id,l,0,f"[NUEVO] {l.expected_name()}",'pendiente')
            print(f"    {C.WARN}Marcado para alta{C.RESET}")
        else:
            try:
                idx=int(resp)
                if cands and 1<=idx<=len(cands):
                    c=cands[idx-1]; syns.add(provider_id,l,c['id'],c['nombre'],'manual')
                    print(f"    {C.OK}✓ → {c['nombre']}{C.RESET}"); res+=1
                elif idx>0:
                    a=art.articulos.get(idx)
                    if a: syns.add(provider_id,l,a['id'],a['nombre'],'manual'); print(f"    {C.OK}✓ → {a['nombre']}{C.RESET}"); res+=1
                    else: print(f"    {C.ERR}id no encontrado{C.RESET}")
            except ValueError: pass
    return res

def auto_export(syns):
    if syns.count()==0: return
    EXPORT_DIR.mkdir(exist_ok=True)
    with open(EXPORT_DIR/'sinonimos_universal_LATEST.sql','w',encoding='utf-8') as f: f.write(syns.export_sql())

def process_pdfs(pdfs, art, syns, hist, matcher):
    n=0
    for pdf in pdfs:
        name=Path(pdf).name
        pdata=detect_provider(pdf)
        if not pdata:
            print(f"\n  {C.WARN}⚠ No reconocido:{C.RESET} {name}")
            continue
        fmt=pdata['fmt']
        parser=FORMAT_PARSERS.get(fmt)
        if not parser:
            print(f"\n  {C.WARN}⚠ Sin parser para formato '{fmt}':{C.RESET} {name}")
            continue
        try:
            header,lines=parser.parse(pdata['text'],pdata)
        except Exception as e:
            print(f"\n  {C.ERR}✗ Error parseando {name}: {e}{C.RESET}")
            continue
        if not lines:
            print(f"\n  {C.WARN}⚠ Sin líneas extraídas:{C.RESET} {name}")
            continue
        pid=pdata['id']
        lines=matcher.match_all(pid,lines)
        already=' (ya)' if hist.was_processed(header.invoice_number or name) else ''
        print(f"\n  {C.CYAN}{'━'*57}{C.RESET}\n  {C.BOLD}📄 {name}{C.RESET}{C.DIM}{already}{C.RESET}")
        ok,fail=show_result(header,lines,syns)
        hist.add(header.invoice_number or name,name,pdata['name'],header.total,len(lines),ok,fail)
        n+=1
        um=[l for l in lines if l.match_status=='sin_match']
        if um:
            uu=set(l.match_key() for l in um)
            try: resp=input(f"\n  {C.MAG}¿Resolver {len(uu)} sin match? [S/n/q]: {C.RESET}").strip().lower()
            except: break
            if resp=='q': break
            elif resp!='n':
                r=resolve_unmatched(pid,lines,art,syns)
                if r>0:
                    lines=matcher.match_all(pid,lines)
                    show_result(header,lines,syns)
                    hist.add(header.invoice_number or name,name,pdata['name'],header.total,len(lines),
                              sum(1 for l in lines if l.match_status=='ok'),
                              sum(1 for l in lines if l.match_status=='sin_match'))
    auto_export(syns)
    print(f"\n  {C.OK}Procesadas {n} facturas.{C.RESET}")

def show_stats(syns, hist):
    print(f"\n  {C.BOLD}ESTADÍSTICAS{C.RESET}\n  {'─'*50}")
    print(f"  Sinónimos totales: {syns.count()}")
    if hist.entries:
        tbl=[]
        for num,e in sorted(hist.entries.items()):
            r=(e['ok']/e['lineas']*100) if e['lineas']>0 else 0
            cl=C.OK if r>=80 else C.WARN if r>=50 else C.ERR
            tbl.append([num[:20],e['provider'][:20],f"${e['total_usd']:,.2f}",e['lineas'],e['ok'],e['sin_match'],f"{cl}{r:.0f}%{C.RESET}",e['fecha']])
        print(); print(tabulate(tbl,headers=['Factura','Proveedor','Total','Lín','OK','Fail','Match','Fecha'],tablefmt='simple'))

def setup():
    sql=find_articulos_sql()
    if not sql:
        print(f"\n  {C.WARN}No se encontró articulos*.sql{C.RESET}")
        try: sql=input(f"  {C.MAG}Ruta: {C.RESET}").strip().strip('"').strip("'")
        except: return None
        if not sql or not os.path.exists(sql): return None
    art=ArticulosLoader()
    print(f"  {C.DIM}Cargando {Path(sql).name}...{C.RESET}",end='',flush=True)
    n=art.load_from_sql(sql)
    rosas=len(art.rosas_ec)
    print(f" {C.OK}{n:,} artículos, {rosas} rosas EC{C.RESET}")
    return art

def main():
    clear(); show_banner(); print()
    art=setup()
    if not art: input("\n  No se cargaron artículos. Enter para salir..."); return
    syns=SynonymStore(); hist=History(); matcher=Matcher(art,syns)
    pdfs=find_pdfs()
    detected=[(p, detect_provider(p)) for p in pdfs]
    known=[(p,d) for p,d in detected if d]
    unknown=[p for p,d in detected if not d]
    print(f"  {C.DIM}Sinónimos: {syns.count()} | PDFs detectados: {len(known)}/{len(pdfs)}{C.RESET}")
    if unknown:
        print(f"  {C.WARN}Sin detectar ({len(unknown)}):{C.RESET}")
        for p in unknown[:5]: print(f"    {C.DIM}📄 {Path(p).name}{C.RESET}")
    provs_found={}
    for p,d in known: provs_found[d['name']]=provs_found.get(d['name'],0)+1
    for pn,cnt in sorted(provs_found.items()): print(f"    {C.DIM}✓ {pn}: {cnt} PDF(s){C.RESET}")

    while True:
        print(f"\n  {C.BOLD}{'─'*47}{C.RESET}\n  {C.BOLD}¿Qué quieres hacer?{C.RESET}\n")
        print(f"    {C.CYAN}1{C.RESET}  Procesar todos los PDFs")
        print(f"    {C.CYAN}2{C.RESET}  Procesar un proveedor concreto")
        print(f"    {C.CYAN}3{C.RESET}  Procesar un PDF concreto")
        print(f"    {C.CYAN}4{C.RESET}  Estadísticas e historial")
        print(f"    {C.CYAN}5{C.RESET}  Exportar SQL para la BD")
        print(f"    {C.CYAN}6{C.RESET}  Recargar artículos")
        print(f"    {C.CYAN}0{C.RESET}  Salir")
        try: ch=input(f"\n  {C.MAG}→ {C.RESET}").strip()
        except: break

        if ch=='1':
            pdfs=find_pdfs()
            if not pdfs: print(f"\n  {C.WARN}No hay PDFs{C.RESET}")
            else: process_pdfs(pdfs,art,syns,hist,matcher)
        elif ch=='2':
            provs={}
            for p in find_pdfs():
                d=detect_provider(p)
                if d: provs.setdefault(d['name'],[]).append(p)
            if not provs: print(f"\n  {C.WARN}Sin PDFs detectados{C.RESET}"); continue
            print(f"\n  {C.BOLD}Proveedores:{C.RESET}")
            plist=sorted(provs.items())
            for i,(pn,fps) in enumerate(plist,1): print(f"    {C.CYAN}{i}{C.RESET}. {pn} ({len(fps)} PDF)")
            try: r=input(f"\n  {C.MAG}Nº: {C.RESET}").strip()
            except: continue
            try:
                idx=int(r)-1
                if 0<=idx<len(plist): process_pdfs(plist[idx][1],art,syns,hist,matcher)
            except: pass
        elif ch=='3':
            pdfs=find_pdfs()
            if not pdfs: continue
            print(f"\n  {C.BOLD}PDFs:{C.RESET}")
            for i,p in enumerate(pdfs,1): print(f"    {C.CYAN}{i}{C.RESET}. {Path(p).name}")
            try: r=input(f"\n  {C.MAG}Nº: {C.RESET}").strip()
            except: continue
            try:
                idx=int(r)-1
                if 0<=idx<len(pdfs): process_pdfs([pdfs[idx]],art,syns,hist,matcher)
            except: pass
        elif ch=='4': show_stats(syns,hist)
        elif ch=='5':
            EXPORT_DIR.mkdir(exist_ok=True)
            sql=syns.export_sql()
            ts=f"{datetime.now():%Y%m%d_%H%M}"
            for fp in [EXPORT_DIR/f"sinonimos_{ts}.sql", EXPORT_DIR/'sinonimos_universal_LATEST.sql']:
                with open(fp,'w',encoding='utf-8') as f: f.write(sql)
            print(f"\n  {C.OK}Exportado → exportar/sinonimos_universal_LATEST.sql{C.RESET}")
        elif ch=='6': art=setup() or art; matcher=Matcher(art,syns)
        elif ch=='0': break

    if syns.count()>0: auto_export(syns); print(f"\n  {C.OK}Sinónimos guardados.{C.RESET}")
    print(f"\n  {C.DIM}¡Hasta luego!{C.RESET}\n")

if __name__=='__main__':
    main()

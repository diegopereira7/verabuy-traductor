from __future__ import annotations

from src.parsers.cantiza import CantizaParser
from src.parsers.agrivaldani import AgrivaldaniParser
from src.parsers.colibri import ColibriParser
from src.parsers.golden import GoldenParser
from src.parsers.latin import LatinParser
from src.parsers.mystic import MysticParser
from src.parsers.alegria import AlegriaParser
from src.parsers.sayonara import SayonaraParser
from src.parsers.life import LifeParser
from src.parsers.otros import (
    BrissasParser,
    AlunaParser,
    DaflorParser,
    EqrParser,
    BosqueParser,
    MultifloraParser,
    FlorsaniParser,
    MaxiParser,
    PrestigeParser,
    RoselyParser,
    CondorParser,
    MalimaParser,
    MonterosaParser,
    SecoreParser,
    TessaParser,
    UmaParser,
    ValleVerdeParser,
    VerdesEstacionParser,
    FloraromaParser,
    GardaParser,
    UtopiaParser,
)

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
    'verdesestacion': VerdesEstacionParser(),
    'sayonara'   : SayonaraParser(),
    'life'       : LifeParser(),
    'floraroma'  : FloraromaParser(),
    'garda'      : GardaParser(),
    'utopia'     : UtopiaParser(),
}

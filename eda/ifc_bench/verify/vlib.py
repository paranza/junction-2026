import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Shared helpers for the skeptic pass (own code, not the analyst's).
import json, re, functools
import ifcopenshell
import ifcopenshell.util.element as ue
import ifcopenshell.util.unit as uu

D = _DATA + '/data/ifc_bench/'
WD = _ROOT + '/eda/ifc_bench/verify/'
SHORT = {'ac20': 'ac20_arc', 'dh': 'digital_hub_arc', 'duplex': 'duplex_arc',
         'fantasy': 'fantasy_office_building_3_arc', 'hitos': 'hitos_arc'}

@functools.lru_cache(None)
def load(m):
    return ifcopenshell.open(D + SHORT.get(m, m) + '.ifc')

def Q():
    return [json.loads(l) for l in open(WD + 'ib_q.jsonl')]

def storey(e):
    """Nearest IfcBuildingStorey above e via containment or aggregation."""
    seen = 0
    x = e
    while x is not None and seen < 10:
        if x.is_a('IfcBuildingStorey'):
            return x
        c = ue.get_container(x)
        if c is None:
            c = ue.get_aggregate(x)
        x = c
        seen += 1
    return None

def sname(e):
    s = storey(e)
    return s.Name if s else None

def psets(e):
    return ue.get_psets(e)

def flat_props(e, include_type=True):
    """{(pset, prop): value} from instance (and type if requested, instance wins)."""
    out = {}
    if include_type:
        t = ue.get_type(e)
        if t is not None:
            for ps, d in ue.get_psets(t).items():
                for k, v in d.items():
                    if k != 'id':
                        out[(ps, k)] = v
    for ps, d in ue.get_psets(e).items():
        for k, v in d.items():
            if k != 'id':
                out[(ps, k)] = v
    return out

def tname(e):
    t = ue.get_type(e)
    return t.Name if t is not None else None

def r1(x):
    return None if x is None else round(x + 1e-9, 1)

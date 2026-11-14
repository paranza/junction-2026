# Own timing: tessellate all IfcProduct with geometry (except openings/annotations/spaces kept) per model, 8 threads.
import sys, time
sys.path.insert(0, '.')
from vlib import *
import ifcopenshell.geom
for m in ['duplex', 'ac20', 'dh', 'hitos', 'fantasy']:
    f = load(m)
    s = ifcopenshell.geom.settings()
    s.set('use-world-coords', True)
    els = [e for e in f.by_type('IfcProduct') if e.Representation is not None and not e.is_a('IfcOpeningElement') and not e.is_a('IfcAnnotation')]
    t = time.perf_counter()
    it = ifcopenshell.geom.iterator(s, f, 8, include=els)
    n = 0
    if it.initialize():
        while True:
            n += 1
            if not it.next():
                break
    print(m, 'products', len(els), 'shapes', n, 'seconds', round(time.perf_counter() - t, 1), flush=True)

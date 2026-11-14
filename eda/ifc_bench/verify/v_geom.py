# Geometry helpers: mesh volume and plan footprint (own code).
import numpy as np
import ifcopenshell.geom
from shapely.geometry import Polygon
from shapely.ops import unary_union

S = ifcopenshell.geom.settings()
S.set('use-world-coords', True)

def mesh(e):
    sh = ifcopenshell.geom.create_shape(S, e)
    v = np.array(sh.geometry.verts).reshape(-1, 3)
    f = np.array(sh.geometry.faces).reshape(-1, 3)
    return v, f

def volume(e):
    v, f = mesh(e)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return abs(np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6.0)

def footprint(e):
    v, f = mesh(e)
    tris = [Polygon(v[t][:, :2]) for t in f]
    tris = [t for t in tris if t.is_valid and t.area > 1e-9]
    return unary_union(tris)

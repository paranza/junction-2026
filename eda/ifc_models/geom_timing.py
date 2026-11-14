# Time a full tessellation pass (all products) of one IFC with the multi-threaded geometry iterator.
import sys, time, os, resource, multiprocessing
import ifcopenshell, ifcopenshell.geom
p = sys.argv[1]; t0 = time.time(); f = ifcopenshell.open(p); t1 = time.time()
st = ifcopenshell.geom.settings()
it = ifcopenshell.geom.iterator(st, f, multiprocessing.cpu_count())
n = 0
if it.initialize():
    while True:
        n += 1
        if not it.next(): break
t2 = time.time()
print(os.path.basename(p), "open %.1fs, tessellate %d products %.1fs, peak RSS %.0f MB, cpus %d" % (t1 - t0, n, t2 - t1, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, multiprocessing.cpu_count()))

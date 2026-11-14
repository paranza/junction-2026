"""Tessellate all products (world coords), record z-range per GUID; time + memory."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, time, resource, pickle, multiprocessing, numpy as np, ifcopenshell, ifcopenshell.geom
DS=_DATA + "/data/ifc_models/"
fn=sys.argv[1]; nthreads=int(sys.argv[2])
t0=time.time(); f=ifcopenshell.open(DS+fn); t1=time.time()
s=ifcopenshell.geom.settings(); s.set("use-world-coords",True)
it=ifcopenshell.geom.iterator(s,f,nthreads)
z={}; n=0; t2=time.time()
if it.initialize():
    while True:
        sh=it.get()
        v=np.array(sh.geometry.verts).reshape(-1,3)
        if len(v): z[sh.guid]=(float(v[:,2].min()),float(v[:,2].max()),float(v[:,0].min()),float(v[:,0].max()),float(v[:,1].min()),float(v[:,1].max()))
        n+=1
        if not it.next(): break
t3=time.time()
print(fn,"threads",nthreads,"open %.2fs"%(t1-t0),"tessellate %.1fs"%(t3-t2),"shapes",n,"maxrss MB %.0f"%(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6))
pickle.dump(z,open(f"zr_{fn}.pkl","wb"))

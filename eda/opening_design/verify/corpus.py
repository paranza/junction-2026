import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, glob, os, collections, ezdxf
R=_DATA + "/data/opening_design/"
pdfs=sorted(glob.glob(R+"**/*.pdf",recursive=True)); dwgs=sorted(glob.glob(R+"**/*.dwg",recursive=True))
pages=0; rot=collections.Counter(); notext=0; ann=0; annpages=0; anntext=0; hollow=[]; sizes=collections.Counter()
for p in pdfs:
    try: d=pymupdf.open(p)
    except Exception as e: print("OPENFAIL",p,e); continue
    for pg in d:
        pages+=1; rot[pg.rotation]+=1
        t=pg.get_text()
        if len(t.strip())==0: notext+=1
        a=list(pg.annots() or [])
        if a: annpages+=1; ann+=len(a); anntext+=sum(1 for x in a if (x.info.get("content") or "").strip())
        if "HOLLOW" in t.upper() or "HOLLOW" in " ".join((x.info.get("content") or "") for x in a).upper(): hollow.append((os.path.relpath(p,R),pg.number))
        w,h=sorted((pg.rect.width/72,pg.rect.height/72)); sizes[f"{round(w)}x{round(h)}"]+=1
print("pdfs",len(pdfs),"pages",pages,"rotation",dict(rot),"no-text pages",notext,"annots",ann,"on pages",annpages,"with text",anntext)
print("sizes",sizes.most_common())
print("HOLLOW pages",hollow)
for p in dwgs:
    hdr=open(p,"rb").read(6)
    try: ezdxf.readfile(p); r="OK"
    except Exception as e: r=type(e).__name__
    print("DWG",hdr,r,os.path.basename(p)[:60])

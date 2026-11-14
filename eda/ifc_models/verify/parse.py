"""Independent question parser for ifc_models templates (EN/ET/DA/DE)."""
import re, pandas as pd
Q=r"(?:'(?P<a>.+?)'|„(?P<b>.+?)“)"
def quoted(s):
    return [m.group("a") or m.group("b") for m in re.finditer(Q,s)]
ELEM={ # word -> canonical
 "doors":"door","døre":"door","ust":"door","türen":"door",
 "windows":"window","vinduer":"window","akent":"window","fenster":"window",
 "rooms (spaces)":"space","rum":"space","ruumi":"space","räume":"space",
 "walls":"wall","vægge":"wall","seina":"wall","wände":"wall",
 "columns":"column","søjler":"column","posti":"column",
 "stairs":"stair","trapper":"stair","treppi":"stair","treppen":"stair",
 "beams":"beam","bjælker":"beam","tala":"beam","träger":"beam",
 "sanitary fixtures":"sanitary",
}
def lang(s):
    if s.startswith(("What","How")): return "en"
    if s.startswith(("Kui","Mitu")): return "et"
    if s.startswith(("Hvad","Hvor")): return "da"
    if s.startswith("Wie"): return "de"
    return "?"
def parse(s):
    lo=s.lower(); qs=quoted(s); L=lang(s)
    d={"lang":L,"quoted":qs}
    # room area (single room)
    if re.search(r"net floor area of the room|ruumi .*netopõrandapind korrusel|nettoarealet af rummet",lo):
        d.update(fam="room_area",room=qs[0],storey=qs[1]); return d
    if re.search(r"total net floor area of all rooms|samlede nettoareal af alle rum|kõigi ruumide netopõrandapind kokku",lo):
        d.update(fam="storey_space_area",storey=qs[0]); return d
    if re.search(r"net side area|nettosideareal|netto-seitenfläche",lo):
        d.update(fam="wall_side_area",storey=qs[0]); return d
    if re.search(r"total length of all walls|samlede længde af alle vægge|wie lang sind alle wände",lo):
        d.update(fam="wall_length",storey=qs[0]); return d
    if re.search(r"net volume|nettovolumen|netto-volumen",lo):
        if re.search(r"slabs|dæk og plader|decken und bodenplatten",lo): d.update(fam="slab_volume",storey=qs[0]); return d
        if re.search(r"walls|vægge|wände",lo): d.update(fam="wall_volume",storey=qs[0]); return d
    m=re.match(r"(?:how many|hvor mange|mitu|wie viele) (.+?) (?:are shown|are there|er vist|er der|on näidatud|on mudelis|sind im grundriss|enthält das modell)",lo)
    if m:
        w=m.group(1); el=ELEM.get(w)
        model=bool(re.search(r"in the model|i modellen|on mudelis|enthält das modell",lo))
        d.update(fam="model_count" if model else "storey_count",elem=el,word=w)
        if model: d["model"]=qs[0]
        else: d["storey"]=qs[0]
        return d
    d["fam"]="UNPARSED"; return d
if __name__=="__main__":
    q=pd.read_pickle("q.pkl")
    P=pd.DataFrame([parse(s) for s in q.question])
    q=pd.concat([q,P],axis=1)
    print(q.fam.value_counts()); print(q.lang.value_counts())
    print(q[q.fam.str.contains("count")].groupby(["fam","word","elem"],dropna=False).size())
    assert (q.fam!="UNPARSED").all()
    assert q[q.fam.str.contains("count")].elem.notna().all()
    q.to_pickle("qp.pkl")

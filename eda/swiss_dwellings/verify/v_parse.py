import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# My own multilingual question parser -> (family, param). Used by all later checks.
import json, re
D = _DATA + ""

def lang_of(q):
    if q.startswith(("How ", "What ")): return "en"
    if q.startswith(("Wie ",)): return "de"
    if q.startswith(("Combien", "Quelle")): return "fr"
    if q.startswith(("Quant", "Qual")): return "it"
    return "?"

def quoted(q):
    # label between guillemets (strip inner spaces) or between the first and LAST apostrophe-quote pair
    m = re.search(r"«\s*(.*?)\s*»", q)
    if m: return m.group(1)
    m = re.search(r"labelled '(.*)' (?:are|on)", q)
    if m: return m.group(1)
    m = re.search(r"\('(.*)'\)", q)
    if m: return m.group(1)
    return None

def parse(q):
    ql = q.lower()
    lab = quoted(q)
    room = re.search(r"\b(U?\d+\.\d+)\b", q)
    apt = re.search(r"(?:apartment|appartement|appartamento|Wohnung) ([A-Z0-9]+)\b", q)
    is_area = "m²" in q
    if is_area:
        if apt: return ("area_apartment", apt.group(1))
        if room and lab is not None: return ("area_room", (room.group(1), lab))
        if lab is not None: return ("area_label_total", lab)
        return ("area_total_indoor", None)
    if lab is not None: return ("count_label", lab)
    for fam, keys in [("count_apartments", ["apartment", "wohnungen", "appartements", "appartamenti"]),
                      ("count_doors", ["door", "türen", "portes", "porte "]),
                      ("count_windows", ["window", "fenster", "fenêtres", "finestre"]),
                      ("count_wc", ["toilets", "wcs", "wc "]),
                      ("count_washbasins", ["washbasin", "lavabo", "lavabi"]),
                      ("count_bathtubs", ["bathtub", "badewannen", "baignoires", "vasche"]),
                      ("count_showers", ["shower", "duschen", "douches", "docce"])]:
        if any(k in ql for k in keys): return (fam, None)
    return ("?", None)

def load():
    rows = [json.loads(l) for l in open(D + "/questions.jsonl", encoding="utf-8")]
    out = []
    for i, r in enumerate(rows):
        if not r["path"].startswith("data/swiss_dwellings/"): continue
        fam, p = parse(r["question"])
        out.append(dict(idx=i, path=r["path"], stem=r["path"].split("/")[-1][:-4], q=r["question"],
                        ans=r["answer"], type=r["type"], lang=lang_of(r["question"]), fam=fam, param=p))
    return out

if __name__ == "__main__":
    import collections
    qs = load()
    print(collections.Counter((q["lang"]) for q in qs))
    print(collections.Counter(q["fam"] for q in qs if q["lang"] == "en"))
    print("unparsed", [q["q"] for q in qs if q["fam"] == "?"][:5])
    # pairing independent of order: key (stem, fam, param) per language
    en = collections.defaultdict(list); loc = collections.defaultdict(list)
    for q in qs:
        (en if q["lang"] == "en" else loc)[(q["stem"], q["fam"], json.dumps(q["param"]))].append(q)
    # local labels are in local language, english questions quote the same drawing label, so param equal
    ok = mism = 0; unmatched = []
    for k, v in en.items():
        w = loc.get(k, [])
        if len(v) != 1 or len(w) != 1: unmatched.append((k, len(v), len(w))); continue
        if v[0]["ans"] == w[0]["ans"]: ok += 1
        else: mism += 1
    print("pairs equal answer", ok, "mismatch", mism, "unmatched keys", len(unmatched), unmatched[:5])
    # local language per file
    lf = {}
    for q in qs:
        if q["lang"] != "en": lf.setdefault(q["stem"], set()).add(q["lang"])
    print("files by local lang", collections.Counter(tuple(sorted(v))[0] if len(v)==1 else "multi" for v in lf.values()))
    # consecutive-line pairing
    cons = sum(1 for a, b in zip(qs[::2], qs[1::2]) if a["lang"]=="en" and b["lang"]!="en" and a["path"]==b["path"] and a["ans"]==b["ans"])
    print("consecutive en/local pairs with same path+answer", cons, "of", len(qs)//2)
    # duplicates of exact question text on same file
    dup = collections.Counter((q["stem"], q["q"]) for q in qs)
    print("duplicate (file, question) rows", sum(1 for v in dup.values() if v > 1))
    # area answer decimals
    import decimal
    decs = collections.Counter(len(str(q["ans"]).split(".")[1]) if "." in str(q["ans"]) else 0 for q in qs if q["type"]=="area")
    print("area answer decimals", decs)

# Is the room-number prefix a usable proxy for apartment membership? What are unnumbered room-styled polygons,
# and would counting them change the floor total?
import sys, os, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_pdf, v_parse, v_local, v_eval
stems = v_local.stems("pdf")
qs = [q for q in v_parse.load() if q["lang"] == "en" and q["fam"] in ("area_apartment", "area_total_indoor")]
C = collections.Counter()
for s in stems:
    m = v_eval.model(s)
    # prefix -> set of residential unit letters
    pre = collections.defaultdict(set)
    for r in m["rooms"]:
        tags = [t for t in (r["unit"]["tags"] if r["unit"] else []) if v_eval.res_tag(t)]
        pre[r["num"].rsplit(".", 1)[0]].add(tags[0].split()[-1] if tags else "-")
    C["floors"] += 1
    C["floors_prefix_maps_to_one_unit"] += all(len(v) == 1 for v in pre.values())
    # unnumbered room-styled polygons (grey 0.541 stroke) not used by any numbered room
    used = {id(r["poly"]) for r in m["rooms"]}
    un = [p for p in m["polys"] if id(p) not in used]
    for p in un: C[("unnumbered_fill", v_eval.FILL.get(p["fill"], p["fill"]))] += 1
    extra = sum(p["g"].area for p in un if v_eval.FILL.get(p["fill"]) in ("common", "room")) * m["mpp"] ** 2
    for q in [q for q in qs if q["stem"] == s and q["fam"] == "area_total_indoor"]:
        base = v_eval.predict(q["fam"], None, m)["all_but_outdoor_fill"]
        C["total_ok_with_unnumbered_added"] += abs(base + extra - q["ans"]) <= 0.02 * q["ans"]
        C["floors_with_unnumbered_indoor"] += extra > 0
print(dict(C))

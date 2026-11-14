# Evaluate my independent PDF model (and variants of each convention) against questions.jsonl, English questions.
import sys, os, collections, json, re, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_pdf, v_fixtures, v_parse, v_local
import pandas as pd

OUT_LABELS = {"Balkon", "Balcon", "Balcone", "Loggia", "Terrasse", "Terrazza", "Terrazzo", "Veranda", "Sitzplatz", "Gartensitzplatz", "Wintergarten", "Patio"}
FILL = {1.0: "room", 0.953: "common", 0.894: "outdoor", 0.812: "shaft"}

def model(stem):
    m = v_pdf.load(stem)
    fx = v_fixtures.classify(m)
    m["fx"] = fx
    m["fxc"] = collections.Counter(); [m["fxc"].update({f["kind"]: f["mult"]}) for f in fx]
    m["fxc_distinct"] = collections.Counter(f["kind"] for f in fx)
    return m

def res_tag(t): return bool(re.match(r"^(App\.|Whg\.|Appart\.|Apt\.)\s*[A-Z]+$", t))

def predict(fam, param, m):
    rooms = m["rooms"]
    cat = lambda r: FILL.get(r["fill"], "?")
    P = {}
    if fam == "count_label":
        P["exact"] = sum(r["label"] == param for r in rooms)
        P["casefold_prefix"] = sum(bool(r["label"]) and r["label"].casefold().startswith(param.casefold()) for r in rooms)
        P["in_unit_only"] = sum(r["label"] == param and r["unit"] is not None for r in rooms)
    elif fam == "count_apartments":
        P["res_tags"] = sum(res_tag(t["t"]) for t in m["tags"])
        P["all_tags"] = len(m["tags"])
        P["all_outlines"] = len(m["units"])
        P["tagged_outlines"] = sum(1 for u in m["units"] if u["tags"])
    elif fam == "count_doors":
        P["frames_all"] = len(m["doors"]); P["frames_distinct"] = len(m["door_keys"])
    elif fam == "count_windows":
        P["all"] = m["fxc"].get("window", 0); P["distinct"] = m["fxc_distinct"].get("window", 0)
    elif fam in ("count_wc", "count_washbasins", "count_bathtubs", "count_showers"):
        k = {"count_wc": "wc", "count_washbasins": "washbasin", "count_bathtubs": "bathtub", "count_showers": "shower"}[fam]
        P["all"] = m["fxc"].get(k, 0); P["distinct"] = m["fxc_distinct"].get(k, 0)
    elif fam == "area_room":
        num, lab = param
        rr = [r for r in rooms if r["num"] == num]
        r = rr[0] if rr else None
        P["net"] = round(r["net"], 2) if r and r["net"] is not None else None
        P["raw"] = round(r["raw"], 2) if r and r["raw"] is not None else None
        P["printed_only"] = r["printed"] if r else None
        P["label_matches"] = (r["label"] == lab) if r else None
    elif fam == "area_label_total":
        P["net"] = round(sum(r["net"] for r in rooms if r["label"] == param and r["net"]), 2)
        P["raw"] = round(sum(r["raw"] for r in rooms if r["label"] == param and r["raw"]), 2)
        pr = [r["printed"] for r in rooms if r["label"] == param]
        P["printed_only"] = round(sum(pr), 2) if pr and all(p is not None for p in pr) else None
    elif fam == "area_apartment":
        inu = [r for r in rooms if r["unit"] is not None and any(t.split()[-1] == param and res_tag(t) for t in r["unit"]["tags"])]
        P["net_excl_outdoor_fill"] = round(sum(r["net"] for r in inu if cat(r) != "outdoor"), 2)
        P["net_excl_outdoor_label"] = round(sum(r["net"] for r in inu if r["label"] not in OUT_LABELS), 2)
        P["net_incl_outdoor"] = round(sum(r["net"] for r in inu), 2)
        P["raw_excl_outdoor_fill"] = round(sum(r["raw"] for r in inu if cat(r) != "outdoor"), 2)
        P["net_excl_outdoor_and_unlabelled"] = round(sum(r["net"] for r in inu if cat(r) != "outdoor" and r["label"]), 2)
    elif fam == "area_total_indoor":
        ok = [r for r in rooms if r["net"] is not None]
        P["all_but_outdoor_fill"] = round(sum(r["net"] for r in ok if cat(r) != "outdoor"), 2)
        P["all_but_outdoor_label"] = round(sum(r["net"] for r in ok if r["label"] not in OUT_LABELS), 2)
        P["excl_common_fill"] = round(sum(r["net"] for r in ok if cat(r) == "room"), 2)
        P["excl_lift_labels"] = round(sum(r["net"] for r in ok if cat(r) != "outdoor" and not (r["label"] or "").lower().startswith(("lift", "ascens", "aufzug"))), 2)
        P["excl_unlabelled"] = round(sum(r["net"] for r in ok if cat(r) != "outdoor" and r["label"]), 2)
        P["raw_all_but_outdoor"] = round(sum(r["raw"] for r in ok if cat(r) != "outdoor"), 2)
        P["in_units_only"] = round(sum(r["net"] for r in ok if cat(r) != "outdoor" and r["unit"] is not None), 2)
    return P

def ok(fam, pred, gold):
    if pred is None or isinstance(pred, bool): return False
    if fam.startswith("count"): return int(pred) == int(gold)
    return abs(pred - gold) <= 0.02 * abs(gold)

if __name__ == "__main__":
    stems = sys.argv[1:] or v_local.stems("pdf")
    qs = [q for q in v_parse.load() if q["lang"] == "en" and q["stem"] in set(stems)]
    t0 = time.time(); M = {s: model(s) for s in stems}; dt = time.time() - t0
    rows = []
    for q in qs:
        P = predict(q["fam"], q["param"], M[q["stem"]])
        for k, v in P.items():
            rows.append(dict(stem=q["stem"], fam=q["fam"], param=json.dumps(q["param"], ensure_ascii=False), gold=q["ans"], variant=k, pred=v, ok=ok(q["fam"], v, q["ans"])))
    df = pd.DataFrame(rows)
    df.to_csv(f"eval_pdf_{len(stems)}files.csv", index=False)
    print(f"files {len(stems)}  english questions {len(qs)}  parse time {dt:.1f}s ({1000*dt/len(stems):.0f} ms/file)")
    g = df[df.variant != "label_matches"].groupby(["fam", "variant"]).ok.agg(["sum", "count"])
    print(g.to_string())

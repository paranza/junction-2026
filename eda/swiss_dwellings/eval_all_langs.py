"""Score the PDF-only solver on all 2,358 questions (en, de, fr, it) with a multilingual template parser."""
import os, re, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_solver as S

WD = os.path.dirname(os.path.abspath(__file__))
Q = r"(?:'(.+)'(?= are there| on this floor|\))|«\s*(.+?)\s*»)"  # 'x' (greedy: labels contain apostrophes) or « x » (French adds spaces)
RULES = [  # (family, regex) in priority order; group 1 = label / room / apartment id
    ("area_total_indoor", r"(numbered indoor rooms|nummerierten Innenräume|pièces intérieures numérotées|locali interni numerati)"),
    ("area_apartment", r"(?:apartment|Wohnung|l'appartement|dell'appartamento) ([A-Z]+)\b"),
    ("area_room", r"(?:room|Raum|la pièce|del locale) ([A-Z]?\d*\.\d+) \("),
    ("area_label_total", r"(?:total net area|gesamte Nettofläche|surface nette totale|superficie netta totale).*?" + Q),
    ("count_label", r"(?:rooms labelled|Räume mit der Bezeichnung|pièces portant la désignation|locali con la denominazione) " + Q),
    ("count_apartments", r"(apartments|Wohnungen|appartements|appartamenti)"),
    ("count_doors", r"(doors|Türen|portes|porte \()"),
    ("count_windows", r"(windows|Fenster|fenêtres|finestre)"),
    ("count_wc", r"(toilets|WCs? sind|WC sont|WC sono)"),
    ("count_washbasins", r"(washbasins|Lavabos|lavabos|lavabi)"),
    ("count_bathtubs", r"(bathtubs|Badewannen|baignoires|vasche da bagno)"),
    ("count_showers", r"(showers|Duschen|douches|docce)"),
]


def parse(q):
    for fam, rx in RULES:
        m = re.search(rx, q)
        if m: return fam, next(g for g in m.groups() if g is not None).strip()
    return None, None


def to_en(fam, arg):
    """Re-express the parsed question in the English template the solver understands."""
    return {"count_label": f"How many rooms labelled '{arg}' are there on this floor?",
            "area_room": f"What is the net floor area of room {arg} ('x') in m²?",
            "area_label_total": f"What is the total net area in m² of all rooms labelled '{arg}' on this floor?",
            "area_apartment": f"apartment {arg} in m²"}.get(fam, "")


if __name__ == "__main__":
    df = pd.read_csv(f"{WD}/questions_swiss.csv")
    cache, out = {}, []
    for _, r in df.iterrows():
        fam, arg = parse(r.question)
        name = os.path.basename(r.path)[:-4]
        if name not in cache: cache[name] = S.load(name)
        pred = S.answer(fam, to_en(fam, arg), cache[name]) if fam else None
        out.append((fam, arg, pred, S.correct(fam, pred, r.answer) if fam else False))
    df[["family", "arg", "pred", "ok"]] = pd.DataFrame(out, index=df.index)
    print("unparsed:", df.family.isna().sum())
    print(df.pivot_table(index="family", columns="lang", values="ok", aggfunc=lambda s: f"{s.sum()}/{len(s)}").to_string())
    print("TOTAL", df.ok.sum(), "/", len(df))
    # area precision
    a = df[df.family.str.startswith("area", na=False)].copy()
    a["relerr"] = (a.pred - a.answer).abs() / a.answer
    a["abserr"] = (a.pred - a.answer).abs()
    print(a.groupby("family")[["abserr", "relerr"]].agg(["median", "max"]).to_string())
    print("area answers exactly equal at 2 decimals:", (a.abserr < 0.005).sum(), "/", len(a))
    df.to_csv(f"{WD}/eval_pdf_all_langs.csv", index=False)
    print(df[~df.ok][["path", "lang", "question", "answer", "pred"]].head(20).to_string())

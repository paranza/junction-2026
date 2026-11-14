# Parse ifc_models questions into (family, target, storey/room/model) with per-language regexes.
import re, pandas as pd
Q = r"[\"'„“]"; E = r"[\"'“”]"
CNT = {  # localized element words -> canonical target
 "doors":"door","døre":"door","ust":"door","türen":"door",
 "windows":"window","vinduer":"window","akent":"window","fenster":"window",
 "rooms (spaces)":"space","rum":"space","ruumi":"space","räume":"space",
 "walls":"wall","vægge":"wall","seina":"wall","wände":"wall",
 "columns":"column","søjler":"column","posti":"column","stützen":"column",
 "beams":"beam","bjælker":"beam","tala":"beam","träger":"beam",
 "stairs":"stair","trapper":"stair","treppi":"stair","treppen":"stair",
 "sanitary fixtures":"sanitary",
}
W = "|".join(sorted(map(re.escape, CNT), key=len, reverse=True))
PATS = [
 ("room_area", "en", rf"What is the net floor area of the room {Q}(?P<room>.+){E} on {Q}(?P<storey>.+){E}, in m²\?"),
 ("room_area", "et", rf"Kui suur on ruumi {Q}(?P<room>.+){E} netopõrandapind korrusel {Q}(?P<storey>.+){E} \(m²\)\?"),
 ("room_area", "da", rf"Hvad er nettoarealet af rummet {Q}(?P<room>.+){E} på {Q}(?P<storey>.+){E} i m²\?"),
 ("storey_space_area", "en", rf"What is the total net floor area of all rooms \(spaces\) on {Q}(?P<storey>.+){E}, in m²\?"),
 ("storey_space_area", "et", rf"Kui suur on kõigi ruumide netopõrandapind kokku korrusel {Q}(?P<storey>.+){E} \(m²\)\?"),
 ("storey_space_area", "da", rf"Hvad er det samlede nettoareal af alle rum på {Q}(?P<storey>.+){E} i m²\?"),
 ("storey_count", "en", rf"How many (?P<what>{W}) are shown on the floor plan of {Q}(?P<storey>.+){E}\?"),
 ("storey_count", "et", rf"Mitu (?P<what>{W}) on näidatud korruse {Q}(?P<storey>.+){E} plaanil\?"),
 ("storey_count", "da", rf"Hvor mange (?P<what>{W}) er vist på plantegningen for {Q}(?P<storey>.+){E}\?"),
 ("storey_count", "de", rf"Wie viele (?P<what>{W}) sind im Grundriss {Q}(?P<storey>.+){E} dargestellt\?"),
 ("model_count", "en", rf"How many (?P<what>{W}) are there in the model {Q}(?P<model>.+){E}\?"),
 ("model_count", "et", rf"Mitu (?P<what>{W}) on mudelis {Q}(?P<model>.+){E}\?"),
 ("model_count", "da", rf"Hvor mange (?P<what>{W}) er der i modellen {Q}(?P<model>.+){E}\?"),
 ("model_count", "de", rf"Wie viele (?P<what>{W}) enthält das Modell {Q}(?P<model>.+){E}\?"),
 ("wall_length", "en", rf"What is the total length of all walls on {Q}(?P<storey>.+){E}, in metres\?"),
 ("wall_length", "da", rf"Hvad er den samlede længde af alle vægge på {Q}(?P<storey>.+){E} i meter\?"),
 ("wall_length", "de", rf"Wie lang sind alle Wände im Geschoss {Q}(?P<storey>.+){E} zusammen, in Metern\?"),
 ("wall_side_area", "en", rf"What is the total net side area of all walls on {Q}(?P<storey>.+){E}, in m²\?"),
 ("wall_side_area", "da", rf"Hvad er det samlede nettosideareal af alle vægge på {Q}(?P<storey>.+){E} i m²\?"),
 ("wall_side_area", "de", rf"Wie groß ist die gesamte Netto-Seitenfläche aller Wände im Geschoss {Q}(?P<storey>.+){E} in m²\?"),
 ("wall_volume", "en", rf"What is the total net volume of all walls on {Q}(?P<storey>.+){E}, in m³\?"),
 ("wall_volume", "da", rf"Hvad er det samlede nettovolumen af alle vægge på {Q}(?P<storey>.+){E} i m³\?"),
 ("wall_volume", "de", rf"Wie groß ist das gesamte Netto-Volumen aller Wände im Geschoss {Q}(?P<storey>.+){E} in m³\?"),
 ("slab_volume", "en", rf"What is the total net volume of all slabs on {Q}(?P<storey>.+){E}, in m³\?"),
 ("slab_volume", "da", rf"Hvad er det samlede nettovolumen af alle dæk og plader på {Q}(?P<storey>.+){E} i m³\?"),
 ("slab_volume", "de", rf"Wie groß ist das gesamte Netto-Volumen aller Decken und Bodenplatten im Geschoss {Q}(?P<storey>.+){E} in m³\?"),
]
def parse(q):
    for fam, lang, p in PATS:
        m = re.fullmatch(p, q, flags=re.I)
        if m:
            d = m.groupdict(); d["family"] = fam; d["lang"] = lang
            if "what" in d: d["what"] = CNT[d["what"].lower()]
            return d
    return {"family": None}
def load():
    df = pd.read_pickle("ifc_q.pkl")
    P = pd.DataFrame([parse(q) for q in df.question])
    return pd.concat([df, P], axis=1)
if __name__ == "__main__":
    df = load()
    print("unparsed:", df.family.isna().sum())
    print(df[df.family.isna()].question.tolist()[:10])
    df.to_pickle("ifc_q_parsed.pkl")
    pd.set_option("display.width", 250)
    print(pd.crosstab([df.file, df.family], df.lang, margins=True).to_string())
    print(pd.crosstab([df.family, df.what.fillna("-")], df.file.str[:14]).to_string())
